import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from combined_video import new_draft, save_draft, drafts


class CombinedVideoUITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.clips = []
        for i in range(3):
            video = self.root/f'clip-{i}.mp4'
            video.write_bytes(b'Video placeholder; real exports are tested separately')
            self.clips.append(dict(id=str(i), video=str(video), captions=None, title=f'Clip {i+1}', project=f'Project {i%2}', duration=10.))
        self.draft = dict(new_draft(), clips=self.clips[:2])
        save_draft(self.root, self.draft)
        self.mock = patch('combined_video_ui.saved_clips', return_value=(self.clips, []))
        self.mock.start()
        self.app = AppTest.from_string(f'from pathlib import Path\nfrom combined_video_ui import show\nshow(Path({str(self.root)!r}))', default_timeout=10)

    def tearDown(self):
        self.mock.stop()
        self.tmp.cleanup()

    def current(self):
        return next(d for d in drafts(self.root) if d['id'] == self.draft['id'])

    def test_wide_default_order_changes_and_added_clips_persist(self):
        app = self.app.run()
        self.assertFalse(app.exception)
        self.assertEqual(next(s for s in app.selectbox if s.label == 'Video shape').value, 'Wide · 16:9')
        next(b for b in app.button if b.key == f'down-{self.draft["id"]}-0').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.current()['clips'][0]['id'], '1')
        next(m for m in app.multiselect if m.label == 'Choose clips to add').set_value(['2'])
        next(b for b in app.button if b.label == 'Add selected clips').click().run()
        self.assertFalse(app.exception)
        self.assertEqual([c['id'] for c in self.current()['clips']], ['1', '0', '2'])
        next(t for t in app.text_input if t.label == 'Video name').set_value('My full video')
        next(b for b in app.button if b.label == 'Save video settings').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.current()['title'], 'My full video')

    def test_removing_only_changes_the_playlist_and_single_clip_cannot_export(self):
        app = self.app.run()
        next(b for b in app.button if b.key == f'remove-{self.draft["id"]}-0').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(self.current()['clips']), 1)
        self.assertTrue(next(b for b in app.button if b.label == 'Export combined video').disabled)
        self.assertTrue(all(Path(c['video']).is_file() for c in self.clips))

    def test_export_saves_a_reopenable_result_without_inference(self):
        video = self.root/'combined.mp4'
        video.write_bytes(b'Render placeholder')
        captions = video.with_suffix('.srt'); captions.write_text('')
        chapters = video.with_suffix('.txt'); chapters.write_text('00:00 Clip 1\n00:10 Clip 2\n')
        result = dict(video=str(video), captions=str(captions), chapters=str(chapters), duration=20., width=1280, height=720)
        with patch('combined_video_ui.run_job', side_effect=lambda key, work, estimate: work(lambda *args: None)), \
             patch('combined_video_ui.export_combination', return_value=result) as export, \
             patch('upgrades.worker', side_effect=AssertionError('Unexpected inference')):
            app = self.app.run()
            next(b for b in app.button if b.label == 'Export combined video').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(self.current()['last_export'], result)
            self.assertEqual(export.call_count, 1)
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(export.call_count, 1)

    def test_sidebar_opens_the_builder_without_an_active_project(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'), default_timeout=15)
        app.session_state['page'] = 'source'
        with patch('combined_video_ui.show') as show:
            app.run()
            self.assertFalse(app.exception)
            next(b for b in app.button if b.label == 'Combine clips').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['page'], 'combine')
            show.assert_called_once()


if __name__ == '__main__':
    unittest.main()
