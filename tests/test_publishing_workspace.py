import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch,Mock

import social_store as store
import social_auth as auth
import social_publish as publisher
import publishing_workspace as workspace
from clip_queue import QueueStore
from project_store import read,write,save_run,library
from queue_runner import process_item
from streamlit.testing.v1 import AppTest
from test_social import Response


SETTINGS=dict(mode='Podcast',minimum=5,maximum=30,windows=6,vision=False,semantic=True,
              quality='Higher quality',shorts_editor=True,portrait=True,editor_model='qwen3-4b')
TITLE='Keep your speed #Colts #NFL #Football #fyp'
DESCRIPTION='Keeping momentum can matter more than adding another move.'


class PublishingWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.folder=self.root/'data/project';self.folder.mkdir(parents=True)
        (self.root/'work').mkdir()
        source=self.folder/'source.mp4';source.write_bytes(b'preserved source')
        self.project=dict(folder=str(self.folder),source=str(source),title='Colts interview',duration=30)
        self.candidate=dict(start=2.,end=12.,text='You keep your speed and momentum.',title='Momentum',passed=True)
        self.run=self.folder/'clips-v10-Podcast-5-30-all-ai.json'
        write(self.run,[self.candidate]);save_run(self.project,SETTINGS,self.run);write(self.folder/'ui-settings.json',SETTINGS)
        self.video=self.root/'exports/clip-one.mp4';self.video.parent.mkdir();self.video.write_bytes(b'finished export')
        self.srt=self.video.with_suffix('.srt');self.srt.write_text('1\n00:00:00,000 --> 00:00:10,000\nYou keep your speed and momentum.\n')
        self.package=dict(fingerprint='package-one',final_transcript=self.candidate['text'],posting={})
        self.row=workspace.register_render(self.folder,self.run,self.candidate,self.package,SETTINGS,self.video,self.srt,'render-one')
        write(self.folder/'render-render-one.json',[str(self.video),str(self.srt)])
        self.db=patch.object(store,'DB',self.root/'data/social.sqlite3');self.db.start()
        self.launch=patch('clip_queue.ensure_runner');self.launch.start()
        self.account=dict(id='youtube:channel',name='Test channel',platform='youtube',remote_id='channel');store.save_account(self.account)
        self.before={p:p.read_bytes() for p in (source,self.video,self.srt,self.run)}

    def tearDown(self):self.launch.stop();self.db.stop();self.tmp.cleanup()

    def save_copy(self):return workspace.save_text(self.row,TITLE,DESCRIPTION)

    def test_project_selection_persists_and_does_not_include_other_projects(self):
        workspace.add_project(self.root,self.folder);workspace.add_project(self.root,self.folder)
        self.assertEqual(workspace.preferences(self.root)['projects'],[str(self.folder.resolve())])
        with patch('social_copy.get_copy',side_effect=AssertionError('Browsing must not infer')):
            rows,errors=workspace.catalog(self.root,[self.folder])
            self.assertEqual(len(rows),1);self.assertFalse(errors)
            self.assertEqual(workspace.catalog(self.root,[])[0],[])
        for p,data in self.before.items():self.assertEqual(p.read_bytes(),data)

    def test_catalog_keeps_exact_render_package_and_merges_duplicate_manifests(self):
        write(self.folder/'render-second-manifest.json',[str(self.video),str(self.srt)])
        rows,_=workspace.catalog(self.root,[self.folder]);self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['package'],self.package);self.assertEqual(rows[0]['candidate'],dict(start=2.,end=12.))

    def test_old_project_without_folder_field_still_opens_its_saved_exports(self):
        write(self.folder/'project.json',{k:v for k,v in self.project.items() if k!='folder'})
        rows,errors=workspace.catalog(self.root,[self.folder])
        self.assertFalse(errors);self.assertEqual(len(rows),1)

    def test_preparation_keeps_successful_text_when_another_clip_fails_source_check(self):
        second=dict(self.row,id='another',title='Another clip')
        with patch('publishing_workspace.catalog',return_value=([self.row,second],[])),patch('publishing_workspace.prepare_text',side_effect=[dict(title=TITLE,description=DESCRIPTION),ValueError('Source check failed')]) as prepare:
            with self.assertRaisesRegex(ValueError,'successful text are kept'):
                workspace.prepare_project(self.project,SETTINGS,str(self.run),[dict(video=str(self.video))])
            self.assertEqual(prepare.call_count,2)

    def test_older_export_uses_actual_caption_speech_without_retranscription(self):
        (self.folder/'publishing-clips.json').unlink()
        rows,errors=workspace.catalog(self.root,[self.folder]);self.assertFalse(errors)
        self.assertEqual(rows[0]['package']['final_transcript'],self.candidate['text'])
        self.assertEqual(rows[0]['run'],str(self.run.resolve()))
        self.assertFalse(all(workspace.posting_text(rows[0]).values()))

    def test_manual_text_is_preserved_and_ai_runs_only_for_missing_text(self):
        self.save_copy()
        with patch('social_copy.get_copy',side_effect=AssertionError('Repeated AI')):
            self.assertEqual(workspace.prepare_text(self.row)['title'],TITLE)
        path=self.folder/'publishing-text.json';path.unlink()
        with patch('social_copy.get_copy',return_value=dict(title=TITLE,description=DESCRIPTION)) as generate:
            workspace.prepare_text(self.row);generate.assert_called_once()
        self.assertEqual(workspace.posting_text(self.row)['description'],DESCRIPTION)

    def test_existing_editor_text_and_inline_tags_are_reused(self):
        write(self.folder/'platform-posts-v517.json',{'package-one':{'YouTube Shorts':dict(title='Keep your speed',description=DESCRIPTION,hashtags=['#fyp'],copy_origin='manual')}})
        self.assertEqual(workspace.posting_text(self.row)['title'],'Keep your speed #fyp')
        with patch('social_copy.get_copy',side_effect=AssertionError('Replaced manual text')):workspace.prepare_text(self.row)

    def test_publishing_reads_checked_ai_cache_without_opening_social_editor(self):
        from test_ai_social_copy import TEXT,checked_copy
        from social_copy import get_copy
        row=dict(self.row,package=dict(self.package,final_transcript=TEXT))
        with patch('posting_style.load',return_value={}),patch('upgrades.worker',return_value=checked_copy()):
            generated=get_copy(self.folder,row['package'],SETTINGS)
        self.assertFalse((self.folder/'publishing-text.json').exists())
        with patch('posting_style.load',return_value={}),patch('upgrades.worker',side_effect=AssertionError('Repeated inference')):
            self.assertEqual(workspace.posting_text(row),dict(title=generated['title'],description=generated['description']))

    def test_automatic_text_queue_respects_an_explicit_pause(self):
        queue=QueueStore(self.root);queue.set_enabled(False)
        workspace.queue_text(self.root,[self.row]);self.assertFalse(queue.enabled())
        self.assertEqual(queue.items()[0]['state'],'queued')

    def test_incomplete_manual_editor_copy_is_not_overwritten_by_automatic_ai(self):
        write(self.folder/'platform-posts-v517.json',{'package-one':{'YouTube Shorts':dict(title='My unfinished title',description='',copy_origin='manual')}})
        self.assertEqual(workspace.queue_text(self.root,[self.row]),[])
        self.assertEqual(workspace.posting_text(self.row)['title'],'My unfinished title #fyp')
        self.assertIn('manual posting text is incomplete',workspace.text_status(self.row)['error'])
        with patch('social_copy.get_copy',side_effect=AssertionError('Replaced manual edit')):
            with self.assertRaisesRegex(ValueError,'manual posting text is incomplete'):workspace.prepare_text(self.row)

    def test_no_speech_or_failed_generation_never_saves_a_transcript_description(self):
        empty=dict(self.row,package=dict(self.package,final_transcript=''))
        with self.assertRaises(ValueError):workspace.prepare_text(empty)
        with patch('social_copy.get_copy',side_effect=ValueError('Source check failed')):
            with self.assertRaises(ValueError):workspace.prepare_text(self.row)
        self.assertFalse((self.folder/'publishing-text.json').exists())

    def test_one_publish_click_freezes_visible_text_and_uses_existing_backend(self):
        with patch('social_publish.publish',return_value=dict(status='Processing')) as publish:
            result=workspace.publish_clip(self.row,self.account,'Better momentum',DESCRIPTION,'public',False)
        self.assertEqual(result['status'],'Processing');self.assertTrue(publish.call_args.kwargs['prevent_duplicate'])
        draft=store.get(publish.call_args.args[0])
        self.assertEqual(draft['title'],'Better momentum #fyp');self.assertEqual(draft['description'],DESCRIPTION)
        self.assertEqual(draft['privacy'],'public');self.assertFalse(draft['made_for_kids'])
        self.assertEqual(publish.call_args.kwargs['expected_updated'],draft['updated'])

    def test_youtube_upload_sends_exact_title_and_description_and_retains_receipt(self):
        secrets={}
        def secret(key,value=None):
            if value is not None:secrets[key]=value
            return secrets.get(key)
        responses=[Response(headers={'Location':'https://www.googleapis.com/upload/session'}),Response(308),Response(201,{'id':'posted','status':{'privacyStatus':'public'}})]
        with patch.object(auth,'secret',side_effect=secret),patch.object(auth,'access',return_value='test-token'),patch.object(auth,'request',side_effect=responses) as request:
            result=workspace.publish_clip(self.row,self.account,TITLE,DESCRIPTION,'public',False)
        self.assertEqual(result['status'],'Processing')
        sent=request.call_args_list[0].kwargs['json'];self.assertEqual(sent['snippet']['title'],TITLE)
        self.assertEqual(sent['snippet']['description'],DESCRIPTION)
        self.assertEqual(store.get(result['id'])['remote_id'],'posted')

    def test_changed_file_unknown_audience_and_empty_copy_do_not_publish(self):
        with patch('social_publish.publish') as publish:
            with self.assertRaises(ValueError):workspace.publish_clip(self.row,self.account,TITLE,DESCRIPTION,'public',None)
            with self.assertRaises(ValueError):workspace.publish_clip(self.row,self.account,TITLE,'','public',False)
            self.video.write_bytes(b'changed export')
            with self.assertRaises(ValueError):workspace.publish_clip(self.row,self.account,TITLE,DESCRIPTION,'public',False)
            publish.assert_not_called()

    def test_existing_attempt_blocks_another_version_and_backend_checks_under_upload_lock(self):
        with patch('social_publish.publish') as publish:
            workspace.publish_clip(self.row,self.account,TITLE,DESCRIPTION,'public',False)
            draft=store.get(publish.call_args.args[0]);store.save(dict(draft,status='Processing'))
            with self.assertRaises(ValueError):workspace.publish_clip(self.row,self.account,TITLE,DESCRIPTION,'public',False)
        second=dict(draft,id='racing-draft',status='Draft');store.save(second)
        with patch.object(auth,'access') as access,patch.object(auth,'request') as request:
            with self.assertRaises(auth.SocialError):publisher.publish(second['id'],prevent_duplicate=True)
            access.assert_not_called();request.assert_not_called()

    def test_instagram_places_title_hashtags_and_description_in_one_caption(self):
        account=dict(self.account,id='instagram:channel',platform='instagram');store.save_account(account)
        with patch('social_publish.publish') as publish:
            workspace.publish_clip(self.row,account,TITLE,DESCRIPTION,'public',None)
        draft=store.get(publish.call_args.args[0]);self.assertEqual(draft['description'],TITLE+'\n\n'+DESCRIPTION)

    def test_instagram_draft_title_can_be_edited_without_repeating_its_old_title(self):
        account=dict(self.account,id='instagram:channel',platform='instagram');store.save_account(account)
        with patch('social_publish.publish'):
            workspace.publish_clip(self.row,account,TITLE,DESCRIPTION,'public',None)
        workspace.save_preferences(self.root,projects=[str(self.folder.resolve())],account_id=account['id'])
        app=AppTest.from_string(f"from pathlib import Path\nfrom publishing_workspace_ui import show\nshow(Path({str(self.root)!r}),lambda page:None)",default_timeout=15)
        with patch('social_publish.publish',side_effect=lambda *args,**kwargs:store.save(dict(store.get(args[0]),status='Processing'))) as publish:
            app.run();self.assertFalse(app.exception)
            self.assertEqual(next(i for i in app.text_area if i.label=='Description about this clip').value,DESCRIPTION)
            next(i for i in app.text_input if i.label=='Title with hashtags').set_value('New momentum #fyp')
            next(b for b in app.button if b.label=='Publish to Test channel').click().run()
            self.assertFalse(app.exception);self.assertEqual(publish.call_count,1)
            self.assertEqual(store.get(publish.call_args.args[0])['description'],'New momentum #fyp\n\n'+DESCRIPTION)

    def test_preparation_is_durable_reuses_selection_and_respects_pause(self):
        store_queue=QueueStore(self.root);store_queue.set_enabled(False)
        with patch('clip_queue.ensure_runner'):
            items=workspace.queue_preparation(self.root,library(self.root/'data'))
            again=workspace.queue_preparation(self.root,library(self.root/'data'))
        self.assertEqual(items[0]['id'],again[0]['id']);self.assertFalse(store_queue.enabled())
        settings=items[0]['settings'];self.assertTrue(settings['publishing_prepare'])
        store_queue.set_enabled(True);item=store_queue.claim()
        with patch('jobs.analyze',side_effect=AssertionError('Repeated analysis')),patch('queue_exports.export_suggestions',return_value=[dict(video=str(self.video))]),patch('publishing_workspace.prepare_project') as prepare:
            process_item(store_queue,item);prepare.assert_called_once()
        self.assertEqual(store_queue.get(item['id'])['result'],str(self.run.resolve()))
        for p,data in self.before.items():self.assertEqual(p.read_bytes(),data)

    def test_partial_analysis_is_not_queued_for_automatic_preparation(self):
        write(self.run.with_suffix('.diagnostics.json'),dict(partial_analysis=True))
        with patch('clip_queue.ensure_runner'):
            self.assertEqual(workspace.queue_preparation(self.root,library(self.root/'data')),[])

    def test_ui_shows_ready_title_and_posts_once_from_a_single_button(self):
        self.save_copy();workspace.save_preferences(self.root,projects=[str(self.folder.resolve())],privacy='public',made_for_kids=False)
        app=AppTest.from_string(f"from pathlib import Path\nfrom publishing_workspace_ui import show\nshow(Path({str(self.root)!r}),lambda page:None)",default_timeout=15)
        with patch('social_publish.publish',side_effect=lambda *args,**kwargs:store.save(dict(store.get(args[0]),status='Processing'))) as publish:
            app.run();self.assertFalse(app.exception)
            self.assertTrue(any(metric.label=='Ready clips' and metric.value=='1' for metric in app.metric))
            self.assertEqual(next(i for i in app.text_input if i.label=='Title with hashtags').value,TITLE)
            next(b for b in app.button if b.label=='Publish to Test channel').click().run()
            self.assertFalse(app.exception);self.assertEqual(publish.call_count,1)
            app.run();self.assertFalse(app.exception);self.assertEqual(publish.call_count,1)
            self.assertFalse(any(b.label=='Publish to Test channel' for b in app.button))

    def test_expired_account_shows_a_direct_reconnect_route_without_uploading(self):
        self.save_copy();store.save_account(dict(self.account,connection_error=auth.OAUTH_ERRORS['invalid_grant']))
        workspace.save_preferences(self.root,projects=[str(self.folder.resolve())])
        app=AppTest.from_string(f"from pathlib import Path\nfrom publishing_workspace_ui import show\nshow(Path({str(self.root)!r}),lambda page:None)",default_timeout=15)
        with patch('social_publish.publish',side_effect=AssertionError('Reconnect uploaded a clip')):
            app.run();self.assertFalse(app.exception)
            self.assertTrue(any('reconnect YouTube' in w.value for w in app.warning))
            self.assertTrue(any(b.label=='Reconnect in Accounts' for b in app.button))

    def test_ui_missing_copy_can_be_saved_without_inference_and_unknown_audience_blocks_publish(self):
        workspace.save_preferences(self.root,projects=[str(self.folder.resolve())])
        app=AppTest.from_string(f"from pathlib import Path\nfrom publishing_workspace_ui import show\nshow(Path({str(self.root)!r}),lambda page:None)",default_timeout=15)
        with patch('social_copy.get_copy',side_effect=AssertionError('Browsing ran AI')):
            app.run();self.assertFalse(app.exception)
            self.assertTrue(next(b for b in app.button if b.label=='Publish to Test channel').disabled)
            next(i for i in app.text_input if i.label=='Title with hashtags').set_value(TITLE)
            next(i for i in app.text_area if i.label=='Description about this clip').set_value(DESCRIPTION)
            next(b for b in app.button if b.label=='Save posting text').click().run()
            self.assertFalse(app.exception);self.assertEqual(workspace.posting_text(self.row)['title'],TITLE)

    def test_ui_successful_retry_replaces_old_preparation_failure(self):
        self.save_copy();workspace.save_preferences(self.root,projects=[str(self.folder.resolve())])
        failed=dict(project=self.project,settings=dict(publishing_prepare=True),created=1,state='failed',error='Old source check failure')
        completed=dict(failed,created=2,state='completed',error='')
        app=AppTest.from_string(f"from pathlib import Path\nfrom publishing_workspace_ui import show\nshow(Path({str(self.root)!r}),lambda page:None)",default_timeout=15)
        with patch('clip_queue.QueueStore') as queue:
            queue.return_value.items.return_value=[failed,completed]
            app.run();self.assertFalse(app.exception)
            self.assertFalse(any('Old source check failure' in warning.value for warning in app.warning))
            self.assertTrue(any(metric.label=='Ready clips' and metric.value=='1' for metric in app.metric))

    def test_sidebar_publishing_opens_without_active_project(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15)
        app.session_state['page']='source'
        with patch('publishing_workspace_ui.show') as show,patch('channel_watch.ensure_watcher'),patch('clip_queue.resume_enabled_queue'):
            app.run();self.assertFalse(app.exception)
            next(b for b in app.button if b.label=='Publishing').click().run()
            self.assertFalse(app.exception);self.assertEqual(app.session_state['page'],'publishing');show.assert_called_once()

    def test_automatic_text_job_is_deduplicated_and_failure_waits_for_explicit_retry(self):
        queue=QueueStore(self.root)
        first=workspace.queue_text(self.root,[self.row])
        self.assertEqual(len(first),1);self.assertTrue(queue.enabled())
        self.assertEqual(workspace.queue_text(self.root,[self.row]),[])
        item=queue.claim()
        with patch('social_copy.get_copy',side_effect=ValueError('Source check rejected draft')),patch('jobs.analyze',side_effect=AssertionError('Repeated analysis')),patch('queue_exports.export_suggestions',side_effect=AssertionError('Repeated render')):
            with self.assertRaises(ValueError):process_item(queue,item)
        queue.finish(item['id'],'Source check rejected draft')
        self.assertEqual(workspace.queue_text(self.root,[self.row]),[])
        self.assertIn('Source check',workspace.text_status(self.row)['error'])
        retry=workspace.queue_text(self.root,[self.row],retry=True)
        self.assertEqual(len(retry),1);self.assertNotEqual(retry[0]['id'],item['id'])
        for p,data in self.before.items():self.assertEqual(p.read_bytes(),data)

    def test_existing_export_prepares_without_source_or_saved_analysis_settings(self):
        write(self.folder/'project.json',dict(title='Existing project',source=''))
        row=dict(self.row,settings={})
        queue=QueueStore(self.root);workspace.queue_text(self.root,[row]);item=queue.claim()
        with patch('social_copy.get_copy',return_value=dict(title=TITLE,description=DESCRIPTION)),patch('jobs.analyze',side_effect=AssertionError('Repeated analysis')),patch('queue_exports.export_suggestions',side_effect=AssertionError('Repeated render')):
            process_item(queue,item)
        self.assertEqual(workspace.posting_text(row)['description'],DESCRIPTION)
        self.assertFalse(workspace.text_status(row)['error'])

    def test_ai_cannot_replace_text_edited_while_generation_runs(self):
        def generate(*args,**kwargs):
            workspace.save_text(self.row,'My reviewed title #fyp','My reviewed description.')
            return dict(title=TITLE,description=DESCRIPTION)
        with patch('social_copy.get_copy',side_effect=generate):workspace.prepare_text(self.row)
        self.assertEqual(workspace.posting_text(self.row)['title'],'My reviewed title #fyp')

    def test_changed_export_does_not_receive_text_for_queued_old_media(self):
        queue=QueueStore(self.root);workspace.queue_text(self.root,[self.row]);item=queue.claim()
        self.video.write_bytes(b'new export requires its own text')
        with patch('social_copy.get_copy',side_effect=AssertionError('Wrong media copy')):
            with self.assertRaisesRegex(ValueError,'export changed'):process_item(queue,item)
        self.assertFalse((self.folder/'publishing-text.json').exists())

    def test_automatic_generation_preserves_reviewed_drafts_and_upload_receipts(self):
        with patch('social_publish.publish'):workspace.publish_clip(self.row,self.account,TITLE,DESCRIPTION,'public',False)
        (self.folder/'publishing-text.json').unlink()
        draft=store.drafts()[0]
        self.assertEqual(workspace.queue_text(self.root,[self.row]),[])
        store.save(dict(draft,status='Scheduled',remote_id='existing-receipt'))
        before=store.get(draft['id'])
        self.assertEqual(workspace.queue_text(self.root,[self.row],retry=True),[])
        self.assertEqual(store.get(draft['id']),before)

    def test_ui_automatically_queues_then_shows_saved_generated_copy(self):
        workspace.save_preferences(self.root,projects=[str(self.folder.resolve())])
        app=AppTest.from_string(f"from pathlib import Path\nfrom publishing_workspace_ui import show\nshow(Path({str(self.root)!r}),lambda page:None)",default_timeout=15)
        with patch('social_copy.get_copy',side_effect=AssertionError('Inference blocked the page')):app.run()
        self.assertFalse(app.exception);queue=QueueStore(self.root);self.assertEqual(len(queue.items()),1)
        item=queue.claim()
        with patch('social_copy.get_copy',return_value=dict(title=TITLE,description=DESCRIPTION)):
            process_item(queue,item)
        queue.finish(item['id']);app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m.label=='Ready clips' and m.value=='1' for m in app.metric))
        self.assertEqual(next(i for i in app.text_input if i.label=='Title with hashtags').value,TITLE)
        self.assertEqual(next(i for i in app.text_area if i.label=='Description about this clip').value,DESCRIPTION)

    def test_large_ready_list_keeps_all_clips_accessible_on_pages(self):
        workspace.save_preferences(self.root,projects=[str(self.folder.resolve())])
        rows=[dict(self.row,id=f'clip-{i}',project_title='Project') for i in range(25)]
        app=AppTest.from_string(f"from pathlib import Path\nfrom publishing_workspace_ui import show\nshow(Path({str(self.root)!r}),lambda page:None)",default_timeout=15)
        with patch('publishing_workspace.catalog',return_value=(rows,[])),patch('publishing_workspace.queue_text'),patch('publishing_workspace.posting_text',return_value=dict(title=TITLE,description=DESCRIPTION)):
            app.run();self.assertFalse(app.exception)
            self.assertEqual(len([i for i in app.text_input if i.label=='Title with hashtags']),12)
            next(i for i in app.number_input if i.label=='Ready clip page').set_value(3).run()
            self.assertFalse(app.exception)
            self.assertEqual(len([i for i in app.text_input if i.label=='Title with hashtags']),1)
            self.assertTrue(any('25–25 of 25' in c.value for c in app.caption))


if __name__=='__main__':unittest.main()
