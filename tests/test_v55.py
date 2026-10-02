import unittest
from presentation import LAYOUTS,default_layout,normalize_layout,layout_filter
from framing import AUTO,choose_framing
class UniversalFramingTests(unittest.TestCase):
 def test_vertical_default_is_automatic(self):
  self.assertEqual(default_layout(True),AUTO)
  self.assertEqual(default_layout(False),LAYOUTS[0])
 def test_legacy_layout_remains_compatible(self):
  self.assertEqual(normalize_layout('Portrait · automatic interview'),AUTO)
  self.assertEqual(layout_filter('Portrait · automatic interview'),layout_filter(AUTO))
 def test_manual_layouts_remain_explicit(self):
  for layout in LAYOUTS:self.assertEqual(normalize_layout(layout),layout)
 def test_uncertain_action_is_not_blindly_cropped(self):
  self.assertEqual(choose_framing([[],[],[]],1920,1080)['kind'],'blur')
