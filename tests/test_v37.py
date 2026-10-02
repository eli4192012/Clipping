import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from modes import select_highlights
from jobs import analyze,analysis_path
class V37(unittest.TestCase):
 def test_no_clip_count_cap(self):
  clips=[dict(start=i*10,end=i*10+5,text=f'Unique topic number {i}',rank=100-i,passed=True) for i in range(9)]
  # use distinct token sets to avoid the duplicate-content safeguard
  for i,c in enumerate(clips):c['text']=f'subject{i} explanation{i}'
  self.assertEqual(len(select_highlights(clips,100,'Interview',None,coverage=1,strict=True)),9)
 def test_minimum_target_does_not_pad_failed_drafts(self):
  clips=[dict(start=0,end=5,text='Incomplete',rank=1,passed=False)]
  self.assertEqual(select_highlights(clips,100,'Interview',None,coverage=1,strict=True),[])
 def test_cached_analysis_does_not_run_models(self):
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/'source';source.write_text('fixture')
   p=dict(folder=d,source=str(source));s=dict(mode='Interview',minimum=20,maximum=65,vision=False,semantic=True,windows=6,quality='Higher quality')
   path=analysis_path(p,s);path.write_text('[]')
   with patch('jobs.get_transcript',side_effect=AssertionError('Unexpected transcription')):
    self.assertEqual(analyze(p,s,lambda *a:None),str(path))
   self.assertEqual(analysis_path(p,s),analysis_path(p,dict(s,min_clips=8)))
