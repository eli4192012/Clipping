import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import imageio_ffmpeg
import numpy as np
from sound_analysis import installed,scan,summarize,WEIGHTS_SHA
from curation_vision import checked


class SoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.silent=cls.root/'silent.mp4';cls.delayed=cls.root/'delayed.mkv'
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','color=black:s=32x32:r=5:d=2','-c:v','libx264',str(cls.silent)],check=True)
        subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','color=black:s=32x32:r=5:d=4','-itsoffset','2','-f','lavfi','-i','sine=frequency=440:sample_rate=16000:duration=2',
                        '-map','0:v','-map','1:a','-c:v','libx264','-c:a','pcm_s16le',str(cls.delayed)],check=True)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_silent_video_does_not_require_or_load_sound_model(self):
        project=dict(source=str(self.silent),folder=str(self.root),duration=2)
        with patch('sound_analysis.installed',side_effect=AssertionError('Model check unnecessary')):
            report=scan(project)
        self.assertEqual(report['status'],'No audio track');self.assertFalse(summarize(report,[dict(start=0,end=2)])['available'])

    def test_delayed_audio_is_padded_to_actual_source_time(self):
        from sound_worker import run
        chunks=[]
        def model(audio):
            chunks.append(audio.copy());count=max(1,int((len(audio)/16000-.96)/.48)+1)
            return [SimpleNamespace(numpy=lambda:np.tile([.9,.1],(count,1)))]
        with patch('sound_worker.load',return_value=(model,np.array(['Speech','Applause']))):
            report=run(dict(source=str(self.delayed),ffmpeg=imageio_ffmpeg.get_ffmpeg_exe(),duration=4))
        self.assertAlmostEqual(report['decoded_seconds'],4,places=2)
        self.assertLess(report['levels'][0]['rms_db'],-100);self.assertLess(report['levels'][1]['rms_db'],-100)
        self.assertGreater(report['levels'][2]['rms_db'],-30)
        self.assertTrue(all(f['end']<=4 for f in report['frames']))

    def test_modified_weights_cannot_be_treated_as_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);weights=root/'models/sound-yamnet/yamnet.h5';weights.parent.mkdir(parents=True);weights.write_bytes(b'model')
            python=root/'.venv-audio/bin/python';python.parent.mkdir(parents=True);python.touch()
            ready=dict(sha256=WEIGHTS_SHA,size=weights.stat().st_size,mtime_ns=weights.stat().st_mtime_ns)
            (weights.parent/'.ready').write_text(json.dumps(ready));self.assertTrue(installed(root))
            weights.write_bytes(b'changed');self.assertFalse(installed(root))

    def test_conflicting_visual_labels_are_rejected_or_left_unknown(self):
        raw=dict(shot='close_up',action_visible=True,reaction_visible=True,description='A seated person faces the camera.')
        result=checked(raw);self.assertIsNone(result['action_visible']);self.assertIsNone(result['reaction_visible'])
        self.assertEqual(len(result['uncertainty']),2)
        with self.assertRaises(ValueError):checked(dict(raw,shot='wide_action',description='A person speaks at a microphone.'))
        with self.assertRaises(ValueError):checked(dict(raw,action_visible='true'))

    def test_supported_visible_action_is_retained_without_claiming_completion(self):
        result=checked(dict(shot='wide_action',action_visible=True,reaction_visible=False,description='Players are running on a field.'))
        self.assertIs(result['action_visible'],True);self.assertFalse(result['uncertainty'])
