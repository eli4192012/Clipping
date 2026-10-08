"""Exercise real mixed-format joins, audio, caption offsets and saved combinations."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import av
import numpy as np
import imageio_ffmpeg
from combined_video import (export_combination, join_captions, register_clip, saved_clips,
                            new_draft, save_draft, drafts, move_clip)


class CombinedVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="combined clips' ")
        cls.root = Path(cls.tmp.name)
        for name in ('data', 'exports', 'work'):
            (cls.root/name).mkdir()
        cls.red = cls.root/'red.mp4'
        cls.blue = cls.root/'blue.mp4'
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=red:s=320x180:r=25:d=1.6',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100:duration=1.6',
                        '-c:v', 'libx264', '-c:a', 'aac', str(cls.red)], check=True, capture_output=True)
        subprocess.run([ffmpeg, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=blue:s=180x320:r=24:d=1.2',
                        '-vf', 'drawbox=x=0:y=0:w=8:h=ih:color=white:t=fill,drawbox=x=iw-8:y=0:w=8:h=ih:color=white:t=fill',
                        '-c:v', 'libx264', '-an', str(cls.blue)], check=True, capture_output=True)
        cls.red.with_suffix('.srt').write_text('1\n00:00:00,200 --> 00:00:01,000\nRed words.\n')
        cls.blue.with_suffix('.srt').write_text('1\n00:00:00,100 --> 00:00:00,700\nBlue words.\n')
        cls.clips = [dict(id=color, video=str(video), captions=str(video.with_suffix('.srt')), title=color.title(), project='Fixture')
                     for color, video in [('red', cls.red), ('blue', cls.blue)]]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def draft(self, clips=None):
        return dict(new_draft(), clips=list(clips or self.clips))

    def test_mixed_shapes_rates_and_silent_clip_preserve_order_audio_and_subtitles(self):
        states = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in (self.red, self.blue, self.red.with_suffix('.srt'), self.blue.with_suffix('.srt'))}
        progress = []
        result = export_combination(self.root, self.draft(), lambda p, label: progress.append(p))
        self.assertAlmostEqual(result['duration'], 2.9, delta=.12)
        self.assertEqual(progress, sorted(progress))
        self.assertEqual(progress[-1], 1.)
        captions = Path(result['captions']).read_text()
        self.assertIn('Red words.', captions)
        self.assertIn('Blue words.', captions)
        self.assertIn('00:00:01,700', captions)
        with av.open(result['video']) as media:
            video = media.streams.video[0]
            self.assertEqual((video.width, video.height), (1280, 720))
            self.assertTrue(media.streams.subtitles)
            self.assertEqual(media.streams.audio[0].sample_rate, 48000)
            self.assertEqual([c['metadata']['title'] for c in media.chapters()], ['Red', 'Blue'])
            frames = [(f.time, f.to_ndarray(format='rgb24')) for f in media.decode(video=0)]
        for at, channel in [(.5, 0), (2.1, 2)]:
            pixels = min(frames, key=lambda f: abs(f[0]-at))[1]
            self.assertEqual(int(pixels[300:400, 550:650].mean(axis=(0, 1)).argmax()), channel)
        portrait = min(frames, key=lambda f: abs(f[0]-2.1))[1]
        # Both edge markers survive inside the fitted portrait foreground.
        self.assertGreater(portrait[300:400, 442:448].mean(), 210)
        self.assertGreater(portrait[300:400, 831:837].mean(), 210)
        with av.open(result['video']) as media:
            audio = np.concatenate([f.to_ndarray() for f in media.decode(audio=0)], axis=1).mean(axis=0)
        block = audio[int(.4*48000):int(.8*48000)]
        peak = np.fft.rfftfreq(len(block), 1/48000)[np.abs(np.fft.rfft(block)).argmax()]
        self.assertAlmostEqual(peak, 440, delta=5)
        self.assertLess(np.abs(audio[int(2.1*48000):int(2.4*48000)]).max(), .001)
        self.assertEqual([x['title'] for x in result['timeline']], ['Red', 'Blue'])
        self.assertIn('00:00 Red', Path(result['chapters']).read_text())
        self.assertEqual(states, {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in states})

    def test_unchanged_export_reuses_cache_and_new_order_reuses_normalized_clips(self):
        result = export_combination(self.root, self.draft())
        with patch('combined_video._run', side_effect=AssertionError('Encoded unchanged assembly again')):
            self.assertEqual(export_combination(self.root, self.draft()), result)
        with patch('combined_video._normalize', side_effect=AssertionError('Encoded existing clip again')):
            reordered = export_combination(self.root, self.draft(list(reversed(self.clips))))
        self.assertNotEqual(reordered['video'], result['video'])
        self.assertEqual(reordered['timeline'][0]['title'], 'Blue')
        self.assertTrue(Path(result['video']).is_file())

    def test_vertical_dark_background_and_missing_subtitles_export_successfully(self):
        clips = [dict(c, captions=None) for c in self.clips]
        draft = dict(self.draft(clips), format='Vertical · 9:16', background='dark')
        result = export_combination(self.root, draft)
        self.assertEqual((result['width'], result['height']), (720, 1280))
        self.assertFalse(Path(result['captions']).read_text().strip())
        with av.open(result['video']) as media:
            self.assertFalse(media.streams.subtitles)
            self.assertTrue(media.streams.audio)

    def test_missing_clip_or_bad_captions_fail_before_encoding(self):
        with patch('combined_video._normalize', side_effect=AssertionError('Encoding should not start')):
            with self.assertRaisesRegex(ValueError, 'at least two'):
                export_combination(self.root, self.draft(self.clips[:1]))
            missing = dict(self.clips[0], video=str(self.root/'missing.mp4'))
            with self.assertRaises(FileNotFoundError):
                export_combination(self.root, self.draft([missing, self.clips[1]]))
            bad = self.root/'bad.srt'
            bad.write_text('1\ninvalid subtitle\n')
            with self.assertRaisesRegex(ValueError, 'valid SRT'):
                export_combination(self.root, self.draft([dict(self.clips[0], captions=str(bad)), self.clips[1]]))

    def test_long_timeline_caption_offsets_and_boundary_clamping(self):
        result = join_captions(self.clips, [3661.001, .5])
        self.assertIn('01:01:01,101 --> 01:01:01,501', result)
        self.assertEqual(result.count('Blue words.'), 1)

    def test_old_exports_and_new_indexed_clips_are_available_and_draft_order_persists(self):
        folder = self.root/'data/project'
        folder.mkdir(exist_ok=True)
        (folder/'project.json').write_text(json.dumps(dict(title='Original project')))
        (folder/'render-old.json').write_text(json.dumps([str(self.red), str(self.red.with_suffix('.srt'))]))
        self.red.with_suffix('.ass').write_text('Dialogue: 1,0:00:00.00,0:00:03.00,Title,,0,0,0,,Old\\Nhook')
        register_clip(folder, self.blue, self.blue.with_suffix('.srt'), 'Indexed blue', 'Original project')
        rows, errors = saved_clips(self.root)
        self.assertFalse(errors)
        self.assertEqual({r['title'] for r in rows}, {'Old hook', 'Indexed blue'})
        draft = self.draft()
        save_draft(self.root, draft)
        moved = move_clip(draft, 0, 1)
        save_draft(self.root, moved)
        self.assertEqual(next(d for d in drafts(self.root) if d['id'] == draft['id'])['clips'][0]['id'], 'blue')
        self.assertEqual(draft['clips'][0]['id'], 'red')
        with self.assertRaises(ValueError):
            save_draft(self.root, dict(draft, id='../escape'))


if __name__ == '__main__':
    unittest.main()
