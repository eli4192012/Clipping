import unittest
from framing import choose_framing,blur_filter
class FramingTests(unittest.TestCase):
 def test_single_person_gets_safe_portrait(self):
  d=choose_framing([[(540,100,140,170)],[(560,100,140,170)],[(550,100,140,170)]],1280,720)
  self.assertEqual(d['kind'],'crop');self.assertLessEqual(d['x']+d['width'],1280);self.assertLessEqual(d['y']+d['height'],720)
  self.assertAlmostEqual(d['width']/d['height'],9/16,delta=.005)
 def test_two_people_keep_full_picture(self):
  self.assertEqual(choose_framing([[(100,100,120,160),(900,100,120,160)]]*3,1280,720)['kind'],'blur')
 def test_action_and_shot_changes_do_not_force_zoom(self):
  self.assertEqual(choose_framing([[],[],[]],1280,720)['kind'],'blur')
  self.assertEqual(choose_framing([[(100,100,140,160)],[(800,100,140,160)],[(400,100,140,160)]],1280,720)['kind'],'blur')
 def test_blur_uses_video_not_black_padding(self):
  self.assertNotIn('pad=',blur_filter());self.assertIn('boxblur',blur_filter());self.assertIn('overlay',blur_filter())

class CropFirstTests(unittest.TestCase):
 def test_existing_portrait_stays_unzoomed_without_faces(self):
  from framing import framing_filter
  d=choose_framing([],1080,1920)
  self.assertEqual(d['kind'],'native');self.assertNotIn('blur',framing_filter(d));self.assertNotIn('crop',framing_filter(d))
 def test_moving_subject_that_fits_is_not_automatically_blurred(self):
  samples=[[(400,150,80,90)],[(530,150,80,90)],[(650,150,80,90)]]
  d=choose_framing(samples,1280,720)
  self.assertEqual(d['kind'],'crop')
  for sample in samples:
   x,y,w,h=sample[0]
   self.assertLessEqual(d['x'],x-w*.2);self.assertGreaterEqual(d['x']+d['width'],x+w*1.2)
  self.assertEqual(d['width']*16,d['height']*9)
 def test_close_face_keeps_source_headroom_without_unnecessary_blur(self):
  d=choose_framing([[(530,0,140,200)]]*4,1280,720)
  self.assertEqual(d['kind'],'crop');self.assertEqual(d['y'],0)
 def test_wide_movement_retains_blur_fallback(self):
  d=choose_framing([[(300,100,120,160)],[(650,100,120,160)],[(500,100,120,160)]],1280,720)
  self.assertIn(d['kind'],('blur','blur_person'))
