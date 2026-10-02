import math,unittest
from boundary_editor import check_boundaries,adjacent_time

class PreciseBoundaryTests(unittest.TestCase):
 def setUp(self):
  self.words=[dict(start=1.,end=1.4,text='Colts'),dict(start=1.5,end=2.,text='win.')]
  self.sentences=[dict(start=1.,end=2.,text='Colts win.')]
 def test_cut_words_warn_and_only_expand(self):
  result=check_boundaries(self.words,self.sentences,1.2,1.8,5)
  self.assertEqual(len(result['warnings']),2)
  self.assertEqual(result['suggestion'],(.92,2.08))
 def test_gap_inside_sentence_is_not_reported_as_cut_word(self):
  result=check_boundaries(self.words,self.sentences,1.45,2.1,5)
  self.assertIn('sentence',result['warnings'][0]);self.assertIsNone(result['suggestion'])
 def test_clean_bounds_have_no_warning(self):
  self.assertEqual(check_boundaries(self.words,self.sentences,.9,2.1,5)['warnings'],[])
 def test_bad_times_are_rejected(self):
  for start,end in [(2,1),(math.nan,2),(0,6),(-1,1)]:
   self.assertIsNone(check_boundaries([],[],start,end,5)['suggestion'])
   self.assertTrue(check_boundaries([],[],start,end,5)['warnings'])
 def test_unanswered_question_flagged(self):
  result=check_boundaries([dict(start=1,end=2,text='Why?')],[],0,3,4)
  self.assertIn('question',result['warnings'][0])
 def test_vfr_frame_steps_use_actual_pts(self):
  times=[1.,1.033,1.091,1.15]
  self.assertEqual(adjacent_time(times,1.033,1),1.091)
  self.assertEqual(adjacent_time(times,1.033,-1),1.)
  self.assertEqual(adjacent_time(times,1.15,1),1.15)
 def test_suspicious_long_word_timing_not_auto_repaired(self):
  result=check_boundaries([dict(start=0,end=10,text='bad')],[],4,6,12)
  self.assertIsNone(result['suggestion'])
 def test_source_edges_clamp_suggestion(self):
  result=check_boundaries([dict(start=0,end=1,text='Hi')],[],.1,.9,1)
  self.assertEqual(result['suggestion'],(0,1))
