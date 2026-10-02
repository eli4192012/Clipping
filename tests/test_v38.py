import unittest,tempfile,json
from pathlib import Path
from project_store import write,read,save_run,library,runs_for
class Projects(unittest.TestCase):
 def test_settings_snapshot_survives_changes(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'project';f.mkdir();source=f/'source.mp4';source.touch()
   project=dict(source=str(source),folder=str(f),title='Saved',duration=100)
   result=f/'clips-v10-Interview-20-65-all-ai-c1.0-v37-test.json'
   write(result,[dict(start=0,end=10,text='A topic')]);save_run(project,dict(mode='Interview',quality='Balanced'),result)
   write(f/'ui-settings.json',dict(mode='Sports',quality='Higher quality'))
   entry=library(d)[0];self.assertEqual(entry['runs'][0]['settings']['mode'],'Interview')
   self.assertEqual(entry['runs'][0]['count'],1)
 def test_missing_source_is_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'project';write(f/'project.json',dict(source=str(f/'missing'),folder=str(f),title='Missing'))
   self.assertFalse(library(d)[0]['available'])
 def test_corrupt_project_does_not_break_library(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d)/'bad';f.mkdir();(f/'project.json').write_text('{')
   self.assertEqual(library(d),[])
 def test_empty_run_is_saved_but_sidecars_are_not_runs(self):
  with tempfile.TemporaryDirectory() as d:
   f=Path(d);write(f/'clips-v10-Interview-20-65-all-ai.json',[])
   write(f/'clips-v10-Interview-20-65-all-ai.diagnostics.json',{'kept':0})
   self.assertEqual(len(runs_for(dict(folder=d))),1)
