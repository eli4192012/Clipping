import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from clip_queue import QueueStore
from project_store import write
from queue_power import DURATION, capability, owned, process_identity, status, watch
from queue_runner import run


class QueuePowerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/'work').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def scripted(self, power_checks, snapshots, action=None):
        calls = []
        def script(body, timeout=20):
            calls.append(body)
            return str(DURATION) if 'start new session' in body else ''
        with patch('queue_power.capability', side_effect=power_checks), \
             patch('queue_power.process_identity', return_value='identity'), \
             patch('queue_power.applescript', side_effect=script), \
             patch('queue_power.session_snapshot', side_effect=snapshots), \
             patch('queue_power.time.sleep', side_effect=action):
            watch(self.root, 123, 'test', poll=0)
        return calls

    def test_normal_finish_releases_owned_session_without_changing_defaults(self):
        calls = self.scripted([(True, '')]*2, [(True, True, DURATION)]*3,
                              lambda _: (self.root/'work/queue-power-stop-test').touch())
        self.assertEqual(calls[-1], 'end session')
        self.assertIn('displaySleepAllowed:true', calls[0])
        self.assertEqual(status(self.root)['phase'], 'ended')

    def test_unplug_releases_session_and_reports_actionable_error(self):
        calls = self.scripted([(True, ''), (False, 'Connect your charger.')], [(True, True, DURATION)]*3)
        self.assertEqual(calls[-1], 'end session')
        self.assertEqual(status(self.root)['phase'], 'error')
        self.assertIn('charger', status(self.root)['message'])

    def test_replaced_session_is_not_ended(self):
        calls = self.scripted([(True, '')]*2, [(True, True, DURATION), (True, True, 3600), (True, True, 3600)])
        self.assertNotIn('end session', calls)
        self.assertEqual(status(self.root)['phase'], 'ended')

    def test_closed_mode_denied_releases_new_session(self):
        calls = self.scripted([(True, '')], [(True, False, DURATION)]*2)
        self.assertEqual(calls[-1], 'end session')
        self.assertEqual(status(self.root)['phase'], 'error')

    def test_existing_session_remains_untouched(self):
        with patch('queue_power.capability', return_value=(True, '')), \
             patch('queue_power.process_identity', return_value='identity'), \
             patch('queue_power.applescript', return_value='busy') as script:
            watch(self.root, 123, 'test')
        self.assertEqual(script.call_count, 1)
        self.assertIn('already active', status(self.root)['message'])

    def test_owner_exit_releases_session(self):
        owner = iter(['identity', ''])
        def identity(pid):return next(owner) if pid == 123 else 'watcher'
        calls = []
        def script(body, timeout=20):
            calls.append(body)
            return str(DURATION) if 'start new session' in body else ''
        with patch('queue_power.capability', return_value=(True, '')), \
             patch('queue_power.process_identity', side_effect=identity), \
             patch('queue_power.applescript', side_effect=script), \
             patch('queue_power.session_snapshot', return_value=(True, True, DURATION)):
            watch(self.root, 123, 'test')
        self.assertEqual(calls[-1], 'end session')

    def test_countdown_rejects_indefinite_trigger_expired_and_replaced_sessions(self):
        self.assertTrue(owned((True, True, DURATION-10), 100, 110))
        for snapshot in [(False, False, 0), (True, True, 0), (True, True, -1), (True, True, 3600)]:
            self.assertFalse(owned(snapshot, 100, 110))

    def test_dead_or_stale_monitor_cannot_claim_active(self):
        path = self.root/'work/queue-power.json'
        write(path, dict(phase='active',updated=time.time()-60,watcher=999999,watcher_identity='old'))
        self.assertEqual(status(self.root)['phase'], 'error')
        write(path, dict(phase='active',updated=time.time(),watcher=999999,watcher_identity='old'))
        with patch('queue_power.process_identity', return_value=''):
            self.assertEqual(status(self.root)['phase'], 'error')

    def test_process_identity_is_stable_across_cpu_states_and_rejects_zombies(self):
        with patch('queue_power.subprocess.run', side_effect=[
                Mock(stdout='501 Wed Oct 7 19:00:00 2026 R'),
                Mock(stdout='501 Wed Oct 7 19:00:00 2026 S'),
                Mock(stdout='501 Wed Oct 7 19:00:00 2026 Z')]):
            self.assertEqual(process_identity(1), process_identity(1))
            self.assertEqual(process_identity(1), '')

    def test_unsupported_platform_and_unknown_power_do_not_enable(self):
        with patch('queue_power.platform.system', return_value='Linux'):
            self.assertFalse(capability()[0])
        with patch('queue_power.platform.system', return_value='Darwin'), \
             patch('queue_power.Path.is_file', return_value=True), \
             patch('queue_power.subprocess.run', side_effect=subprocess.TimeoutExpired('pmset', 5)):
            self.assertFalse(capability()[0])

    def test_failed_setup_keeps_waiting_video_unclaimed(self):
        store = QueueStore(self.root)
        folder=self.root/'data/example';folder.mkdir();source=folder/'source.mp4';source.write_bytes(b'video')
        item,_=store.add(dict(folder=str(folder),source=str(source),title='Example',duration=30),
                         dict(mode='Interview',minimum=20,maximum=65,windows=6,quality='Balanced',semantic=False,vision=False))
        store.set_enabled(True)
        processor=Mock()
        with patch('queue_power.QueuePower.start', side_effect=RuntimeError('Connect charger.')), \
             patch('queue_power.QueuePower.stop'):
            run(self.root, processor=processor, closed_lid=True)
        processor.assert_not_called()
        self.assertFalse(store.enabled())
        self.assertEqual(store.get(item['id'])['state'], 'queued')

    def test_lost_keep_awake_mode_leaves_remaining_videos_waiting(self):
        store=QueueStore(self.root)
        folder=self.root/'data/example';folder.mkdir();source=folder/'source.mp4';source.write_bytes(b'video')
        settings=dict(mode='Interview',minimum=20,maximum=65,windows=6,quality='Balanced',semantic=False,vision=False)
        item,_=store.add(dict(folder=str(folder),source=str(source),title='Example',duration=30),settings)
        store.set_enabled(True)
        processor=Mock()
        power=Mock()
        with patch('queue_power.QueuePower',return_value=power), \
             patch('queue_power.status',return_value=dict(phase='error')):
            run(self.root,processor=processor,closed_lid=True)
        processor.assert_not_called();power.stop.assert_called_once()
        self.assertFalse(store.enabled());self.assertEqual(store.get(item['id'])['state'],'queued')


if __name__ == '__main__':unittest.main()
