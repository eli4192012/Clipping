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
        self.patches=[patch('engine.export_clip',return_value=(self.video,self.srt)),patch('boundary_editor.editor',return_value=None),patch('clip_thumbnails.show'),patch('social_ui.composer'),patch('local_editor.installed',return_value=True),patch('upgrades.worker',side_effect=AssertionError('Unrequested inference')),patch('ui_jobs.run_job',side_effect=lambda key,work,estimate:work(lambda *args:None))]
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
