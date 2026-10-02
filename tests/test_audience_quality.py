import unittest
from audience_quality import annotate,validated_review
from modes import select_highlights
from topics import exact_cut_review

TEXT='Why did the Colts change protection? The extra blocker gave Jones time. That adjustment stopped the pressure.'
def review(opening=2,clarity=2,value=2,payoff=2):
 return {k:dict(rating=v,evidence=TEXT.split('?')[0]) for k,v in dict(opening=opening,clarity=clarity,value=value,payoff=payoff).items()}
def clip(**values):
 return dict(dict(start=0,end=25,text=TEXT,rank=1,passed=True,audience_review=review()),**values)

class AudienceQualityTests(unittest.TestCase):
 def test_requires_real_evidence_and_integer_ratings(self):
  self.assertIsNotNone(validated_review(review(),TEXT))
  for bad in (None,{},dict(review(),value={'rating':True,'evidence':'Colts'}),dict(review(),payoff={'rating':2,'evidence':'They won the game'})):
   self.assertIsNone(validated_review(bad,TEXT))
 def test_complete_story_beats_clickbait_on_overlap(self):
  strong=clip(rank=1)
  teaser=clip(rank=999,audience_review=review(2,1,1,0))
  chosen=select_highlights(annotate([teaser,strong],'Podcast'),60,'Podcast',None,coverage=1)
  self.assertEqual(chosen,[strong])
 def test_failed_completeness_cannot_beat_passed(self):
  incomplete=clip(passed=False,rank=999)
  complete=clip(audience_review=review(1,1,1,1))
  chosen=select_highlights(annotate([incomplete,complete],'Interview'),60,'Interview',None,coverage=1)
  self.assertEqual(chosen,[complete])
 def test_empty_value_is_excluded_and_explained(self):
  c=clip(audience_review=review(value=0,payoff=0));why=[]
  self.assertEqual(select_highlights(annotate([c],'Interview'),60,'Interview',None,diagnostics=why,coverage=1),[])
  self.assertIn('payoff',why[0]['reason'])
 def test_missing_review_is_not_silently_rejected(self):
  c=clip(audience_review=None)
  annotate([c],'Podcast');self.assertEqual(c['audience_quality']['basis'],'Basic text checks')
  self.assertEqual(len(select_highlights([c],60,'Podcast',None,coverage=1)),1)
 def test_no_universal_duration_preference(self):
  a,b=clip(end=12),clip(end=55)
  annotate([a,b],'Podcast');self.assertEqual(a['audience_quality']['score'],b['audience_quality']['score'])
 def test_sports_commentary_does_not_prove_action(self):
  a,b=clip(visual_reviewed=True),clip(visual_sequence=True)
  annotate([a,b],'Sports');self.assertGreater(b['audience_quality']['score'],a['audience_quality']['score'])
  self.assertNotIn('criteria',a['audience_quality'])
 def test_exact_review_attaches_supported_rubric(self):
  import json
  class Tokenizer:
   def apply_chat_template(self,*args,**kwargs):return ''
  verdict=dict(title='Colts protection adjustment',standalone=True,complete_ending=True,faithful=True,audience_review=review())
  c=exact_cut_review(clip(),None,Tokenizer(),lambda *args,**kwargs:json.dumps(verdict),None)
  self.assertTrue(c['passed']);self.assertEqual(c['audience_review'],review())
