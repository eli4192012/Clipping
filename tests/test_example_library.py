import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import imageio_ffmpeg
from example_library import add_clip, available_references, directory, import_review, load, save_notes


def review_fixture(root):
    root = Path(root)
    source = root / 'original.mp4'
    source.write_bytes(b'preserved example media')
    transcript = root / 'transcript.json'
    transcript.write_text(json.dumps(dict(language='en', words=[], sentences=[], backend='Saved local transcript')))
    frames = root / 'frames.jpg'
    from PIL import Image
    Image.new('RGB', (20, 20), 'blue').save(frames)
    row = dict(sha256=hashlib.sha256(source.read_bytes()).hexdigest(), source=str(source),
               bytes=source.stat().st_size, filename=source.name, transcript=str(transcript),
               frames=str(frames), duration=25, text='A complete explanation.',
               actual_post_title='Trust your blockers #NFL', opening_text='Trust your blockers',
               content_format='Interview', label='Good pattern',
               editorial_observations=dict(strengths=['Specific opening'], cautions=['Check the tail'], role='Hook reference'),
               analytics={'Views': '1115', 'Engaged views': '560', 'Stayed to watch (%)': '55.1', 'Average percentage viewed (%)': '97.25'},
               association={'status': 'provisional', 'basis': 'Title and duration'}, performance_label='User-reported successful')
    return dict(examples=[row], archive_sha256='archive-fixture', export_period_from_filename=['2026-09-05', '2026-10-03'])


class ExampleLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.review = review_fixture(self.root)
        self.identity = self.review['examples'][0]['sha256']

    def tearDown(self):
        self.tmp.cleanup()

    def test_import_retains_originals_and_makes_independent_reference_assets(self):
        paths = [Path(self.review['examples'][0][key]) for key in ('source', 'transcript', 'frames')]
        before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
        self.assertEqual(import_review(self.root, self.review), 1)
        example = load(self.root)['examples'][0]
        self.assertEqual(example['posted_title'], 'Trust your blockers #NFL')
        self.assertEqual(example['analytics']['Engaged views'], '560')
        self.assertFalse(example['analytics_match_confirmed'])
        self.assertEqual(available_references(self.root), [])
        for path, original in zip(paths, before):
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), original)
        paths[1].unlink()
        paths[2].unlink()
        self.assertEqual(load(self.root)['examples'][0]['transcript']['backend'], 'Saved local transcript')
        self.assertTrue((directory(self.root) / example['frame_sheet']).is_file())

    def test_reimport_preserves_manual_titles_notes_confirmation_and_status(self):
        import_review(self.root, self.review)
        save_notes(self.root, self.identity, posted_title='My reviewed title #Colts', notes='Keep this lesson.',
                   status='Ready for future reference', analytics_match_confirmed=True)
        original = (directory(self.root) / 'library.json').read_bytes()
        self.assertEqual(import_review(self.root, self.review), 0)
        self.assertEqual((directory(self.root) / 'library.json').read_bytes(), original)
        self.assertEqual(len(available_references(self.root)), 1)

    def test_changed_source_rejects_import_without_saving_partial_records(self):
        Path(self.review['examples'][0]['source']).write_bytes(b'changed media')
        with self.assertRaisesRegex(ValueError, 'changed'):
            import_review(self.root, self.review)
        self.assertFalse(directory(self.root).exists())

    def test_corrupted_library_is_preserved_instead_of_replaced(self):
        path = directory(self.root) / 'library.json'
        path.parent.mkdir(parents=True)
        path.write_text('{broken library')
        with self.assertRaisesRegex(ValueError, 'preserved'):
            import_review(self.root, self.review)
        self.assertEqual(path.read_text(), '{broken library')

    def test_protected_source_transcript_and_analytics_cannot_be_overwritten_by_notes(self):
        import_review(self.root, self.review)
        for key in ('source', 'source_sha256', 'transcript', 'analytics'):
            with self.assertRaises(ValueError):
                save_notes(self.root, self.identity, **{key: 'replacement'})
        self.assertEqual(load(self.root)['examples'][0]['analytics']['Views'], '1115')

    def test_excluded_reference_is_not_available_and_media_loss_preserves_notes(self):
        import_review(self.root, self.review)
        save_notes(self.root, self.identity, status='Ready for future reference')
        self.assertEqual(len(available_references(self.root)), 1)
        save_notes(self.root, self.identity, status='Excluded')
        self.assertFalse(available_references(self.root))
        Path(self.review['examples'][0]['source']).unlink()
        self.assertEqual(load(self.root)['examples'][0]['transcript_text'], 'A complete explanation.')

    def test_invalid_upload_does_not_create_library_media(self):
        with self.assertRaisesRegex(ValueError, 'playable'):
            add_clip(self.root, b'not a video', 'bad.mp4', 'Invalid example')
        self.assertFalse(directory(self.root).exists())

    def test_real_uploaded_media_and_duplicate_preserve_saved_notes(self):
        video = self.root / 'tiny.mp4'
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-f', 'lavfi', '-i',
                        'color=blue:s=64x96:r=10:d=0.5', '-c:v', 'libx264', '-an', str(video)],
                       check=True, capture_output=True)
        example, added = add_clip(self.root, video.read_bytes(), video.name, 'My clip', 'My posted title #NFL', 'Podcast')
        self.assertTrue(added)
        self.assertAlmostEqual(example['duration'], .5, places=1)
        self.assertEqual(Path(example['source']).read_bytes(), video.read_bytes())
        save_notes(self.root, example['id'], notes='Manual notes stay here.')
        repeated, added = add_clip(self.root, video.read_bytes(), video.name, 'Different name')
        self.assertFalse(added)
        self.assertEqual(repeated['notes'], 'Manual notes stay here.')
        self.assertEqual(len(load(self.root)['examples']), 1)
