import tempfile,unittest
from pathlib import Path
from modes import select_highlights
from topics import make_topic,exact_cut_review
from presentation import write_ass,layout_filter,LAYOUTS
class V33(unittest.TestCase):
 def test_failed_draft_never_fills_quality_quota(self):
  drafts=[dict(start=0,end=12,text='One complete topic',rank=2,passed=True),dict(start=20,end=30,text='Unknown subject',rank=9,passed=False)]
  why=[]
  self.assertEqual(len(select_highlights(drafts,40,'Interview',5,why,coverage=1,strict=True)),1)
  self.assertEqual(why[0]['reason'],'Failed completeness review')
 def test_coverage_can_keep_complete_topics(self):
  drafts=[dict(start=0,end=25,text='First unique discussion',rank=2,passed=True),dict(start=30,end=55,text='Second independent explanation',rank=1,passed=True)]
  self.assertEqual(len(select_highlights(drafts,60,'Interview',5,coverage=1,strict=True)),2)
  self.assertEqual(len(select_highlights(drafts,60,'Interview',5,coverage=.4,strict=True)),0)
 def test_bad_model_boundaries_rejected(self):
  s=[dict(start=0,end=10,text='Named topic with explanation.')]
  for a,b in [(-1,0),(0,1),(True,0),(0,'0')]:self.assertIsNone(make_topic(s,a,b,30))
 def test_caption_times_are_clip_relative_and_text_is_literal(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'clip.ass'
   write_ass(p,[dict(start=10,end=11,text='{\\pos(0,0)}Hi'),dict(start=11,end=12,text='there')],10,12,720,1280,True,'Title')
   text=p.read_text();self.assertIn('0:00:00.00,0:00:01.00',text);self.assertNotIn('{\\pos',text)
   self.assertIn('0:00:02.00,Title',text)
 def test_final_question_rejected_even_if_model_approves(self):
  class Tok:
   def apply_chat_template(self,*a,**k):return ''
  c=dict(text='What happens next?')
  exact_cut_review(c,None,Tok(),lambda *a,**k:'{"standalone":true,"complete_ending":true,"faithful":true}',None)
  self.assertFalse(c['passed'])
class InterviewRegression(unittest.TestCase):
 def test_followups_are_separate_and_multipart_questions_skipped(self):
  from topics import interview_topics
  texts=['How does C.J.','Allen look this week, and how do you evaluate him going forward?', 'Is there a chance he can play more?', 'Yeah, absolutely.', 'He had a good week of work.', 'Was there enough last week to make determinations?', 'Yeah, he did some good things in six plays.', 'What kind of week did Slayton have?', 'He did good.', 'The fact that you ask him to get deep, does that make it easier?', 'Yeah, he is still getting acclimated to the offense.']
  sentences=[dict(start=i*4,end=i*4+3,text=t) for i,t in enumerate(texts)]
  topics=interview_topics(sentences,65)
  self.assertEqual(sorted((c['first'],c['last']) for c in topics),[(5,6),(7,8),(9,10)])
 def test_next_declarative_setup_is_excluded(self):
  from topics import interview_topics
  texts=['Do you believe every game matters?', 'Yes, every game matters.', 'We know Nico Collins has had success, but his status is uncertain.', 'What other areas do you look at?', 'The tight end has had a lot of targets.']
  topics=interview_topics([dict(start=i*5,end=i*5+4,text=t) for i,t in enumerate(texts)],65)
  self.assertEqual(sorted((c['first'],c['last']) for c in topics),[(0,1),(2,4)])
 def test_adjacent_topics_are_not_overlaps(self):
  c=[dict(start=0,end=10,text='First topic',passed=True,rank=2),dict(start=10.1,end=20,text='Distinct subject',passed=True,rank=1)]
  self.assertEqual(len(select_highlights(c,25,'Interview',5,coverage=1,strict=True)),2)
if __name__=='__main__':unittest.main()
