import fcntl
import json
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from channel_watch import WatchStore, tick, run, watcher_alive, ensure_watcher
from clip_queue import QueueStore
from queue_runner import run as run_queue, process_item
from youtube_channels import normalize_channel, discover, eligible, prepare_item, RECENT_SECONDS, automatic_settings
from youtube_import import UnfinishedVideo

CID = 'UC'+'a'*22
NOW = 1_800_000_000
SETTINGS = dict(mode='Interview',minimum=30,maximum=120,windows=6,vision=False,semantic=True,
                quality='Balanced',shorts_editor=True,portrait=True)


def video(number, age=10, channel=CID):
    identity = f'vid{number:08d}'
    return dict(id=identity,url='https://www.youtube.com/watch?v='+identity,title=f'Upload {number}',
                channel_id=channel,channel='Test channel',published=NOW-age,duration=300)


def channel(entries=(), identity=CID):
    return dict(id=identity,name='Test channel',url='https://www.youtube.com/channel/'+identity+'/videos',entries=list(entries))


class DiscoveryTests(unittest.TestCase):
    def test_channel_links_and_handles_are_canonical_and_video_links_rejected(self):
        for url in ['@Colts','youtube.com/@Colts','https://m.youtube.com/@Colts/shorts?view=0',
                    'https://www.youtube.com/@Colts/videos']:
            self.assertEqual(normalize_channel(url),'https://www.youtube.com/@Colts/videos')
        self.assertEqual(normalize_channel('youtube.com/channel/'+CID),'https://www.youtube.com/channel/'+CID+'/videos')
        for url in ['https://example.com/@Colts','https://youtube.com.evil.test/@Colts',
                    'https://user@youtube.com/@Colts','https://youtube.com/watch?v=vid00000001',
                    'https://youtu.be/vid00000001','https://youtube.com/playlist?list=abc',
                    'https://youtube.com/channel/invalid','https://youtube.com/@Colts%2Fwatch',
                    'file:///etc/passwd']:
            with self.subTest(url=url),self.assertRaises(ValueError):normalize_channel(url)

    def test_discovery_reads_only_videos_tab_without_downloading(self):
        with patch('youtube_channels.YoutubeDL') as downloader:
            downloader.return_value.__enter__.return_value.extract_info.return_value = dict(
                channel_id=CID,channel='Test channel',entries=[video(1),dict(id='bad'),None])
            result = discover('@Colts')
            opts = downloader.call_args.args[0]
            self.assertTrue(opts['extract_flat']);self.assertFalse(opts['noplaylist'])
            self.assertEqual(opts['playlistend'],50)
            downloader.return_value.__enter__.return_value.extract_info.assert_called_once_with(
                'https://www.youtube.com/@Colts/videos',download=False)
        self.assertEqual(result['id'],CID);self.assertEqual(len(result['entries']),1)

    def test_real_timestamp_boundary_newest_fallback_future_and_missing_date(self):
        for age,expected in [(RECENT_SECONDS,True),(RECENT_SECONDS+1,False)]:
            self.assertEqual(eligible(video(1,age),'other',NOW),expected)
        self.assertTrue(eligible(video(1,RECENT_SECONDS*5),video(1)['id'],NOW))
        self.assertFalse(eligible(video(1,-1),video(1)['id'],NOW))
        for bad in [None,0,float('nan'),'today',True]:
            with self.assertRaises(ValueError):eligible(dict(video(1),published=bad),'other',NOW)


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.root = Path(self.tmp.name)
        self.store = WatchStore(self.root);self.queue = QueueStore(self.root)
        self.store.connect(channel(),SETTINGS)
        self.launch = lambda root:None

    def tearDown(self):self.tmp.cleanup()

    def scan(self, videos, now=NOW, inspector=None):
        table = {v['url']:v for v in videos}
        tick(self.store,now,lambda url:channel(videos),inspector or table.__getitem__,self.launch)

    def test_recent_backfill_fifo_frozen_settings_and_no_duplicates_after_completion_restart(self):
        newest, older, ancient = video(1,1),video(2,400),video(3,RECENT_SECONDS+1)
        self.scan([newest,older,ancient])
        items = self.queue.items()
        self.assertEqual([i['remote']['id'] for i in items],[older['id'],newest['id']])
        self.assertTrue(all(i['export_clips'] for i in items));self.assertTrue(self.queue.enabled())
        self.assertFalse((self.root/'data'/('youtube-'+newest['id'])).exists())
        self.store.connect(channel(),dict(SETTINGS,maximum=150))
        self.assertEqual(self.queue.get(items[0]['id'])['settings']['maximum'],120)
        run_queue(self.root,lambda *args:None)
        self.assertFalse(self.queue.enabled());self.assertFalse(self.queue.paused())
        self.store = WatchStore(self.root)
        self.scan([newest,older,ancient],NOW+1)
        self.assertEqual(len(self.queue.items()),2)
        new = video(4,-1)
        self.store.request_check(CID);self.scan([new,newest,older],NOW+2)
        self.assertEqual(len(self.queue.items()),3);self.assertTrue(self.queue.enabled())
        self.assertEqual(self.queue.items()[-1]['settings']['maximum'],150)

    def test_newest_old_upload_is_queued_once(self):
        self.scan([video(1,RECENT_SECONDS*4),video(2,RECENT_SECONDS*5)])
        self.assertEqual([i['remote']['id'] for i in self.queue.items()],[video(1)['id']])

    def test_paused_queue_accepts_jobs_without_resuming(self):
        self.queue.set_enabled(False)
        self.scan([video(1)])
        self.assertEqual(len(self.queue.items()),1);self.assertFalse(self.queue.enabled())
        self.queue.set_enabled(True);run_queue(self.root,lambda *args:None)
        self.store.request_check(CID);self.scan([video(2),video(1)],NOW+301)
        self.assertTrue(self.queue.enabled())

    def test_pause_during_lookup_stops_enqueue_and_resume_recovers_pending_decision(self):
        def pause(url):self.store.set_enabled(CID,False);return video(1)
        self.scan([video(1)],inspector=pause)
        self.assertEqual(self.queue.items(),[])
        self.store.set_enabled(CID,True)
        self.scan([video(1)],NOW+1)
        self.assertEqual(len(self.queue.items()),1)

    def test_live_and_premiere_are_not_queued_and_finished_premiere_can_retry(self):
        live = dict(video(1),live_status='is_live')
        premiere = video(2)
        fallback = video(3,RECENT_SECONDS*3)
        def lookup(url):
            if url==premiere['url']:raise UnfinishedVideo('Upcoming premiere')
            return fallback
        self.scan([live,premiere,fallback],inspector=lookup)
        self.assertEqual([i['remote']['id'] for i in self.queue.items()],[fallback['id']])
        self.store.request_check(CID)
        self.scan([premiere,fallback],NOW+301)
        self.assertEqual(len(self.queue.items()),2)

    def test_future_and_undated_sources_are_not_imported(self):
        self.scan([video(1,-30),dict(video(2),published=None),video(3,RECENT_SECONDS*3)])
        self.assertEqual(self.queue.items(),[])
        self.assertEqual({r['state'] for r in self.store.videos(CID)},{'waiting','error','old'})

    def test_failed_channel_does_not_stop_another_and_retries_with_backoff(self):
        other = 'UC'+'b'*22
        self.store.connect(channel(identity=other),SETTINGS)
        def discovery(url):
            if CID in url:raise OSError('Network unavailable')
            return channel([video(1,channel=other)],other)
        inspector = lambda url:video(1,channel=other)
        tick(self.store,NOW,discovery,inspector,self.launch)
        self.assertEqual(self.store.get(CID)['next_check'],NOW+300)
        self.assertEqual(len(self.queue.items()),1)
        tick(self.store,NOW+300,discovery,inspector,self.launch)
        self.assertEqual(self.store.get(CID)['next_check'],NOW+900)
        self.assertEqual(self.store.get(CID)['failures'],2)

    def test_video_error_retry_does_not_duplicate_other_queued_video(self):
        def lookup(url):
            if url==video(1)['url']:raise OSError('Temporarily private')
            return video(2)
        self.scan([video(1),video(2)],inspector=lookup)
        self.assertEqual(len(self.queue.items()),1)
        self.store.request_check(CID);self.scan([video(1),video(2)],NOW+1)
        self.assertEqual(len(self.queue.items()),2)

    def test_queue_receipt_recovers_crash_before_watch_receipt_commit(self):
        prior,_ = self.queue.add_youtube(video(1),SETTINGS)
        self.scan([video(1)])
        self.assertEqual(len(self.queue.items()),1)
        self.assertEqual(self.store.videos(CID)[0]['queue_id'],prior['id'])
        self.queue.remove(prior['id'])
        self.store.request_check(CID);self.scan([video(1)],NOW+1)
        self.assertEqual(len(self.queue.items()),1)

    def test_wrong_channel_metadata_or_redirect_is_rejected(self):
        self.scan([video(1)],inspector=lambda url:dict(video(1),channel_id='different'))
        self.assertEqual(self.queue.items(),[])
        self.store.request_check(CID)
        tick(self.store,NOW,lambda url:channel([video(1)],'UC'+'b'*22),lambda url:video(1),self.launch)
        self.assertIn('different channel',self.store.get(CID)['error'])

    def test_watcher_elects_one_process_and_pausing_all_stops_it(self):
        path=self.root/'work/channel-watch.lock';path.parent.mkdir()
        with path.open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            self.assertTrue(watcher_alive(self.root))
            run(self.root,poll=0,check=lambda *args:self.fail('Second watcher checked uploads'))
        checks=[]
        def stop(store):checks.append(True);store.set_enabled(CID,False)
        run(self.root,poll=0,check=stop)
        self.assertEqual(checks,[True]);self.assertFalse(watcher_alive(self.root))

    def test_launcher_uses_detached_local_process_and_no_files_when_unconfigured(self):
        with tempfile.TemporaryDirectory() as untouched,patch('channel_watch.subprocess.Popen') as popen:
            ensure_watcher(untouched);popen.assert_not_called()
            self.assertEqual(list(Path(untouched).iterdir()),[])
            ensure_watcher(self.root)
            self.assertTrue(popen.call_args.kwargs['start_new_session'])
            self.assertIn('--root',popen.call_args.args[0])


class RemoteQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=QueueStore(self.root)
        self.meta=dict(video(1),published=time.time()-10)

    def tearDown(self):self.tmp.cleanup()

    def test_queue_origin_deduplicates_completed_manual_import(self):
        folder=self.root/'data'/('youtube-'+self.meta['id']);folder.mkdir()
        source=folder/'source.mp4';source.write_bytes(b'fixture')
        manual,_=self.store.add(dict(folder=str(folder),source=str(source),title='Manual',duration=300),SETTINGS)
        self.store.set_enabled(True);item=self.store.claim();self.store.finish(item['id'])
        auto,fresh=self.store.add_youtube(self.meta,SETTINGS)
        self.assertFalse(fresh);self.assertEqual(auto['id'],manual['id'])
        self.assertEqual(len(self.store.items()),1)

    def test_import_preserves_existing_project_and_settings_and_reuses_analysis_exports(self):
        queued,_=self.store.add_youtube(self.meta,SETTINGS);self.store.set_enabled(True);item=self.store.claim()
        folder=self.root/'data'/('youtube-'+self.meta['id']);folder.mkdir()
        source=folder/'source.mp4';source.write_bytes(b'fixture')
        (folder/'project.json').write_text('{"title":"Manually named"}')
        (folder/'ui-settings.json').write_text('{"custom":true}')
        with (patch('youtube_import.lookup',return_value=self.meta),patch('youtube_import.download',return_value=(source,folder)) as download,
              patch('jobs.analyze',return_value='cached.json') as analyze,patch('jobs.estimate_seconds',return_value=100),patch('queue_exports.export_suggestions') as export):
            process_item(self.store,item)
        download.assert_called_once();self.assertEqual(download.call_args.kwargs['root'],self.root.resolve())
        self.assertEqual(json.loads((folder/'project.json').read_text())['title'],'Manually named')
        self.assertEqual(json.loads((folder/'ui-settings.json').read_text()),{'custom':True})
        analyze.assert_called_once();export.assert_called_once()
        saved=self.store.get(queued['id']);self.assertEqual(saved['project']['source'],str(source))
        self.assertEqual(saved['result'],'cached.json')

    def test_expired_queued_video_skips_download_and_next_job_continues(self):
        old=dict(self.meta,published=time.time()-RECENT_SECONDS-1)
        skipped,_=self.store.add_youtube(old,SETTINGS)
        following,_=self.store.add_youtube(dict(self.meta,**{k:v for k,v in video(2).items() if k in ('id','url','title')}),SETTINGS)
        self.store.set_enabled(True)
        with patch('youtube_import.lookup',side_effect=lambda url:old if url==old['url'] else dict(video(2),published=time.time()-10)),patch('youtube_channels.discover',return_value=channel([video(2),old])),patch('youtube_import.download') as download:
            def process(store,item):
                if item['id']==skipped['id']:prepare_item(store,item)
            run_queue(self.root,process)
        download.assert_not_called()
        self.assertEqual(self.store.get(skipped['id'])['state'],'skipped')
        self.assertEqual(self.store.get(following['id'])['state'],'done')

    def test_old_newest_video_remains_eligible_at_execution(self):
        old=dict(self.meta,published=time.time()-RECENT_SECONDS*3)
        self.store.add_youtube(old,SETTINGS);self.store.set_enabled(True);item=self.store.claim()
        with patch('youtube_import.lookup',return_value=old),patch('youtube_channels.discover',return_value=channel([old])),patch('youtube_import.download',side_effect=RuntimeError('download called')):
            with self.assertRaisesRegex(RuntimeError,'download called'):prepare_item(self.store,item)

    def test_changed_prepared_source_is_rejected_before_reimport(self):
        self.store.add_youtube(self.meta,SETTINGS);self.store.set_enabled(True);item=self.store.claim()
        folder=self.root/'data'/('youtube-'+self.meta['id']);folder.mkdir();source=folder/'source.mp4';source.write_bytes(b'old')
        item=self.store.prepared(item['id'],dict(item['project'],source=str(source)))
        source.write_bytes(b'changed')
        with patch('youtube_channels.prepare_item') as prepare:
            with self.assertRaisesRegex(ValueError,'changed'):process_item(self.store,item)
            prepare.assert_not_called()

    def test_legacy_idle_and_paused_queue_migrations_preserve_intent(self):
        self.store.add_youtube(self.meta,SETTINGS)
        with closing(sqlite3.connect(self.store.path)) as db:
            db.executescript('DROP TABLE control;CREATE TABLE control(id INTEGER PRIMARY KEY,enabled INTEGER NOT NULL);INSERT INTO control VALUES(1,0);')
        migrated=QueueStore(self.root)
        self.assertTrue(migrated.paused());migrated.auto_start();self.assertFalse(migrated.enabled())
        migrated.set_enabled(True);run_queue(self.root,lambda *args:None)
        with closing(sqlite3.connect(self.store.path)) as db:
            db.executescript('DROP TABLE control;CREATE TABLE control(id INTEGER PRIMARY KEY,enabled INTEGER NOT NULL);INSERT INTO control VALUES(1,0);')
        migrated=QueueStore(self.root);self.assertFalse(migrated.paused())

    def test_automatic_mode_uses_saved_transcript_and_persists_resolved_settings(self):
        settings=dict(SETTINGS,watch_auto_type=True,watch_sports_vision=True)
        self.store.add_youtube(self.meta,settings);self.store.set_enabled(True);item=self.store.claim()
        folder=self.root/'data'/('youtube-'+self.meta['id']);folder.mkdir();source=folder/'source.mp4';source.write_bytes(b'fixture')
        speech={'words':[],'sentences':[{'text':'A complete story.'}],'language':'en'}
        detected=dict(mode='Podcast',categories=['Podcast'],confidence='Moderate',reason='Podcast title')
        with (patch('youtube_import.lookup',return_value=self.meta),patch('youtube_import.download',return_value=(source,folder)),
              patch('jobs.get_transcript',return_value=speech) as get_transcript,patch('video_type.detect',return_value=detected) as detect,
              patch('jobs.analyze',return_value='saved.json') as analyze,patch('jobs.estimate_seconds',return_value=10),patch('queue_exports.export_suggestions')):
            process_item(self.store,item)
        get_transcript.assert_called_once();self.assertIs(detect.call_args.kwargs['transcript'],speech)
        self.assertEqual(analyze.call_args.args[1]['mode'],'Podcast')
        self.assertEqual(self.store.get(item['id'])['settings']['video_type'],detected)
        self.assertEqual(self.store.get(item['id'])['settings']['maximum'],120)

    def test_automatic_sports_has_separate_rules_and_retry_retains_speech_preferences(self):
        settings=dict(SETTINGS,watch_auto_type=True,watch_sports_vision=True,coverage=1.)
        sports=automatic_settings(settings,dict(mode='Sports',categories=['American football'],confidence='Moderate'))
        self.assertEqual((sports['minimum'],sports['maximum']),(10,35));self.assertEqual(sports['coverage'],.35)
        self.assertFalse(sports['shorts_editor']);self.assertFalse(sports['semantic']);self.assertTrue(sports['vision'])
        interview=automatic_settings(sports,dict(mode='Interview',categories=['Interview'],confidence='High'))
        self.assertEqual((interview['minimum'],interview['maximum']),(30,120));self.assertEqual(interview['coverage'],1.)
        self.assertTrue(interview['shorts_editor']);self.assertTrue(interview['semantic']);self.assertFalse(interview['vision'])
        basketball=automatic_settings(settings,dict(mode='Sports',categories=['Basketball'],confidence='Moderate'))
        self.assertFalse(basketball['vision'])

    def test_provided_empty_full_transcript_does_not_trigger_sample_transcription(self):
        from video_type import detect
        folder=self.root/'data/detector';folder.mkdir();source=folder/'source.mp4';source.write_bytes(b'fixture')
        project=dict(source=str(source),folder=str(folder),title='A quiet video',duration=300)
        with patch('engine.speech_model',side_effect=AssertionError('Loaded speech for an existing transcript')),patch('framing.inspect_framing',return_value={'sample_count':1,'single_face_samples':0}):
            detected=detect(project,transcript={'sentences':[],'words':[]})
        self.assertEqual(detected['basis'],'saved transcript');self.assertEqual(detected['mode'],'Podcast')


if __name__=='__main__':unittest.main()
