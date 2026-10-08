import fcntl
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clip_queue import QueueStore, runner_alive
from queue_runner import run, process_item

SETTINGS = dict(mode='Interview',minimum=20,maximum=65,windows=6,vision=False,semantic=True,
                quality='Higher quality',shorts_editor=True,portrait=True)


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = QueueStore(self.root)
        self.projects = []
        for i in range(3):
            folder = self.root/'data'/str(i)
            folder.mkdir()
            source = folder/'source.mp4'
            source.write_bytes(b'source placeholder')
            self.projects.append(dict(folder=str(folder),source=str(source),title=f'Video {i}',duration=40))

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, index, **options):
        return self.store.add(self.projects[index], SETTINGS, **options)[0]

    def test_persistent_fifo_uses_frozen_settings_and_blocks_active_duplicates(self):
        settings = dict(SETTINGS)
        item, fresh = self.store.add(self.projects[0], settings)
        settings['maximum'] = 120
        self.assertTrue(fresh)
        same, fresh = self.store.add(self.projects[0], SETTINGS)
        self.assertFalse(fresh); self.assertEqual(item['id'], same['id'])
        second = self.add(1)
        store = QueueStore(self.root)
        self.assertEqual(store.items()[0]['settings']['maximum'], 65)
        self.assertTrue(store.items()[0]['export_clips'])
        store.set_enabled(True)
        self.assertEqual(store.claim()['id'], item['id'])
        self.assertFalse(store.remove(item['id']))
        self.assertFalse(store.move(item['id'], 1))
        store.finish(item['id'])
        self.assertEqual(store.claim()['id'], second['id'])

    def test_move_and_remove_change_only_waiting_queue_records(self):
        a, b, c = [self.add(i) for i in range(3)]
        self.assertTrue(self.store.move(c['id'], -1))
        self.assertEqual([x['id'] for x in self.store.items()], [a['id'], c['id'], b['id']])
        self.assertTrue(self.store.remove(c['id']))
        self.assertTrue(Path(c['project']['source']).is_file())
        self.store.set_enabled(True)
        self.assertEqual(self.store.claim()['id'], a['id'])
        self.store.finish(a['id'])
        self.assertEqual(self.store.claim()['id'], b['id'])

    def test_failed_video_continues_to_next_and_retry_preserves_completed_work(self):
        a, b = self.add(0), self.add(1)
        order = []
        def process(store, item):
            order.append(item['id'])
            store.update(item['id'], progress=.2, result='saved.json', exports=[{'video':'kept.mp4'}])
            if item['id']==a['id']:raise ValueError('Source check failed')
        self.store.set_enabled(True)
        run(self.root, process)
        self.assertEqual(order, [a['id'], b['id']])
        self.assertEqual(self.store.get(a['id'])['state'], 'failed')
        self.assertEqual(self.store.get(a['id'])['progress'], .2)
        self.assertEqual(self.store.get(b['id'])['state'], 'done')
        self.assertFalse(self.store.enabled())
        self.assertTrue(self.store.retry(a['id']))
        self.assertEqual(self.store.get(a['id'])['exports'], [{'video':'kept.mp4'}])

    def test_pause_finishes_current_but_does_not_start_next(self):
        a, b = self.add(0), self.add(1)
        def pause(store, item):store.set_enabled(False)
        self.store.set_enabled(True)
        run(self.root, pause)
        self.assertEqual(self.store.get(a['id'])['state'], 'done')
        self.assertEqual(self.store.get(b['id'])['state'], 'queued')
        self.store.set_enabled(True)
        run(self.root, lambda store, item: None)
        self.assertEqual(self.store.get(b['id'])['state'], 'done')

    def test_an_exception_without_message_is_still_a_failed_video(self):
        item=self.add(0);self.store.set_enabled(True)
        def fail(store,item):raise RuntimeError()
        run(self.root,fail)
        row=self.store.get(item['id'])
        self.assertEqual(row['state'],'failed');self.assertEqual(row['error'],'RuntimeError')

    def test_recovery_resumes_interrupted_item_before_next_without_losing_results(self):
        a, b = self.add(0), self.add(1)
        self.store.set_enabled(True)
        self.store.claim()
        self.store.update(a['id'], progress=.75, result='saved-analysis.json')
        order=[]
        run(self.root, lambda store,item: order.append(item['id']))
        self.assertEqual(order, [a['id'], b['id']])
        self.assertEqual(self.store.get(a['id'])['result'], 'saved-analysis.json')
        self.assertEqual(self.store.get(a['id'])['attempts'], 2)

    def test_only_one_runner_can_claim_work(self):
        item=self.add(0); self.store.set_enabled(True)
        lockpath=self.root/'work/clip-queue-runner.lock'; lockpath.parent.mkdir()
        with lockpath.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.assertTrue(runner_alive(self.root))
            run(self.root, lambda *args: self.fail('Second runner processed work'))
        self.assertEqual(self.store.get(item['id'])['state'], 'queued')
        self.assertFalse(runner_alive(self.root))

    def test_waiting_for_foreground_lock_can_pause_without_claiming_work(self):
        item=self.add(0); self.store.set_enabled(True)
        lockpath=self.root/'work/heavy-job.lock'; lockpath.parent.mkdir()
        with lockpath.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with patch('queue_runner.time.sleep', side_effect=lambda p: self.store.set_enabled(False)):
                run(self.root, lambda *args: self.fail('Concurrent heavy job'))
        self.assertEqual(self.store.get(item['id'])['state'], 'queued')

    def test_changed_or_missing_source_fails_before_inference(self):
        item=self.add(0)
        Path(item['project']['source']).write_bytes(b'changed source')
        with patch('jobs.analyze') as analyze:
            with self.assertRaisesRegex(ValueError, 'changed'):process_item(self.store, item)
            analyze.assert_not_called()

    def test_progress_is_monotonic_and_exports_finish_before_next_video(self):
        item=self.add(0); self.store.set_enabled(True); item=self.store.claim()
        events=[]
        def analyze(project, settings, progress):
            progress(.9, 'Reviewing 3 of 4');progress(.8, 'Updated review');progress(1, 'Saved analysis')
            return 'saved.json'
        def export(project, settings, result, progress, checkpoint):
            events.append(self.store.get(item['id'])['state'])
            progress(.5, 'Exporting clip 1 of 2');checkpoint([{'video':'clip1.mp4'}]);progress(1, 'Exported')
        with patch('jobs.analyze', side_effect=analyze),patch('jobs.estimate_seconds',return_value=400),patch('queue_exports.export_suggestions',side_effect=export):
            process_item(self.store,item)
        row=self.store.get(item['id'])
        self.assertEqual(events,['running'])
        self.assertEqual(row['exports'],[{'video':'clip1.mp4'}])
        self.assertEqual(row['estimate'],400)
        self.assertEqual(row['progress'],.99)

    def test_analysis_only_skips_exports(self):
        item=self.add(0,export_clips=False);self.store.set_enabled(True);item=self.store.claim()
        with patch('jobs.analyze',return_value='saved.json'),patch('jobs.estimate_seconds',return_value=1),patch('queue_exports.export_suggestions') as export:
            process_item(self.store,item)
        export.assert_not_called()
        self.assertEqual(self.store.get(item['id'])['result'],'saved.json')

    def test_deleting_queued_project_is_blocked_until_it_is_removed(self):
        from project_delete import delete_project
        from project_store import write
        item=self.add(0)
        write(Path(item['project']['folder'])/'project.json',item['project'])
        with self.assertRaisesRegex(ValueError,'queue'):delete_project(item['project']['folder'],self.root,self.root/'trash')
        self.store.remove(item['id'])
        self.assertFalse(self.store.active_for(item['project']['folder']))
        self.assertTrue(Path(item['project']['source']).is_file())

    def test_child_retains_heavy_lock_after_parent_closes_its_handle(self):
        from resource_limits import inherited_lock_fds
        path=self.root/'lock'
        with path.open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            with patch.dict(os.environ, {'CLIPPING_HEAVY_LOCK_FD':str(lock.fileno())}):
                child=subprocess.Popen([sys.executable,'-c',"import sys;print('ready',flush=True);sys.stdin.read()"],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True,pass_fds=inherited_lock_fds())
            self.assertEqual(child.stdout.readline().strip(),'ready')
        try:
            with path.open('a') as other:
                with self.assertRaises(BlockingIOError):fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
        finally:
            child.communicate('',timeout=5)
        with path.open('a') as other:fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)

    def test_foreground_worker_inherits_thread_local_lock_without_global_env_mutation(self):
        from resource_limits import HEAVY_JOB_FD
        from local_worker_process import run_local
        root=self.root;request=root/'request.json';result=root/'result.json'
        request.write_text('{}')
        command=[sys.executable,'-c',"import os,fcntl,json,sys;from pathlib import Path;fd=int(os.environ['CLIPPING_HEAVY_LOCK_FD']);os.fstat(fd);Path(sys.argv[1]).write_text(json.dumps({'inherited':True}))",str(result)]
        with (root/'lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            token=HEAVY_JOB_FD.set(lock.fileno())
            try:
                env=dict(os.environ);env.pop('CLIPPING_HEAVY_LOCK_FD',None)
                self.assertEqual(run_local(command,request,result,env,5),{'inherited':True})
                self.assertNotIn('CLIPPING_HEAVY_LOCK_FD',env)
            finally:HEAVY_JOB_FD.reset(token)


if __name__=='__main__':unittest.main()
