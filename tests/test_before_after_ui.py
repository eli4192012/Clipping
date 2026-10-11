from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import unittest

import test_before_after
from before_after import directory
from project_store import read


class BeforeAfterUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):test_before_after.BeforeAfterTests.setUpClass()
    @classmethod
    def tearDownClass(cls):test_before_after.BeforeAfterTests.tearDownClass()
    def setUp(self):
        self.fixture=test_before_after.BeforeAfterTests();self.fixture.setUp()
        self.report=self.fixture.run_comparison();self.root=self.fixture.root
        self.script=f'from pathlib import Path\nfrom before_after_ui import show\nshow(Path({str(self.root)!r}),lambda page:None)'
        self.app=AppTest.from_string(self.script)
    def tearDown(self):self.fixture.tearDown()

    def test_viewing_saved_comparison_never_loads_model_or_renders(self):
        with patch('upgrades.worker',side_effect=AssertionError('Unexpected inference')),patch('engine.export_clip',side_effect=AssertionError('Unexpected render')):
            app=self.app.run();self.assertFalse(app.exception)
            self.assertEqual([s.value for s in app.subheader][:2],['Before','After'])
            self.assertTrue(any('saved cut' in c.value.lower() for c in app.caption))
            self.assertTrue(any('My manual description' in m.value for m in app.markdown))

    def test_user_rating_survives_rerun_without_editing_the_saved_report(self):
        app=self.app.run();path=directory(self.root)/(self.report['id']+'.json');saved=path.read_bytes()
        app.radio[0].set_value('About the same');app.text_area[0].set_value('The opening needs clearer wording.')
        next(b for b in app.button if b.label=='Save comparison review').click().run()
        self.assertFalse(app.exception);self.assertEqual(path.read_bytes(),saved)
        review=read(directory(self.root)/'ratings'/(self.report['id']+'.json'),{})
        self.assertEqual(review['choice'],'About the same')
        fresh=AppTest.from_string(self.script)
        fresh.run();self.assertEqual(fresh.text_area[0].value,review['notes'])

    def test_missing_media_keeps_notes_readable_and_prevents_rating(self):
        Path(self.report['after']['video']['path']).unlink()
        app=self.app.run();self.assertFalse(app.exception)
        self.assertTrue(any('changed or is missing' in w.value for w in app.warning))
        self.assertTrue(next(b for b in app.button if b.label=='Save comparison review').disabled)
        self.assertTrue(any('Golden signature' in m.value for m in app.markdown))

    def test_main_sidebar_page_opens_without_a_project_or_model_job(self):
        import importlib,interview_integrity
        root=Path(__file__).resolve().parents[1]
        app=AppTest.from_file(str(root/'app.py'));app.session_state.page='before_after'
        with patch('before_after_ui.reports',return_value=[]),patch('upgrades.worker',side_effect=AssertionError('Unexpected inference')), \
             patch.object(interview_integrity,'QUESTION_COUNT_API',0),patch('importlib.reload',wraps=importlib.reload) as reload:
            app.run();self.assertFalse(app.exception)
            self.assertIn(interview_integrity,[c.args[0] for c in reload.call_args_list])
            self.assertTrue(any('No comparisons yet' in i.value for i in app.info))
            self.assertTrue(any(b.label=='Before & after' for b in app.button))


if __name__=='__main__':unittest.main()
