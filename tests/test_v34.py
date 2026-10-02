import json,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from topics import interview_topics
from interview import protect_endings
from polish import title_for,name_suggestions,corrected_words,silent_edges
class V34(unittest.TestCase):
 def test_nico_boundaries_remain_exact(self):
  f=json.loads((Path(__file__).parent/'fixtures/nico_v33.json').read_text())
  topics=protect_endings(interview_topics(f['sentences'],65),f['words'],f['duration'])
  nico=next(c for c in topics if c['start']==f['expected_start'])
  self.assertEqual(nico['end'],f['expected_end'])
  self.assertTrue(nico['text'].startswith('We know Nico Collins'))
  self.assertNotIn('When a guy has a big game',nico['text'])
 def test_uncertain_status_cannot_become_confirmed_absence(self):
  class Tok:
   def apply_chat_template(self,*a,**k):return ''
  result=title_for('Nico Collins status is up in the air.',None,Tok(),lambda *a,**k:'{"title":"Colts Prepare Without Nico Collins"}',None)
  self.assertIsNone(result)
 def test_uncertain_defensive_plan_stays_specific(self):
  title=title_for('Nico Collins status is up in the air. We need to do a great job tackling.',None,None,None,None)
  self.assertEqual(title,'Nico Collins Uncertain: The Defensive Plan')
 def test_name_hint_does_not_change_source(self):
  words=[dict(start=0,end=1,text='Iniko')]
  self.assertEqual(name_suggestions(words,['Nico Collins']),{0:'Nico'})
  fixed=corrected_words(words,{'0':'Nico'})
  self.assertEqual(words[0]['text'],'Iniko');self.assertEqual(fixed[0],dict(start=0,end=1,text='Nico'))
 def test_edge_trim_requires_audio_and_word_agreement(self):
  words=[dict(start=10.1,end=11.95,text='Speech')]
  with patch('polish.subprocess.run',return_value=SimpleNamespace(returncode=0,stderr='silence_start: 0\nsilence_end: 0.5\nsilence_start: 1.5\nsilence_end: 2')):
   self.assertEqual(silent_edges('video',10,12,words),(10,12))
  with patch('polish.subprocess.run',return_value=SimpleNamespace(returncode=0,stderr='silence_start: 0\nsilence_end: 0.5\nsilence_start: 1.5\nsilence_end: 2')):
   self.assertEqual(silent_edges('video',10,12,[dict(start=10.6,end=11.4,text='Speech')]),(10.3,11.7))
 def test_no_audio_silence_means_no_trimming(self):
  with patch('polish.subprocess.run',return_value=SimpleNamespace(returncode=0,stderr='')):
   self.assertEqual(silent_edges('video',10,12,[dict(start=10.6,end=11.4,text='Speech')]),(10,12))
