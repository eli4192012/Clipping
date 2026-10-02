import unittest
from topics import interview_topics
from interview_integrity import verify,question_count

def transcript(text):return [dict(start=i*3,end=i*3+2.5,text=t) for i,t in enumerate(text)]
class SingleQuestion(unittest.TestCase):
 def test_two_answered_questions_never_merge(self):
  s=transcript(['How did training go?', 'Yeah, training went very well.', 'Was there enough time to prepare?', 'Yeah, we had plenty of time.'])
  clips=interview_topics(s,65)
  self.assertEqual(sorted((c['first'],c['last']) for c in clips),[(0,1),(2,3)])
  self.assertFalse(verify(dict(first=0,last=3,passed=True),s))
  self.assertTrue(all(verify(c,s) for c in clips))
 def test_short_answer_not_padded(self):
  s=transcript(['What changed in training?', 'We now practice every morning.', 'What happens next?', 'We test the new schedule.'])
  self.assertTrue(all(c['end']-c['start']==5.5 for c in interview_topics(s,65)))
 def test_two_questions_one_sentence_rejected(self):
  s=transcript(['How did training go? What did you learn?', 'Yeah, it went very well.'])
  self.assertEqual(interview_topics(s,65),[])
 def test_overlong_answer_skipped_not_truncated(self):
  s=transcript(['What changed?','We changed practice.']+['We learned several useful skills.']*30)
  self.assertEqual(interview_topics(s,30),[])
 def test_fragmented_single_question_kept(self):
  s=transcript(['How does C.J.', 'Allen look this week?', 'Yeah, he looks very healthy.'])
  self.assertEqual(len(interview_topics(s,65)),1)
 def test_rhetorical_question_in_answer_does_not_create_second_exchange(self):
  s=transcript(['What changed in practice?', 'We improved communication.', 'You know what I mean?', 'Yeah, we work together now.'])
  c=interview_topics(s,65)[0];self.assertTrue(verify(c,s))
