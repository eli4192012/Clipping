"""Exercise real encoded video, audio and subtitle joins rather than command mocks."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import av
import numpy as np
import imageio_ffmpeg
from engine import export_clip, duration
from presentation import LAYOUTS

class TimelineExportTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);(cls.root/'exports').mkdir()
  cls.source=cls.root/'source.mp4'
  cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y']
  for color in ('red','green','blue'):cmd+=['-f','lavfi','-i',f'color=c={color}:s=160x120:r=25:d=2']
  for hz in (440,660,880):cmd+=['-f','lavfi','-i',f'sine=frequency={hz}:sample_rate=48000:duration=2']
  cmd+=['-filter_complex','[0:v][3:a][1:v][4:a][2:v][5:a]concat=n=3:v=1:a=1[v][a]', '-map','[v]','-map','[a]','-c:v','libx264','-c:a','aac',str(cls.source)]
  subprocess.run(cmd,check=True,capture_output=True)
  cls.words=[dict(start=.5,end=1.5,text='Red.'),dict(start=2.5,end=3.5,text='Green.'),dict(start=4.5,end=5.5,text='Blue.')]
  cls.ranges=[dict(start=.4,end=1.8),dict(start=4.3,end=5.8)]
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_real_audio_video_and_captions_follow_identical_joins(self):
  with patch('engine.ROOT',self.root):
   video,srt=export_clip(self.source,0,6,self.words,ranges=self.ranges,presentation=dict(layout=LAYOUTS[0],burn=True,title='Red then blue'))
  self.assertAlmostEqual(duration(video),2.9,delta=.08)
  captions=srt.read_text();self.assertIn('Red.',captions);self.assertIn('Blue.',captions);self.assertNotIn('Green.',captions)
  self.assertIn('00:00:01,600',captions)
  with av.open(str(video)) as media:
   self.assertTrue(media.streams.subtitles)
   frames=[(f.time,f.to_ndarray(format='rgb24')) for f in media.decode(video=0)]
  for at,channel in [(.2,0),(2.5,2)]:
   pixels=min(frames,key=lambda f:abs(f[0]-at))[1][:15,:15].mean(axis=(0,1))
   self.assertEqual(int(pixels.argmax()),channel)
  with av.open(str(video)) as media:
   samples=np.concatenate([f.to_ndarray() for f in media.decode(audio=0)],axis=1).mean(axis=0)
  for at,hz in [(.4,440),(2.2,880)]:
   block=samples[int(at*48000):int((at+.2)*48000)]
   peak=np.fft.rfftfreq(len(block),1/48000)[np.abs(np.fft.rfft(block)).argmax()]
   self.assertAlmostEqual(peak,hz,delta=10)
 def test_silent_source_and_complex_portrait_layout(self):
  silent=self.root/'silent.mp4'
  subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-i',str(self.source),'-an','-c:v','copy',str(silent)],check=True,capture_output=True)
  with patch('engine.ROOT',self.root):
   video,_=export_clip(silent,0,6,[],ranges=self.ranges,presentation=dict(layout=LAYOUTS[1],burn=True,title='Two ranges'))
  with av.open(str(video)) as media:
   self.assertFalse(media.streams.audio)
   self.assertEqual((media.streams.video[0].width,media.streams.video[0].height),(720,1280))
  self.assertAlmostEqual(duration(video),2.9,delta=.08)
