import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

from channel_watch import WatchStore
from clip_queue import QueueStore

CID='UC'+'a'*22
CHANNEL=dict(id=CID,name='Indianapolis Colts',url='https://www.youtube.com/channel/'+CID+'/videos',entries=[])
SETTINGS=dict(mode='Interview',minimum=30,maximum=120,windows=6,vision=False,semantic=True,
              quality='Balanced',shorts_editor=True,portrait=True)


class ChannelUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'data').mkdir()
        self.store=WatchStore(self.root)
        self.patches=[patch('channel_watch_ui.ensure_watcher'),patch('channel_watch_ui.watcher_alive',return_value=True),
                      patch('channel_watch_ui.ready',return_value=True),patch('channel_watch_ui.discover',return_value=CHANNEL)]
        self.launch,self.alive,self.ready,self.discover=[p.start() for p in self.patches]
        self.app=AppTest.from_string(f"from pathlib import Path\nimport streamlit as st\nfrom channel_watch_ui import show\ndef go(page):\n st.session_state.page=page\nshow(Path({str(self.root)!r}),go)",default_timeout=10)

    def tearDown(self):
        for p in self.patches:p.stop()
        self.tmp.cleanup()

    def button(self,label):return next(b for b in self.app.button if b.label==label)

    def test_connect_saves_selected_settings_and_starts_watcher_without_google_login(self):
        self.app.run();self.assertFalse(self.app.exception)
        self.app.text_input[0].set_value('@Colts')
        self.app.slider[0].set_value((40,100))
        next(s for s in self.app.selectbox if s.label=='Processing quality').set_value('Higher quality')
        self.button('Connect and start watching').click().run()
        self.assertFalse(self.app.exception)
        self.discover.assert_called_once_with('@Colts',limit=1)
        saved=self.store.get(CID)
        self.assertTrue(saved['enabled']);self.assertEqual(saved['settings']['minimum'],40)
        self.assertEqual(saved['settings']['maximum'],100);self.assertEqual(saved['settings']['quality'],'Higher quality')
        self.assertTrue(saved['settings']['portrait']);self.launch.assert_called()
        self.assertTrue(saved['settings']['watch_auto_type'])
        self.assertEqual(QueueStore(self.root).items(),[])

    def test_pause_resume_check_now_and_queue_navigation(self):
        self.store.connect(CHANNEL,SETTINGS)
        self.app.run();self.button('Pause watching').click().run()
        self.assertFalse(self.store.get(CID)['enabled'])
        self.assertTrue(self.button('Check now').disabled)
        self.button('Resume watching').click().run()
        self.assertTrue(self.store.get(CID)['enabled'])
        self.store.update(CID,next_check=9999999999)
        self.button('Check now').click().run();self.assertEqual(self.store.get(CID)['next_check'],0)
        self.button('Open video queue').click().run()
        self.assertEqual(self.app.session_state['page'],'queue')

    def test_missing_model_and_invalid_channel_do_not_save_subscription(self):
        self.ready.return_value=False
        self.app.run();self.button('Connect and start watching').click().run()
        self.assertTrue(self.app.error);self.discover.assert_not_called();self.assertEqual(self.store.channels(),[])
        self.ready.return_value=True;self.discover.side_effect=ValueError('Use a channel link')
        self.button('Connect and start watching').click().run()
        self.assertFalse(self.app.exception);self.assertEqual(self.store.channels(),[])
        self.assertIn('channel link',self.app.error[0].value)

    def test_paused_queue_warning_and_failed_upload_history_are_visible(self):
        self.store.connect(CHANNEL,SETTINGS);QueueStore(self.root).set_enabled(False)
        self.store.record(CID,dict(id='vid00000001',title='Pending upload'),'error',error='Video temporarily unavailable')
        self.app.run();self.assertFalse(self.app.exception)
        self.assertTrue(any('queue is paused' in w.value for w in self.app.warning))
        self.assertTrue(any('Pending upload' in t.value for t in self.app.markdown))
        self.assertTrue(any('temporarily unavailable' in c.value for c in self.app.caption))

    def test_new_sidebar_page_opens_without_an_active_project(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15)
        app.session_state['page']='source'
        with patch('channel_watch_ui.show') as show,patch('channel_watch.ensure_watcher'):
            app.run();self.assertFalse(app.exception)
            next(b for b in app.button if b.label=='YouTube channels').click().run()
            self.assertEqual(app.session_state['page'],'channels');show.assert_called_once()

    def test_live_upgrade_reloads_cached_youtube_import_module(self):
        import youtube_import
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15)
        app.session_state['page']='channels'
        with patch.object(youtube_import,'YOUTUBE_IMPORT_API',0),patch('channel_watch_ui.show'),patch('channel_watch.ensure_watcher'):
            app.run();self.assertFalse(app.exception)
            self.assertEqual(youtube_import.YOUTUBE_IMPORT_API,3)
            self.assertTrue(issubclass(youtube_import.UnfinishedVideo,ValueError))

    def test_completed_channel_clips_are_visible_and_open_saved_results_directly(self):
        from project_store import write
        metadata=dict(id='vid00000001',url='https://www.youtube.com/watch?v=vid00000001',
                      title='Completed upload',duration=300,channel_id=CID,published=100)
        self.store.connect(CHANNEL,SETTINGS);self.store.record(CID,metadata,'ready',metadata)
        item=self.store.enqueue(CID,metadata);queue=QueueStore(self.root)
        queue.set_enabled(True);queue.claim()
        result=self.root/'data/clips.json';write(result,[dict(start=0,end=5)])
        output=self.root/'data/clip.mp4';output.write_bytes(b'export')
        queue.update(item['id'],result=str(result),exports=[dict(video=str(output))]);queue.finish(item['id'])
        self.app.run();self.assertFalse(self.app.exception)
        self.assertEqual(next(m for m in self.app.metric if m.label=='Ready clips').value,'1')
        self.button('Open clips').click().run()
        self.assertEqual(self.app.session_state['page'],'results')
        self.assertEqual(self.app.session_state['result_path'],str(result))
        self.assertEqual(self.app.session_state['settings'],SETTINGS)

    def test_processing_and_automatic_retry_are_visible_on_channel_page(self):
        import time
        self.store.connect(CHANNEL,SETTINGS)
        meta=dict(id='vid00000001',url='https://www.youtube.com/watch?v=vid00000001',
                  title='Pending upload',duration=300,channel_id=CID,published=time.time())
        self.store.record(CID,meta,'ready',meta);item=self.store.enqueue(CID,meta)
        queue=QueueStore(self.root);queue.set_enabled(True);queue.claim()
        queue.update(item['id'],progress=.6,label='Reviewing 2 of 4')
        self.app.run();self.assertFalse(self.app.exception)
        self.assertTrue(any('Reviewing 2 of 4'==p.text for p in self.app.get('progress')))
        queue.retry_upload(item['id'],'HTTP Error 403: Forbidden')
        self.app.run();self.assertFalse(self.app.exception)
        self.assertTrue(any('Automatic retry' in i.value for i in self.app.info))

    def test_live_upgrade_reloads_old_worker_and_queue_modules(self):
        import jobs,upgrades,local_worker_process,clip_queue
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15)
        app.session_state['page']='channels'
        with (patch.object(jobs,'CURATION_API',0),patch.object(upgrades,'WORKER_API',0),
              patch.object(local_worker_process,'LOCAL_WORKER_API',0),patch.object(clip_queue,'QUEUE_API',0),
              patch('channel_watch_ui.show'),patch('channel_watch.ensure_watcher')):
            app.run();self.assertFalse(app.exception)
            self.assertEqual(jobs.CURATION_API,3);self.assertEqual(upgrades.WORKER_API,2)
            self.assertEqual(local_worker_process.LOCAL_WORKER_API,3);self.assertEqual(clip_queue.QUEUE_API,4)


if __name__=='__main__':unittest.main()
