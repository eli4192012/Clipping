import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from example_library import import_review, load
from test_example_library import review_fixture

ROOT = Path(__file__).resolve().parents[1]


class ExampleLibraryUITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.review = review_fixture(self.root)
        import_review(self.root, self.review)
        self.app = self.new_app()

    def new_app(self):
        return AppTest.from_string('from example_library_ui import show\nshow(' + repr(str(self.root)) + ')', default_timeout=10)

    def tearDown(self):
        self.tmp.cleanup()

    def test_shows_correct_metrics_titles_and_provisional_match_without_model_work(self):
        with patch('upgrades.worker', side_effect=AssertionError('Unrequested inference')):
            app = self.app.run()
        self.assertFalse(app.exception)
        self.assertEqual({m.label: m.value for m in app.metric},
                         {'Views': '1115', 'Engaged views': '560', 'Stayed to watch': '55.1%', 'Average viewed': '97.25%'})
        self.assertTrue(any('not confirmed' in w.value for w in app.warning))
        self.assertTrue(any('Trust your blockers #NFL' in t.value for t in app.markdown))

    def test_saved_review_notes_and_status_survive_reopening(self):
        app = self.app.run()
        next(t for t in app.text_area if t.label == 'Your notes').set_value('Use the concrete benefit as the hook.')
        next(s for s in app.selectbox if s.label == 'Reference status').set_value('Ready for future reference')
        next(c for c in app.checkbox if c.label.startswith('I confirmed')).check()
        next(b for b in app.button if b.label == 'Save example notes').click().run()
        self.assertFalse(app.exception)
        reopened = self.new_app().run()
        self.assertFalse(reopened.exception)
        self.assertEqual(next(t for t in reopened.text_area if t.label == 'Your notes').value, 'Use the concrete benefit as the hook.')
        self.assertEqual(load(self.root)['examples'][0]['status'], 'Ready for future reference')
        self.assertFalse(any('not confirmed' in w.value for w in reopened.warning))

    def test_search_and_filter_do_not_delete_examples(self):
        app = self.app.run()
        next(t for t in app.text_input if t.label == 'Find an example').set_value('No such video').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('No examples match' in e.value for e in app.info))
        self.assertEqual(len(load(self.root)['examples']), 1)

    def test_missing_original_keeps_notes_and_transcript_visible(self):
        Path(self.review['examples'][0]['source']).unlink()
        app = self.app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any('original clip is missing' in w.value for w in app.warning))
        self.assertTrue(any('A complete explanation.' in m.value for m in app.markdown))

    def test_main_app_page_opens_without_project_or_inference(self):
        app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=15)
        app.session_state['page'] = 'examples'
        with patch('example_library_ui.show') as show, patch('upgrades.worker', side_effect=AssertionError('Unrequested inference')):
            app.run()
        self.assertFalse(app.exception)
        show.assert_called_once_with(ROOT)
        self.assertTrue(any(b.label == 'Example library' for b in app.button))
