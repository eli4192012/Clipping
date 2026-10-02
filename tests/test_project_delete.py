import fcntl,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import social_store as store
from project_delete import delete_project

class ProjectDeleteTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.project=self.root/'data/project';self.project.mkdir(parents=True)
  self.original=self.root/'Downloads/original.mp4';self.original.parent.mkdir();self.original.write_bytes(b'original')
  (self.project/'project.json').write_text(json.dumps(dict(title='Example',source=str(self.original))))
  (self.project/'source.mp4').write_bytes(b'imported copy')
  self.trash=self.root/'Trash'
  self.db=patch.object(store,'DB',self.root/'data/social.sqlite3');self.db.start()
 def tearDown(self):self.db.stop();self.tmp.cleanup()
 def test_trash_keeps_external_original_and_disables_drafts(self):
  store.save(dict(id='draft',folder=str(self.project),status='Draft'))
  target=delete_project(self.project,self.root,self.trash)
  self.assertFalse(self.project.exists());self.assertTrue((target/'source.mp4').exists())
  self.assertTrue(self.original.exists());self.assertTrue(store.get('draft')['project_deleted'])
  with self.assertRaises(ValueError):store.validate(store.get('draft'))
 def test_outside_root_and_symlink_rejected(self):
  alias=self.root/'data/alias';alias.symlink_to(self.original.parent,target_is_directory=True)
  for path in (self.original.parent,alias,self.root/'data'):
   with self.assertRaises(ValueError):delete_project(path,self.root,self.trash)
  self.assertTrue(self.original.exists())
 def test_active_job_blocks_deletion(self):
  lock=self.root/'work/heavy-job.lock';lock.parent.mkdir()
  with lock.open('a') as handle:
   fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaises(ValueError):delete_project(self.project,self.root,self.trash)
  self.assertTrue(self.project.exists())
 def test_failed_move_preserves_project_and_draft(self):
  store.save(dict(id='draft',folder=str(self.project),status='Draft'))
  with patch('project_delete.shutil.move',side_effect=PermissionError):
   with self.assertRaises(PermissionError):delete_project(self.project,self.root,self.trash)
  self.assertTrue(self.project.exists());self.assertNotIn('project_deleted',store.get('draft'))
