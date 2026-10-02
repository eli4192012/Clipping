import unittest
from publishing import normalize,fallback,clean_saved
class Publishing(unittest.TestCase):
 def test_title_limit(self):
  for n in range(1,220):
   c=normalize('Title '*n,'Description')
   self.assertLessEqual(len(c['title']),100)
   self.assertEqual(set(c),{'title','description'})
 def test_legacy_copy_keeps_title_and_description(self):
  self.assertEqual(clean_saved(dict(title='Title',hashtags='#Colts',combined='Title #Colts',description='Text')),dict(title='Title',description='Text'))
 def test_fallback_has_only_requested_fields(self):
  c=fallback({'title':'An interview'},'Nico Collins may play.')
  self.assertIn('may play',c['description']);self.assertEqual(set(c),{'title','description'})
