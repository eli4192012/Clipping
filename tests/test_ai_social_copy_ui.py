import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from test_shorts_editor import fixture
from test_ai_social_copy import checked_copy
from shorts_editor import compile_plan,editorial_units

ROOT=Path(__file__).resolve().parents[1]


class AISocialCopyUITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
        c,s,w,raw,_=fixture();plan=compile_plan(raw,c,editorial_units(c,s,w),w,30)
        plan.update(meaning_preserved=True,supported_variants=[])
        self.primary=dict(c,edit_plan=plan,source_candidate=c,start=plan['ranges'][0]['start'],end=plan['ranges'][-1]['end'],text=plan['final_transcript'],title=plan['title'],passed=True)
        self.analysis=self.folder/'clips-fixture.json';self.analysis.write_text(json.dumps([self.primary]))
        (self.folder/'transcript.json').write_text(json.dumps(dict(words=w,sentences=s,language='en')))
        self.source=self.folder/'source.mp4';self.source.write_bytes(b'Fingerprint fixture')
        self.video=self.folder/'render.mp4';self.video.write_bytes(b'Render fixture')
        self.srt=self.folder/'render.srt';self.srt.write_text('1\n00:00:00,000 --> 00:00:01,000\nTest.\n')
        self.settings=dict(mode='Interview',minimum=5,maximum=30,vision=False,semantic=True,quality='Balanced',portrait=False,shorts_editor=True,windows=6,editor_model='qwen3-4b')
        self.state=dict(page='editor',project=dict(source=str(self.source),folder=str(self.folder),title='Interview fixture',duration=25),settings=self.settings,result_path=str(self.analysis),clip_index=0)
        self.patches=[patch('engine.export_clip',return_value=(self.video,self.srt)),patch('boundary_editor.editor',return_value=None),patch('clip_thumbnails.show'),patch('social_ui.composer'),patch('local_editor.installed',return_value=True),patch('upgrades.worker',side_effect=AssertionError('Unrequested inference')),patch('ui_jobs.run_job',side_effect=lambda key,work,estimate:work(lambda *args:None)),patch('posting_style.load',return_value={})]
        self.export=self.patches[0].start()
        self.composer=None
        for i,p in enumerate(self.patches[1:],1):
            mock=p.start()
            if i==3:self.composer=mock
        self.app=self.new_app()

    def new_app(self):
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
        for k,v in self.state.items():app.session_state[k]=v
        return app

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()

    def test_generation_fills_title_inline_and_description_without_rerender_or_publish(self):
        app=self.app.run();self.assertFalse(app.exception)
        self.assertEqual([t.label for t in app.tabs],['Edit','Look','Social media','Advanced'])
        self.assertFalse(any(t.label.endswith('hashtags') for t in app.text_input))
        with patch('upgrades.worker',return_value=checked_copy()) as worker:
            next(b for b in app.button if b.label=='Generate title & description with AI').click().run()
        self.assertFalse(app.exception);worker.assert_called_once()
        self.assertEqual(worker.call_args.args[1]['text'],self.primary['text'])
        self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,'Keep your speed and momentum #Momentum #Speed')
        description=next(t for t in app.text_area if t.label=='YouTube description').value
        self.assertNotIn('#',description);self.assertIn('avoiding cuts',description)
        self.assertEqual(self.composer.call_args.args[-1]['title'],'Keep your speed and momentum #Momentum #Speed')
        self.assertEqual(self.composer.call_args.args[-1]['description'],description)
        self.assertEqual(self.export.call_count,1)
        reopened=self.new_app().run();self.assertFalse(reopened.exception)
        self.assertEqual(next(t for t in reopened.text_input if t.label=='YouTube title').value,'Keep your speed and momentum #Momentum #Speed')
        self.assertEqual(self.export.call_count,1)

    def test_failed_regeneration_preserves_manual_saved_copy(self):
        app=self.app.run();self.assertFalse(app.exception)
        next(t for t in app.text_input if t.label=='YouTube title').set_value('My manual title #Speed')
        next(t for t in app.text_area if t.label=='YouTube description').set_value('My manually reviewed summary.')
        next(b for b in app.button if b.label=='Save YouTube Shorts text').click().run()
        saved=(self.folder/'platform-posts-v517.json').read_bytes()
        with patch('upgrades.worker',side_effect=RuntimeError('Inference failed')):
            next(b for b in app.button if b.label=='Generate fresh text').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Inference failed' in e.value for e in app.error))
        self.assertEqual((self.folder/'platform-posts-v517.json').read_bytes(),saved)
        self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,'My manual title #Speed')
        self.assertEqual(self.export.call_count,1)

    def test_source_check_failure_shows_reason_and_keeps_saved_manual_text(self):
        app=self.app.run()
        next(t for t in app.text_input if t.label=='YouTube title').set_value('My verified title #Speed')
        next(t for t in app.text_area if t.label=='YouTube description').set_value('My verified summary.')
        next(b for b in app.button if b.label=='Save YouTube Shorts text').click().run()
        saved=(self.folder/'platform-posts-v517.json').read_bytes()
        report=json.dumps(dict(reason="Source says 'golden signature', not 'bold signature'.",unsupported_claims=['wrong prize']))
        failure=RuntimeError('Local worker failed: Traceback (most recent call last):\n  File "/private/quality_worker.py", line 100\nValueError: The AI posting text did not pass its source check. '+report)
        with patch('upgrades.worker',side_effect=failure):
            next(b for b in app.button if b.label=='Generate fresh text').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('golden signature' in e.value and 'Generate fresh text' in e.value for e in app.error))
        self.assertFalse(any('Traceback' in e.value or '/private/' in e.value for e in app.error))
        self.assertEqual((self.folder/'platform-posts-v517.json').read_bytes(),saved)
        self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,'My verified title #Speed')
        self.assertEqual(next(t for t in app.text_area if t.label=='YouTube description').value,'My verified summary.')
        self.assertEqual(self.export.call_count,1)

    def test_editor_refreshes_old_loaded_post_form_without_losing_saved_copy(self):
        import importlib
        import packaging_ui
        app=self.app.run();self.assertFalse(app.exception)
        next(t for t in app.text_input if t.label=='YouTube title').set_value('My saved title #Speed')
        next(b for b in app.button if b.label=='Save YouTube Shorts text').click().run()
        saved=(self.folder/'platform-posts-v517.json').read_bytes()
        def legacy_post_form(folder,package):
            raise AssertionError('The old posting form should be refreshed before use.')
        with patch.object(packaging_ui,'POST_FORM_API',0,create=True),patch.object(packaging_ui,'post_form',legacy_post_form),patch('importlib.reload',wraps=importlib.reload) as reload:
            app.run()
            self.assertFalse(app.exception)
            reload.assert_called_once_with(packaging_ui)
            self.assertEqual(packaging_ui.POST_FORM_API,5)
            self.assertTrue(any(b.label=='Generate title & description with AI' for b in app.button))
            self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,'My saved title #Speed')
        self.assertEqual((self.folder/'platform-posts-v517.json').read_bytes(),saved)
        self.assertEqual(self.export.call_count,1)

    def test_current_post_form_does_not_reload_on_editor_reruns(self):
        with patch('importlib.reload',side_effect=AssertionError('Current posting code should not be reloaded')):
            app=self.app.run();self.assertFalse(app.exception)
            app.run();self.assertFalse(app.exception)
        self.assertEqual(self.export.call_count,1)

    def test_personal_style_is_visible_and_sent_to_worker_without_rendering_again(self):
        from posting_style import build_profile
        profile=build_profile(dict(channel='Example channel',records=[dict(id=1,title='Speed and momentum',description='Momentum helps a run develop without extra cuts.')]))
        app=self.app.run()
        with patch('posting_style.load',return_value=profile),patch('upgrades.worker',return_value=checked_copy()) as worker:
            app.run()
            self.assertTrue(any('Example channel writing style' in c.value for c in app.caption))
            next(b for b in app.button if b.label=='Generate title & description with AI').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(worker.call_args.args[1]['posting_style']['fingerprint'],profile['fingerprint'])
        self.assertEqual(self.export.call_count,1)

    def open_social(self,app):
        app.session_state['clip-editor-tab-'+str(self.analysis)+'-0']='Social media'
        return app.run()

    def test_opening_social_generates_once_without_using_transcript_as_default_description(self):
        app=self.app.run();self.assertFalse(app.exception)
        self.assertEqual(next(t for t in app.text_area if t.label=='YouTube description').value,'')
        with patch('upgrades.worker',return_value=checked_copy()) as worker:
            self.open_social(app)
            self.assertFalse(app.exception);worker.assert_called_once()
        self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,checked_copy()['title'])
        self.assertTrue(any(t.value=='Keep your speed and momentum' for t in app.title))
        self.assertEqual(self.export.call_count,1)
        self.open_social(self.new_app())  # Saved AI copy reopens without another worker call.
        self.assertEqual(self.export.call_count,1)

    def test_failed_auto_generation_is_not_retried_on_each_rerun(self):
        app=self.app.run()
        with patch('upgrades.worker',side_effect=RuntimeError('No checked text')) as worker:
            self.open_social(app)
            self.assertFalse(app.exception);worker.assert_called_once()
        app.run();self.assertFalse(app.exception)
        self.assertEqual(next(t for t in app.text_area if t.label=='YouTube description').value,'')
        with patch('upgrades.worker',return_value=checked_copy()) as worker:
            next(b for b in app.button if b.label=='Generate title & description with AI').click().run()
            self.assertFalse(app.exception);worker.assert_called_once()

    def test_legacy_quoted_description_is_rewritten_without_replacing_edited_title_or_other_platform(self):
        self.app.run()
        package=json.loads(next((self.folder/'packaging-v517').glob('*.json')).read_text())
        old=dict(package['posting']['YouTube Shorts'],title='My hand-written title')
        posts={'YouTube Shorts':old,'TikTok':dict(caption='My reviewed TikTok caption',hashtags=[])}
        (self.folder/'platform-posts-v517.json').write_text(json.dumps({package['fingerprint']:posts}))
        with patch('upgrades.worker',return_value=checked_copy()) as worker:
            app=self.open_social(self.new_app());self.assertFalse(app.exception);worker.assert_called_once()
        from social_copy import inline_title
        self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,inline_title(old['title'],old['hashtags']))
        self.assertEqual(next(t for t in app.text_area if t.label=='YouTube description').value,checked_copy()['description'])
        saved=json.loads((self.folder/'platform-posts-v517.json').read_text())[package['fingerprint']]
        self.assertEqual(saved['TikTok'],posts['TikTok'])

    def test_saved_manual_summary_and_title_are_not_automatically_replaced(self):
        app=self.app.run()
        next(t for t in app.text_input if t.label=='YouTube title').set_value('My reviewed title')
        next(t for t in app.text_area if t.label=='YouTube description').set_value('My reviewed teaser.')
        next(b for b in app.button if b.label=='Save YouTube Shorts text').click().run()
        saved=(self.folder/'platform-posts-v517.json').read_bytes()
        self.open_social(app);self.assertFalse(app.exception)
        self.assertEqual((self.folder/'platform-posts-v517.json').read_bytes(),saved)
        self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,'My reviewed title')

    def test_alternative_hook_is_saved_and_keeps_description_without_extra_inference(self):
        with patch('upgrades.worker',return_value=checked_copy()):app=self.open_social(self.app)
        self.assertFalse(app.exception)
        choice=checked_copy()['title_options'][1]
        next(b for b in app.button if b.label==choice).click().run()
        self.assertFalse(app.exception)
        self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,choice)
        self.assertEqual(next(t for t in app.text_area if t.label=='YouTube description').value,checked_copy()['description'])
        reopened=self.open_social(self.new_app());self.assertFalse(reopened.exception)
        self.assertEqual(next(t for t in reopened.text_input if t.label=='YouTube title').value,choice)
        self.assertEqual(self.export.call_count,1)


class DraftCopyUITests(unittest.TestCase):
    def test_reviewed_draft_uses_new_text_only_on_explicit_apply_and_save(self):
        from social_store import identity as draft_identity
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);video=root/'clip.mp4';video.write_bytes(b'video')
            candidate=dict(start=0,end=5);run=root/'clips.json';run.write_text('[]')
            account=dict(id='youtube:channel',platform='youtube',name='Channel')
            key=draft_identity(root,run,candidate,account['id'],'render')
            draft=dict(id=key,status='Draft',title='Old reviewed title',description='Old reviewed description',privacy='private',made_for_kids=False,share_to_feed=True,account_name='Channel',account_id=account['id'],platform='youtube',folder=tmp)
            payload=dict(folder=tmp,run=str(run),candidate=candidate,video=str(video),render_id='render',copy=dict(title='New AI title #Momentum',description='New AI summary.'))
            script='from pathlib import Path\nfrom social_ui import composer\n'+f'p={payload!r}\ncomposer(Path(p["folder"]),Path(p["run"]),p["candidate"],Path(p["video"]),p["render_id"],p["copy"])'
            with patch('social_store.accounts',return_value=[account]),patch('social_store.get',return_value=draft),patch('social_ui.draft_panel'),patch('social_store.save_draft') as save,patch('social_store.validate'),patch('social_publish.publish',side_effect=AssertionError('Published while generating')):
                app=AppTest.from_string(script).run();self.assertFalse(app.exception)
                self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,'Old reviewed title')
                next(b for b in app.button if b.label=='Use current posting text in this draft').click().run()
                self.assertFalse(app.exception);save.assert_not_called()
                self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,'New AI title #Momentum')
                next(b for b in app.button if b.label=='Save draft & review').click().run()
                self.assertFalse(app.exception);save.assert_called_once()
                self.assertEqual(save.call_args.args[0]['title'],'New AI title #Momentum')
                self.assertEqual(save.call_args.args[0]['description'],'New AI summary.')
                self.assertEqual(save.call_args.args[0]['privacy'],'private')


if __name__=='__main__':unittest.main()
