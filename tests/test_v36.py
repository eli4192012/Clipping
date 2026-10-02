import unittest
from video_type import classify
class TypeTests(unittest.TestCase):
 def test_football_interview_is_not_gameplay(self):
  s=[{'text':t} for t in ['How is Nico Collins doing?', 'Yeah, he practiced.', 'What is the plan against Houston?', 'We need to tackle better.']]
  self.assertEqual(classify('Colts football update',s,.9)['mode'],'Interview')
 def test_action_highlights(self):
  self.assertEqual(classify('Colts game highlights',[{'text':'He throws into the end zone. Touchdown! First down.'}],0)['mode'],'Sports')
 def test_podcast_questions_remain_podcast(self):
  s=[{'text':t} for t in ['What do you think?', 'Yeah, absolutely.', 'How about the Colts?', 'Yes, they looked strong.']]
  self.assertEqual(classify('Weekly NFL podcast',s,.8)['mode'],'Podcast')
 def test_unknown_does_not_claim_high_confidence(self):
  self.assertEqual(classify('video',[],0)['confidence'],'Low')
 def test_explicit_press_conference(self):
  self.assertEqual(classify('Coach press conference',[],0)['mode'],'Interview')
