import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import av
import numpy as np
import imageio_ffmpeg
from engine import export_clip,duration
from visual_pacing import plan_camera
from clip_thumbnails import generate,overlay_cover,clean_frame

class PackagedExportTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.source=cls.root/'source.mp4'
  ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
  cmd=[ffmpeg,'-v','error','-y','-f','lavfi','-i','color=red:s=640x720:r=25:d=12','-f','lavfi','-i','color=blue:s=640x720:r=25:d=12','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=12','-filter_complex','[0:v][1:v]hstack[v]','-map','[v]','-map','2:a','-c:v','libx264','-c:a','aac',str(cls.source)]
  subprocess.run(cmd,check=True,capture_output=True)
  cls.words=[]
  for speaker,start,text in [('A',0,'Here is the secret weapon.'),('B',7,'Here is my complete reply.')]:
   for i,t in enumerate(text.split()):cls.words.append(dict(text=t,start=start+i*.6,end=start+(i+1)*.6,speaker=speaker))
  cls.scene=dict(width=1280,height=720,samples=[dict(time=i,faces=[[250,100,100,130],[850,100,100,130]]) for i in (0,3,6,9,11)])
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_confirmed_camera_switch_preserves_audio_duration_and_caption_clock(self):
  package=dict(fingerprint='edit');options=dict(conversation='Active Speaker',speaker_mapping_confirmed=True,speaker_mapping_fingerprint='edit',speaker_positions={'A':'Left','B':'Right'})
  plan=plan_camera(self.scene,self.words,[dict(start=0,end=12)],package,options,'Podcast')
  style=dict(layout='Portrait · automatic',burn=True,title='Secret weapon',packaging_version=1,_visual_plan=plan,semantic_emphasis=True,_emphasis=dict(indices=[3,4]),emphasis_style='Gentle pop')
  with patch('engine.ROOT',self.root):video,srt=export_clip(self.source,0,12,self.words,presentation=style)
  self.assertAlmostEqual(duration(video),12,delta=.08)
  with av.open(str(video)) as media:
   self.assertEqual((media.streams.video[0].width,media.streams.video[0].height),(720,1280));self.assertTrue(media.streams.audio);self.assertTrue(media.streams.subtitles)
   frames=[(f.time,f.to_ndarray(format='rgb24')) for f in media.decode(video=0)]
  for at,channel in [(2,0),(9,2)]:
   rgb=min(frames,key=lambda x:abs(x[0]-at))[1][450:550,300:400].mean(axis=(0,1));self.assertEqual(int(rgb.argmax()),channel)
  self.assertIn('00:00:07,000',srt.read_text())
  self.assertEqual(video.with_suffix('.ass').read_text().count('\\t('),2)
  clean=clean_frame(video,2)
  self.assertIsNotNone(clean)
  self.assertEqual(clean.size,(720,1280))
  self.assertLess(np.asarray(clean)[:,:,1].max(),5) # no white/green burned captions or title
 def test_split_and_progressive_pacing_render_without_changing_speech(self):
  split=plan_camera(self.scene,self.words,[dict(start=0,end=12)],dict(fingerprint='x'),dict(conversation='Split Screen'),'Podcast')
  single=dict(width=1280,height=720,samples=[dict(time=i,faces=[[540,100,100,130]]) for i in (0,4,8,11)])
  pacing=plan_camera(single,self.words,[dict(start=0,end=12)],dict(sentences=[dict(start=0,text='Opening'),dict(start=5,text='Explanation')]),dict(pacing='Dynamic',conversation='Off'),'Interview')
  for plan in (split,pacing):
   with patch('engine.ROOT',self.root):video,srt=export_clip(self.source,0,12,self.words,presentation=dict(layout='Portrait · automatic',packaging_version=1,_visual_plan=plan))
   self.assertAlmostEqual(duration(video),12,delta=.08)
   with av.open(str(video)) as media:
    frames=[f.to_ndarray(format='rgb24') for f in media.decode(video=0)]
   self.assertTrue(frames);self.assertEqual(frames[0].shape,(1280,720,3))
   if plan['decision']['kind']=='split':
    self.assertEqual(int(frames[30][100:200,300:400].mean(axis=(0,1)).argmax()),0)
    self.assertEqual(int(frames[30][850:950,300:400].mean(axis=(0,1)).argmax()),2)
 def test_cover_cache_uses_three_distinct_frames_and_does_not_redo_analysis(self):
  cache,result=generate(self.source,self.root)
  self.assertEqual(result['sampled_frames'],8);self.assertEqual(len(result['options']),3)
  self.assertEqual(len({o['seconds'] for o in result['options']}),3)
  target=overlay_cover(cache,result['options'][0],'A real source quote')
  self.assertTrue(target.is_file())
  with patch('av.open',side_effect=AssertionError('decoded again')):
   self.assertEqual(generate(self.source,self.root),(cache,result))
   self.assertEqual(overlay_cover(cache,result['options'][0],'A real source quote'),target)
  self.assertEqual(overlay_cover(cache,result['options'][0],''),cache/result['options'][0]['file'])
