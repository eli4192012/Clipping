import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from test_shorts_editor import fixture
from shorts_editor import compile_plan,editorial_units

ROOT=Path(__file__).resolve().parents[1]

class PackagingUITests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
  c,s,w,raw,_=fixture();plan=compile_plan(raw,c,editorial_units(c,s,w),w,30)
  plan.update(meaning_preserved=True,supported_variants=[],validation=dict(standalone=True,faithful=True,complete_ending=True))
  self.primary=dict(c,edit_plan=plan,source_candidate=c,start=plan['ranges'][0]['start'],end=plan['ranges'][-1]['end'],text=plan['final_transcript'],title=plan['title'],passed=True,reason='Checked edit.')
  self.analysis=self.folder/'clips-fixture.json';self.analysis.write_text(json.dumps([self.primary]))
  (self.folder/'transcript.json').write_text(json.dumps(dict(words=w,sentences=s,language='en')))
  self.source=self.folder/'source.mp4';self.source.write_bytes(b'Fingerprint fixture; export mocked')
  self.video=self.folder/'render.mp4';self.video.write_bytes(b'Render fixture')
  self.srt=self.folder/'render.srt';self.srt.write_text('1\n00:00:00,000 --> 00:00:01,000\nTest.\n')
  self.settings=dict(mode='Interview',minimum=5,maximum=30,vision=False,semantic=True,quality='Balanced',portrait=False,shorts_editor=True,windows=6,category_selection=['Interview'])
  self.app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=20)
  for key,value in dict(page='editor',project=dict(source=str(self.source),folder=str(self.folder),title='Interview fixture',duration=25),settings=self.settings,result_path=str(self.analysis),clip_index=0).items():self.app.session_state[key]=value
  self.patches=[patch('engine.export_clip',return_value=(self.video,self.srt)),patch('boundary_editor.editor',return_value=None),patch('clip_thumbnails.show'),patch('social_ui.composer'),patch('upgrades.worker',side_effect=AssertionError('Unnecessary AI work')),patch('ui_jobs.run_job',side_effect=lambda key,work,estimate:work(lambda *args:None))]
  self.export=self.patches[0].start()
  for p in self.patches[1:]:p.start()
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def test_review_screen_preserves_editor_and_uses_final_packages_without_model_work(self):
  app=self.app.run();self.assertFalse(app.exception)
  self.assertEqual([t.label for t in app.tabs],['Edit','Look','Post','Advanced'])
  self.assertTrue(any(b.label=='v5.17' for b in app.button))
  self.assertEqual(self.export.call_args.kwargs['ranges'],self.primary['edit_plan']['ranges'])
  self.assertTrue(self.export.call_args.kwargs['presentation']['semantic_emphasis'])
  self.assertEqual(next(s for s in app.selectbox if s.label=='Visual pacing').value,'Subtle')
  self.assertTrue(any(e.label=='B-roll suggestions' for e in app.expander))
  self.assertTrue(any(e.label=='YouTube Shorts posting package' for e in app.expander))
  with patch('final_package.hook_from_final',side_effect=AssertionError('Package regenerated')):app.run()
  self.assertFalse(app.exception);self.assertEqual(self.export.call_count,1)
  next(b for b in app.button if b.label=='Restore suggested boundaries').click().run()
  self.assertFalse(app.exception);self.assertFalse(json.loads(self.analysis.with_suffix('.edits.json').read_text()))
  next(s for s in app.selectbox if s.label=='Edit version').set_value('Original moment').run()
  self.assertFalse(app.exception);self.assertIsNone(self.export.call_args.kwargs['ranges'])
 def test_user_can_disable_hook_and_pacing_and_saved_look_is_retained(self):
  app=self.app.run();self.assertFalse(app.exception)
  next(s for s in app.selectbox if s.label=='Visual pacing').set_value('Off')
  next(t for t in app.text_input if t.label=='Opening hook · leave blank to hide').set_value('')
  next(b for b in app.button if b.label=='Apply style').click().run()
  self.assertFalse(app.exception)
  style=next(iter(json.loads(self.analysis.with_suffix('.styles.json').read_text()).values()))
  self.assertEqual(style['title'],'');self.assertEqual(style['pacing'],'Off')
  self.assertEqual(self.export.call_args.kwargs['presentation']['title'],'')
  next(t for t in app.text_input if t.label=='YouTube title').set_value('My saved posting title')
  next(b for b in app.button if b.label=='Save YouTube Shorts text').click().run()
  self.assertFalse(app.exception)
  app.run();self.assertFalse(app.exception)
  self.assertEqual(next(t for t in app.text_input if t.label=='YouTube title').value,'My saved posting title')
 def test_legacy_manual_style_does_not_silently_gain_automatic_effects(self):
  key=f"{self.primary['start']}-{self.primary['end']}:Balanced"
  old=dict(layout='Portrait · two speakers',burn=False,title='Manual title',position=.15,second=.8,trim_edges=False)
  self.analysis.with_suffix('.styles.json').write_text(json.dumps({key:old}))
  self.app.run();self.assertFalse(self.app.exception)
  self.assertEqual(self.export.call_args.kwargs['presentation'],old)
  self.assertEqual(json.loads(self.analysis.with_suffix('.styles.json').read_text()),{key:old})
 def test_collection_assesses_candidates_without_rendering_or_reanalysis(self):
  self.app.session_state['page']='results'
  self.app.run();self.assertFalse(self.app.exception)
  self.assertTrue(any(e.label=='Suggested edit assessment' for e in self.app.expander))
  self.export.assert_not_called()
