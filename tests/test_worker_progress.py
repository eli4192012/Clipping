import json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from local_worker_process import run_local
from topic_cache import reviewed_topics
class WorkerProgress(unittest.TestCase):
 def test_worker_reports_progress_and_drains_output(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);req=p/'request.json';result=p/'result.json';req.write_text('{}')
   script=p/'worker.py';script.write_text('import json,sys,time\nfrom pathlib import Path\np=Path(sys.argv[1]);r=json.loads(p.read_text())\nPath(r["progress"]).write_text(json.dumps(dict(fraction=.5,label="Reviewing 1 of 2")))\nprint("x"*100000)\ntime.sleep(.4)\np.with_name("result.json").write_text("[]")\n')
   events=[]
   self.assertEqual(run_local([sys.executable,str(script),str(req)],req,result,dict(os.environ),5,lambda *x:events.append(x)),[])
   self.assertIn((.5,'Reviewing 1 of 2'),events)
 def test_timeout_terminates_process(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);req=p/'request.json';req.write_text('{}')
   with self.assertRaises(TimeoutError):run_local([sys.executable,'-c','import time;time.sleep(30)'],req,p/'result.json',dict(os.environ),.1)
 def test_invalid_interview_context_skips_model(self):
  c=dict(start=0,end=6,text='Unknown subject',context_uncertain=True)
  with patch('topic_cache.interview_topics',return_value=[c]):
   results=reviewed_topics(dict(mode='Interview',maximum=65,quality='Balanced',sentences=[]),Mock(side_effect=AssertionError('Unnecessary model load')))
   self.assertTrue(results[0]['boundary_rejected'])
 def test_proposal_window_cache_resumes_without_generation(self):
  from topics import topic_candidates
  class Tok:
   def apply_chat_template(self,messages,**kwargs):return messages[0]['content']
  s=[dict(start=i,end=i+1,text='Complete sentence.') for i in range(80)]
  with tempfile.TemporaryDirectory() as tmp:
   generate=Mock(return_value='{"topics":[]}')
   topic_candidates(s,5,30,'Podcast',None,Tok(),generate,None,cache_dir=tmp)
   self.assertEqual(generate.call_count,2)
   topic_candidates(s,5,30,'Podcast',None,Tok(),Mock(side_effect=AssertionError('Repeated window')),None,cache_dir=tmp)
