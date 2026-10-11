import tempfile
import subprocess
import time
import unittest
from datetime import date,time as clock,datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
import social_auth as auth
import social_store as store
import social_publish as publisher
import social_schedule as schedule
import publishing_workspace as workspace
from clip_usage import is_used
from project_store import write,save_run
from test_social import Response


class SocialScheduleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.folder=self.root/'data/project';self.folder.mkdir(parents=True)
        source=self.folder/'source.mp4';source.write_bytes(b'original source')
        self.project=dict(folder=str(self.folder),source=str(source),title='Colts interview',duration=30)
        self.run=self.folder/'clips-test.json';self.candidate=dict(start=2.,end=12.,text='Keep your speed.',title='Keep your speed')
        write(self.run,[self.candidate]);self.settings=dict(mode='Podcast',minimum=5,maximum=30)
        save_run(self.project,self.settings,self.run)
        self.video=self.root/'exports/clip.mp4';self.video.parent.mkdir();self.video.write_bytes(b'video bytes')
        self.row=workspace.register_render(self.folder,self.run,self.candidate,dict(fingerprint='copy',final_transcript=self.candidate['text']),self.settings,self.video,self.video.with_suffix('.srt'),'render')
        self.db=patch.object(store,'DB',self.root/'data/social.sqlite3');self.db.start()
        self.account=dict(id='youtube:channel',platform='youtube',remote_id='channel',name='My channel');store.save_account(self.account)
        self.at=(datetime.now(timezone.utc)+timedelta(days=1)).replace(microsecond=0).isoformat().replace('+00:00','Z')
        self.secrets={}
        def secret(key,value=None):
            if value is not None:self.secrets[key]=value
            return self.secrets.get(key)
        self.vault=patch.object(auth,'secret',side_effect=secret);self.vault.start()
        self.access=patch.object(auth,'access',return_value='token');self.access_mock=self.access.start()
        self.ensure_scheduler=schedule.ensure_scheduler
        self.launch=patch('social_schedule.ensure_scheduler');self.launch.start()
        self.request=patch.object(auth,'request',side_effect=AssertionError('Unexpected real upload'));self.transport=self.request.start()

    def tearDown(self):
        self.request.stop();self.launch.stop();self.access.stop();self.vault.stop();self.db.stop();self.tmp.cleanup()

    def responses(self,values):self.transport.side_effect=values

    def schedule(self):
        return workspace.schedule_clip(self.row,self.account,'Keep your speed #fyp','A useful idea about keeping momentum.',False,self.at,'America/Chicago')

    def youtube(self):
        self.responses([Response(headers={'Location':'https://www.googleapis.com/upload/session'}),Response(308),Response(201,{'id':'posted','status':{'privacyStatus':'private','publishAt':self.at}})])
        return self.schedule()

    def instagram(self):
        self.account=dict(self.account,id='instagram:channel',platform='instagram');store.save_account(self.account)
        return self.schedule()

    def due(self):return schedule.parse_time(self.at).timestamp()+1

    def tick_due(self):
        with patch('social_schedule.time.time',return_value=self.due()):schedule.tick()

    def test_timezone_conversion_and_invalid_clock_changes(self):
        self.assertEqual(schedule.posting_time(date(2030,7,15),clock(18,0),'America/Chicago'),'2030-07-15T23:00:00Z')
        self.assertEqual(schedule.posting_time(date(2030,1,15),clock(18,0),'America/Chicago'),'2030-01-16T00:00:00Z')
        with self.assertRaisesRegex(ValueError,'skipped'):schedule.posting_time(date(2027,3,14),clock(2,30),'America/Chicago')
        with self.assertRaisesRegex(ValueError,'twice'):schedule.posting_time(date(2027,11,7),clock(1,30),'America/Chicago')
        with self.assertRaises(ValueError):schedule.posting_time(date(2030,1,15),clock(18),'Invalid/Zone')

    def test_past_naive_or_invalid_times_do_not_create_a_post(self):
        for value in ('2020-01-01T00:00:00Z','2030-01-01T12:00:00','bad'):
            with self.assertRaises(ValueError):workspace.schedule_clip(self.row,self.account,'Title #fyp','Description',False,value,'UTC')
        self.assertFalse(store.drafts());self.transport.assert_not_called()

    def test_youtube_uploads_privately_with_exact_schedule_and_keeps_receipt(self):
        draft=self.youtube();sent=self.transport.call_args_list[0].kwargs['json']
        self.assertEqual(sent['status']['privacyStatus'],'private');self.assertEqual(sent['status']['publishAt'],self.at)
        self.assertEqual(sent['snippet']['title'],'Keep your speed #fyp')
        self.assertEqual(draft['status'],'Scheduled');self.assertEqual(store.get(draft['id'])['remote_id'],'posted')
        self.assertFalse(is_used(self.folder,str(self.run),self.candidate))

    def test_youtube_processed_private_is_scheduled_until_actual_public_release(self):
        draft=self.youtube()
        self.responses([Response(data={'items':[{'status':dict(uploadStatus='processed',privacyStatus='private',publishAt=self.at)}]})])
        publisher.check(draft['id']);self.assertEqual(store.get(draft['id'])['status'],'Scheduled')
        self.assertFalse(is_used(self.folder,str(self.run),self.candidate))
        self.responses([Response(data={'items':[{'status':dict(uploadStatus='processed',privacyStatus='public')} ]})])
        publisher.check(draft['id']);self.assertEqual(store.get(draft['id'])['status'],'Published')
        self.assertTrue(is_used(self.folder,str(self.run),self.candidate))

    def test_missing_platform_schedule_never_claims_publication(self):
        draft=self.youtube()
        self.responses([Response(data={'items':[{'status':dict(uploadStatus='processed',privacyStatus='private')} ]})])
        publisher.check(draft['id']);self.assertEqual(store.get(draft['id'])['status'],'Needs check')
        self.assertFalse(is_used(self.folder,str(self.run),self.candidate))

    def test_scheduled_attempt_blocks_second_post(self):
        self.youtube();self.transport.reset_mock()
        with self.assertRaises(ValueError):self.schedule()
        self.transport.assert_not_called()

    def test_unknown_audience_does_not_start_native_schedule(self):
        with self.assertRaises(ValueError):workspace.schedule_clip(self.row,self.account,'Title #fyp','Description',None,self.at,'UTC')
        self.transport.assert_not_called()

    def test_late_youtube_resume_only_probes_and_does_not_send_more_bytes(self):
        draft=self.youtube();store.save(dict(store.get(draft['id']),status='Uploading'))
        self.responses([Response(308)])
        with patch('social_schedule.time.time',return_value=self.due()),patch('social_schedule.datetime') as dates:
            dates.fromisoformat.side_effect=datetime.fromisoformat;dates.now.return_value=datetime.fromtimestamp(self.due(),timezone.utc)
            with self.assertRaises(auth.SocialError):publisher.publish(draft['id'])
        self.assertEqual(self.transport.call_args.kwargs['data'],b'')
        self.assertEqual(store.get(draft['id'])['status'],'Needs check')

    def test_instagram_schedule_is_local_frozen_and_no_network_before_due(self):
        draft=self.instagram();self.transport.assert_not_called()
        schedule.tick();self.transport.assert_not_called()
        self.assertEqual(draft['status'],'Scheduled');self.assertEqual(draft['description'],'Keep your speed #fyp\n\nA useful idea about keeping momentum.')
        self.assertEqual(store.get(draft['id'])['file_size'],len(b'video bytes'))
        with self.assertRaises(auth.SocialError):publisher.publish(draft['id'],scheduled_due=True)

    def test_due_instagram_schedule_publishes_once(self):
        draft=self.instagram()
        self.responses([Response(data={'id':'container','uri':'https://rupload.facebook.com/upload'}),Response(data={'success':True}),Response(data={'status_code':'FINISHED'}),Response(data={'id':'posted'}),Response(data={'permalink':'https://www.instagram.com/reel/posted/'})])
        self.tick_due();self.assertEqual(store.get(draft['id'])['status'],'Published')
        count=self.transport.call_count;self.tick_due();self.assertEqual(self.transport.call_count,count)
        self.assertTrue(is_used(self.folder,str(self.run),self.candidate))

    def test_busy_upload_defers_local_schedule_without_losing_it(self):
        draft=self.instagram()
        with publisher.upload_lock():self.tick_due()
        self.transport.assert_not_called();self.assertEqual(store.get(draft['id'])['status'],'Scheduled')

    def test_missed_time_needs_new_schedule_instead_of_late_publication(self):
        draft=self.instagram();schedule.tick(now=self.due()+schedule.MAX_LATENESS)
        self.transport.assert_not_called();self.assertEqual(store.get(draft['id'])['status'],'Schedule failed')

    def test_disconnect_or_changed_video_cannot_publish_from_saved_schedule(self):
        draft=self.instagram();store.remove_account(self.account['id']);self.tick_due()
        self.transport.assert_not_called();self.assertEqual(store.get(draft['id'])['status'],'Schedule failed')
        schedule.cancel_local(draft['id'],store.get(draft['id'])['updated']);store.save_account(self.account)
        draft=self.schedule();self.video.write_bytes(b'different video');self.tick_due()
        self.transport.assert_not_called();self.assertEqual(store.get(draft['id'])['status'],'Schedule failed')

    def test_auth_failure_stops_local_schedule_before_network(self):
        draft=self.instagram();self.access_mock.side_effect=auth.SocialError('Reconnect')
        self.tick_due();self.transport.assert_not_called();self.assertEqual(store.get(draft['id'])['status'],'Schedule failed')

    def test_uncertain_instagram_publish_is_never_automatically_repeated(self):
        draft=self.instagram()
        self.responses([Response(data={'id':'container','uri':'https://rupload.facebook.com/upload'}),Response(data={'success':True}),Response(data={'status_code':'FINISHED'}),auth.SocialError('Interrupted')])
        self.tick_due();self.assertEqual(store.get(draft['id'])['status'],'Needs check')
        count=self.transport.call_count;self.tick_due();self.assertEqual(self.transport.call_count,count)

    def test_instagram_processing_continues_original_container(self):
        draft=self.instagram()
        self.responses([Response(data={'id':'container','uri':'https://rupload.facebook.com/upload'}),Response(data={'success':True}),*[Response(data={'status_code':'IN_PROGRESS'}) for _ in range(5)]])
        with patch('social_publish.time.sleep'):self.tick_due()
        self.assertEqual(store.get(draft['id'])['status'],'Processing')
        self.responses([Response(data={'status_code':'FINISHED'}),Response(data={'status_code':'FINISHED'}),Response(data={'id':'posted'}),Response(data={'permalink':'https://www.instagram.com/reel/posted/'})])
        self.tick_due();self.assertEqual(store.get(draft['id'])['status'],'Published')
        self.assertEqual(sum(c.args[0]=='POST' and c.args[1].endswith('/media') for c in self.transport.call_args_list),1)

    def test_crash_without_receipt_requires_check_instead_of_new_upload(self):
        draft=self.instagram();store.save(dict(draft,status='Starting'));self.tick_due()
        self.transport.assert_not_called();self.assertEqual(store.get(draft['id'])['status'],'Needs check')

    def test_cancel_preserves_video_and_copy_and_rejects_stale_cancellation(self):
        draft=self.instagram();fresh=schedule.cancel_local(draft['id'],draft['updated'])
        self.assertEqual(fresh['status'],'Draft');self.assertNotIn('publish_at',fresh)
        self.assertEqual(fresh['description'],draft['description']);self.assertEqual(self.video.read_bytes(),b'video bytes')
        self.tick_due();self.transport.assert_not_called()
        with self.assertRaises(ValueError):schedule.cancel_local(draft['id'],draft['updated'])

    def test_background_runner_retains_future_schedule_and_restarts(self):
        draft=self.instagram();children=[]
        real_spawn=subprocess.Popen
        def spawn(*args,**kwargs):
            child=real_spawn(*args,**kwargs);children.append(child);return child
        def wait_for_runner():
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                if schedule.runner_alive(self.root):return
                time.sleep(.05)
            self.fail('The local scheduling runner did not start')
        try:
            with patch('social_schedule.subprocess.Popen',side_effect=spawn):
                self.ensure_scheduler(self.root);wait_for_runner()
                self.ensure_scheduler(self.root);self.assertEqual(len(children),1)
                self.assertEqual(store.get(draft['id'])['status'],'Scheduled')
                children[0].terminate();children[0].wait(timeout=5)
                self.ensure_scheduler(self.root);wait_for_runner();self.assertEqual(len(children),2)
                self.assertEqual(store.get(draft['id'])['status'],'Scheduled')
            self.transport.assert_not_called()
        finally:
            for child in children:
                if child.poll() is None:child.terminate()
                child.wait(timeout=5)

    def test_failed_upload_reset_clears_expired_schedule(self):
        draft=self.instagram();store.save(dict(draft,status='Failed',container_id='container'))
        with patch.object(auth,'forget'):publisher.retry_failed(draft['id'])
        fresh=store.get(draft['id']);self.assertEqual(fresh['status'],'Draft');self.assertNotIn('publish_at',fresh)

    def test_ui_schedule_uses_displayed_text_and_enters_scheduled_list(self):
        workspace.save_text(self.row,'Keep your speed #fyp','A useful idea about keeping momentum.')
        workspace.save_preferences(self.root,projects=[str(self.folder.resolve())],made_for_kids=False,schedule_timezone='America/Chicago')
        app=AppTest.from_string(f"from pathlib import Path\nfrom publishing_workspace_ui import show\nshow(Path({str(self.root)!r}),lambda page:None)",default_timeout=15)
        self.responses([Response(headers={'Location':'https://www.googleapis.com/upload/session'}),Response(308),Response(201,{'id':'posted','status':{'privacyStatus':'private','publishAt':self.at}})])
        app.run();self.assertFalse(app.exception)
        next(c for c in app.checkbox if c.label=='Schedule this post').check().run()
        self.assertFalse(app.exception);self.assertEqual(len(app.date_input),1);self.assertEqual(len(app.time_input),1)
        app.date_input[0].set_value(date(2030,7,15));app.time_input[0].set_value(clock(18,0));app.run()
        self.assertEqual(app.date_input[0].value,date(2030,7,15));self.assertEqual(app.time_input[0].value,clock(18,0))
        next(b for b in app.button if b.label=='Schedule to My channel').click().run()
        self.assertFalse(app.exception);self.assertEqual(store.drafts()[0]['status'],'Scheduled')
        self.assertEqual(self.transport.call_args_list[0].kwargs['json']['status']['publishAt'],'2030-07-15T23:00:00Z')
        self.assertTrue(any(t.label=='Scheduled posts' for t in app.tabs))
        self.assertTrue(any(b.label=='Manage in YouTube Studio' for b in app.get('link_button')))

    def test_ui_local_schedule_can_be_cancelled_from_history_without_an_upload(self):
        self.instagram();workspace.save_preferences(self.root,projects=[str(self.folder.resolve())],account_id=self.account['id'])
        app=AppTest.from_string(f"from pathlib import Path\nfrom publishing_workspace_ui import show\nshow(Path({str(self.root)!r}),lambda page:None)",default_timeout=15)
        app.run();self.assertFalse(app.exception)
        next(b for b in app.button if b.label=='Cancel schedule & return to editing').click().run()
        self.assertFalse(app.exception);self.assertEqual(store.drafts()[0]['status'],'Draft');self.transport.assert_not_called()
        self.assertTrue(any(b.label=='Publish to My channel' for b in app.button))


if __name__=='__main__':unittest.main()
