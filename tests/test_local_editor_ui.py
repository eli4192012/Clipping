import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from local_editor import QWEN35,QWEN3

ROOT=Path(__file__).resolve().parents[1]


class LocalEditorUITests(unittest.TestCase):
    def setUp(self):
        self.models=tempfile.TemporaryDirectory()
        self.addCleanup(self.models.cleanup)
        self.speech=Path(self.models.name)/'whisper-base'
        self.speech.mkdir()
        # Availability only: inference is forbidden in these settings-screen tests.
        (self.speech/'model.bin').write_bytes(b'UI test marker, not model weights')
        marker=patch('engine.SPEECH',self.speech)
        marker.start();self.addCleanup(marker.stop)

    def test_selector_keeps_recommended_default_and_saves_explicit_new_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);source=folder/'source.mp4';source.write_bytes(b'fixture')
            speech=dict(language='en',sentences=[],words=[])
            path=folder/'transcript.json';path.write_text(json.dumps(speech));before=path.stat().st_mtime_ns
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=15)
            app.session_state['page']='settings'
            app.session_state['project']=dict(source=str(source),folder=tmp,title='Editor comparison',duration=60)
            app.session_state['settings']=dict(mode='Interview',minimum=5,maximum=30,category_selection=['Interview'],auto_mode=False,quality='Balanced',resource_defaults=1)
            with patch('local_editor.installed',return_value=True),patch('project_covers.cover_html',return_value=''),patch('upgrades.worker',side_effect=AssertionError('Unexpected inference')):
                app.run();self.assertFalse(app.exception)
                select=next(s for s in app.selectbox if s.label=='AI editor')
                self.assertEqual(select.value,QWEN3)
                self.assertIn('experimental',select.options[0])
                select.set_value(QWEN35).run();self.assertFalse(app.exception)
                self.assertEqual(json.loads((folder/'ui-settings.json').read_text())['editor_model'],QWEN35)
                self.assertFalse(next(b for b in app.button if b.label=='Find my clips →').disabled)
                next(s for s in app.selectbox if s.label=='AI editor').set_value(QWEN3).run();self.assertFalse(app.exception)
                self.assertEqual(json.loads((folder/'ui-settings.json').read_text())['editor_model'],QWEN3)
            self.assertEqual(path.stat().st_mtime_ns,before)

    def test_missing_new_model_blocks_only_that_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);source=folder/'source.mp4';source.write_bytes(b'fixture')
            app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=15)
            app.session_state['page']='settings'
            app.session_state['project']=dict(source=str(source),folder=tmp,title='Missing model',duration=60)
            app.session_state['settings']=dict(mode='Interview',minimum=5,maximum=30,category_selection=['Interview'],auto_mode=False,quality='Balanced',resource_defaults=1,editor_model=QWEN35)
            with patch('local_editor.installed',side_effect=lambda key:key==QWEN3),patch('project_covers.cover_html',return_value=''):
                app.run();self.assertFalse(app.exception)
                self.assertTrue(next(b for b in app.button if b.label=='Find my clips →').disabled)
                next(s for s in app.selectbox if s.label=='AI editor').set_value(QWEN3).run();self.assertFalse(app.exception)
                self.assertFalse(next(b for b in app.button if b.label=='Find my clips →').disabled)
                (self.speech/'model.bin').unlink()
                app.run();self.assertFalse(app.exception)
                self.assertTrue(next(b for b in app.button if b.label=='Find my clips →').disabled)


if __name__=='__main__':unittest.main()
