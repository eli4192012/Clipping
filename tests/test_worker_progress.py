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
 def test_active_reviews_extend_the_progress_deadline(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);req=p/'request.json';req.write_text('{}');result=p/'result.json'
   script=p/'worker.py';script.write_text('import json,sys,time\nfrom pathlib import Path\np=Path(sys.argv[1]);r=json.loads(p.read_text())\nfor i in range(8):\n Path(r["progress"]).write_text(json.dumps(dict(fraction=i/8,label=f"Reviewing {i+1} of 8")))\n time.sleep(.4)\np.with_name("result.json").write_text("[]")\n')
   events=[]
   self.assertEqual(run_local([sys.executable,str(script),str(req)],req,result,dict(os.environ),2,
                              lambda *x:events.append(x),progress_timeout=True),[])
   self.assertGreater(len(events),3)
 def test_topic_task_uses_progress_deadline_even_when_older_caller_omits_flag(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);req=p/'request.json';req.write_text('{"task":"topics"}');result=p/'result.json'
   script=p/'worker.py';script.write_text('import json,sys,time\nfrom pathlib import Path\np=Path(sys.argv[1]);r=json.loads(p.read_text())\nfor i in range(8):\n Path(r["progress"]).write_text(json.dumps(dict(fraction=i/8,label=f"Reviewing {i+1} of 8")))\n time.sleep(.4)\np.with_name("result.json").write_text("[]")\n')
   self.assertEqual(run_local([sys.executable,str(script),str(req)],req,result,dict(os.environ),2),[])
 def test_rewriting_the_same_progress_does_not_keep_a_stalled_worker_alive(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);req=p/'request.json';req.write_text('{}')
   script=p/'worker.py';script.write_text('import json,sys,time\nfrom pathlib import Path\np=Path(sys.argv[1]);r=json.loads(p.read_text())\nwhile True:\n Path(r["progress"]).write_text(json.dumps(dict(fraction=.5,label="Reviewing 1 of 2")))\n time.sleep(.1)\n')
   import time
   begun=time.monotonic()
   with self.assertRaises(TimeoutError):
    run_local([sys.executable,str(script),str(req)],req,p/'result.json',dict(os.environ),.4,progress_timeout=True)
   self.assertLess(time.monotonic()-begun,3)
 def test_progress_callback_failure_stops_worker_instead_of_being_swallowed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);req=p/'request.json';req.write_text('{}')
   script=p/'worker.py';script.write_text('import json,sys,time\nfrom pathlib import Path\nr=json.loads(Path(sys.argv[1]).read_text())\nPath(r["progress"]).write_text(json.dumps(dict(fraction=.5,label="Reviewing 1 of 2")))\ntime.sleep(30)\n')
   def failed(*args):raise ValueError('Progress storage failed')
   with self.assertRaisesRegex(ValueError,'Progress storage failed'):
    run_local([sys.executable,str(script),str(req)],req,p/'result.json',dict(os.environ),3,failed,progress_timeout=True)
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
