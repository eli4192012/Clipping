import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import av
import imageio_ffmpeg

from project_store import write, read
from queue_exports import export_suggestions, render_identity
from clip_queue import QueueStore
from queue_runner import run
from jobs import analysis_path
from upgrades import transcript_file

SETTINGS = dict(mode='Podcast',minimum=1,maximum=10,windows=1,vision=False,semantic=False,
                quality='Balanced',shorts_editor=False,portrait=False)


class QueueExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.folder=self.root/'data/project';self.folder.mkdir(parents=True)
        self.source=self.folder/'source.mp4'
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-f','lavfi','-i','color=blue:s=320x180:r=25:d=4',
                        '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=4','-c:v','libx264','-c:a','aac',str(self.source)],check=True,capture_output=True)
        self.project=dict(folder=str(self.folder),source=str(self.source),duration=4,title='Saved queue fixture')
        self.words=[dict(start=i*.5,end=i*.5+.4,text=t) for i,t in enumerate('A complete useful idea.'.split())]
        self.transcript=transcript_file(self.folder,SETTINGS)
        write(self.transcript,dict(words=self.words,sentences=[dict(start=0,end=2,text='A complete useful idea.')],language='en'))
        self.candidate=dict(start=0,end=2,text='A complete useful idea.',title='A complete useful idea',passed=True)
        self.result=analysis_path(self.project,SETTINGS)
        write(self.result,[self.candidate])

    def tearDown(self):self.tmp.cleanup()

    def test_native_export_and_manifest_reopen_without_rerendering(self):
        checkpoints=[]
        with patch('engine.ROOT',self.root):
            outputs=export_suggestions(self.project,SETTINGS,self.result,checkpoint=lambda result:checkpoints.append(list(result)))
        self.assertEqual(len(outputs),1);self.assertEqual(checkpoints[-1],outputs)
        video=Path(outputs[0]['video']);self.assertTrue(video.is_file())
        with av.open(str(video)) as media:
            self.assertEqual(media.streams.video[0].width,320)
            self.assertTrue(media.streams.audio);self.assertTrue(media.streams.subtitles)
            self.assertAlmostEqual(media.duration/av.time_base,2,delta=.08)
        self.assertIn('A complete',Path(outputs[0]['captions']).read_text())
        with patch('engine.export_clip',side_effect=AssertionError('Rendered a saved clip again')):
            self.assertEqual(export_suggestions(self.project,SETTINGS,self.result),outputs)
        self.assertEqual(len(read(self.folder/'finished-clips.json',{})),1)

    def test_partial_export_failure_keeps_successful_clip_and_retries_only_missing_export(self):
        second=dict(self.candidate,start=2,end=4,title='Second fixture')
        write(self.result,[self.candidate,second])
        from engine import export_clip
        count=0
        def fail_second(*args,**kwargs):
            nonlocal count
            count+=1
            if count==2:raise RuntimeError('Simulated encoding failure')
            return export_clip(*args,**kwargs)
        outputs=[]
        with patch('engine.ROOT',self.root),patch('engine.export_clip',side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError,'Saved clips are kept'):
                export_suggestions(self.project,SETTINGS,self.result,checkpoint=lambda result:outputs.extend(result))
        self.assertEqual(len(outputs),1);self.assertTrue(Path(outputs[0]['video']).is_file())
        with patch('engine.ROOT',self.root),patch('engine.export_clip',wraps=export_clip) as export:
            final=export_suggestions(self.project,SETTINGS,self.result)
        self.assertEqual(export.call_count,1);self.assertEqual(len(final),2)
        self.assertEqual(final[0]['video'],outputs[0]['video'])

    def test_empty_selection_is_complete_without_creating_an_export(self):
        write(self.result,[])
        with patch('engine.export_clip') as export:
            self.assertEqual(export_suggestions(self.project,SETTINGS,self.result),[])
        export.assert_not_called()

    def test_shared_render_key_preserves_prior_editor_identity(self):
        package={'fingerprint':'package'};style={'packaging_version':1};ranges=[{'start':0,'end':2}]
        import hashlib
        old=[self.folder.name,self.source.stat().st_mtime_ns,self.transcript.stat().st_mtime_ns,0,2,style,self.words,ranges,'package','v517']
        expected=hashlib.sha256(json.dumps(old).encode()).hexdigest()[:24]
        self.assertEqual(render_identity(self.folder,self.source,self.transcript,0,2,style,self.words,ranges,package,ranges),expected)

    def test_two_saved_analyses_run_fifo_and_export_both_with_real_ffmpeg(self):
        second_folder=self.root/'data/second';second_folder.mkdir()
        second_source=second_folder/'source.mp4';second_source.write_bytes(self.source.read_bytes())
        second=dict(self.project,folder=str(second_folder),source=str(second_source),title='Second saved fixture')
        write(transcript_file(second_folder,SETTINGS),read(self.transcript,{}))
        write(analysis_path(second,SETTINGS),[self.candidate])
        store=QueueStore(self.root)
        a,_=store.add(self.project,SETTINGS);b,_=store.add(second,SETTINGS);store.set_enabled(True)
        before=(self.source.read_bytes(),self.transcript.read_bytes(),self.result.read_bytes())
        with patch('engine.ROOT',self.root),patch('jobs.get_transcript',side_effect=AssertionError('Retranscribed saved work')),patch('jobs.worker',side_effect=AssertionError('Unexpected model work')):
            run(self.root)
        first,last=store.get(a['id']),store.get(b['id'])
        self.assertEqual((first['state'],last['state']),('done','done'))
        self.assertLessEqual(first['finished'],last['started'])
        self.assertEqual((len(first['exports']),len(last['exports'])),(1,1))
        self.assertTrue(all(Path(row['exports'][0]['video']).is_file() for row in (first,last)))
        self.assertEqual(before,(self.source.read_bytes(),self.transcript.read_bytes(),self.result.read_bytes()))
        self.assertFalse(store.enabled())

    def test_channel_discovery_to_serial_import_cached_analysis_and_real_captioned_export(self):
        from channel_watch import WatchStore,tick
        import time,fcntl
        cid='UC'+'a'*22;identity='vid00000001'
        new_folder=self.root/'data'/('youtube-'+identity)
        self.folder.rename(new_folder)
        self.folder=new_folder;self.source=new_folder/self.source.name
        self.transcript=new_folder/self.transcript.name;self.result=new_folder/self.result.name
        self.project.update(folder=str(new_folder),source=str(self.source))
        metadata=dict(id=identity,url='https://www.youtube.com/watch?v='+identity,title='Finished channel fixture',
                      channel_id=cid,channel='Fixture channel',duration=4,published=time.time()-10)
        channel=dict(id=cid,name='Fixture channel',url='https://www.youtube.com/channel/'+cid+'/videos',entries=[metadata])
        watch=WatchStore(self.root);watch.connect(channel,SETTINGS)
        tick(watch,discovery=lambda url:channel,inspector=lambda url:metadata,launch=lambda root:None)
        store=QueueStore(self.root);item=store.items()[0]
        self.assertEqual(item['project']['source'],'')
        before=(self.source.read_bytes(),self.transcript.read_bytes(),self.result.read_bytes())
        def imported(*args,**kwargs):
            with (self.root/'work/heavy-job.lock').open('a') as lock:
                with self.assertRaises(BlockingIOError):fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            return self.source,self.folder
        with (patch('youtube_import.lookup',return_value=metadata),patch('youtube_import.download',side_effect=imported),
              patch('engine.ROOT',self.root),patch('jobs.get_transcript',side_effect=AssertionError('Retranscribed saved work')),
              patch('jobs.worker',side_effect=AssertionError('Unexpected model work'))):
            run(self.root)
        saved=store.get(item['id']);self.assertEqual(saved['state'],'done',saved['error'])
        self.assertEqual(len(saved['exports']),1)
        output=saved['exports'][0]
        with av.open(output['video']) as media:
            self.assertAlmostEqual(media.duration/av.time_base,2,delta=.08)
            self.assertTrue(media.streams.audio)
        self.assertIn('A complete',Path(output['captions']).read_text())
        self.assertEqual(before,(self.source.read_bytes(),self.transcript.read_bytes(),self.result.read_bytes()))
        watch.request_check(cid)
        tick(watch,discovery=lambda url:channel,inspector=lambda url:metadata,launch=lambda root:None)
        self.assertEqual(len(store.items()),1)


if __name__=='__main__':unittest.main()
