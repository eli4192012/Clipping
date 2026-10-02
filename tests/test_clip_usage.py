import tempfile,unittest
from clip_usage import is_used,set_used
class Usage(unittest.TestCase):
 def test_persists_and_can_be_unchecked(self):
  with tempfile.TemporaryDirectory() as d:
   c=dict(start=1,end=10,title='Old')
   self.assertFalse(is_used(d,'run.json',c));set_used(d,'run.json',c,True)
   self.assertTrue(is_used(d,'run.json',dict(c,title='New')))
   self.assertFalse(is_used(d,'other.json',c))
   set_used(d,'run.json',c,False);self.assertFalse(is_used(d,'run.json',c))
