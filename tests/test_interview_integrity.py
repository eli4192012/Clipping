import unittest,json
from pathlib import Path
from interview_integrity import verify,topic_title,question,blocks
from topics import interview_topics
from modes import select_highlights
class RealClipBoundaries(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.sentences=json.loads((Path(__file__).parent/'fixtures/interview_sep30.json').read_text())
  cls.clips=interview_topics(cls.sentences,65)
 def test_rivalry_block_keeps_answer_but_multiple_questions_are_skipped(self):
  a,q,b=next(e for e in blocks(self.sentences) if self.sentences[e[0]]['start']==374.38)
  self.assertAlmostEqual(self.sentences[b]['end'],398.52)
  self.assertFalse(any(c['first']==a for c in self.clips))
  self.assertFalse(verify(dict(first=a,last=b),self.sentences))
 def test_injury_topics_separate_and_context_kept(self):
  a=next(c for c in self.clips if abs(c['start']-42.04)<.01)
  self.assertAlmostEqual(a['end'],63.32);self.assertIn('Alex',a['text']);self.assertNotIn('CJ Allen',a['text'])
  self.assertFalse(any(abs(c['start']-65.92)<.01 for c in self.clips)) # two reporter questions before answer
 def test_old_bad_cuts_fail_even_if_approved(self):
  for first,last in [(96,98),(14,18),(64,69)]:
   self.assertFalse(verify(dict(first=first,last=last,passed=True),self.sentences))
 def test_playbook_does_not_cross_missing_speech(self):
  a,q,b=next(e for e in blocks(self.sentences) if self.sentences[e[0]]['start']==224.76)
  self.assertAlmostEqual(self.sentences[b]['end'],256.22)
  self.assertFalse(any(c['first']==a for c in self.clips))
 def test_rhetorical_filler_is_not_new_question(self):
  self.assertFalse(question('You know what I mean?'))
  self.assertFalse(question("But when you've got both teams hungry, it comes down to physicality."))
 def test_no_role_or_person_in_topic_title(self):
  title=topic_title('Yeah, studying the playbook and communication.')
  self.assertEqual(title,'Playbook Study and Communication')
  self.assertNotIn('Coach',title)
 def test_hard_rejection_applies_even_in_balanced(self):
  c=dict(start=0,end=15,text='Bad cut',rank=100,passed=True,boundary_rejected=True)
  self.assertEqual(select_highlights([c],100,'Interview',coverage=1,strict=False),[])
