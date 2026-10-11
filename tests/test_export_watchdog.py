"""Real child processes exercise silent hangs, flooded stderr and termination."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import app_logging
from ffmpeg_export import run_ffmpeg
from local_worker_process import run_local


class ExportWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.log_patch = patch('app_logging.LOG_PATH', self.root / 'logs' / 'app.log')
        self.log_patch.start()

    def tearDown(self):
        self.log_patch.stop()
        self.temp.cleanup()

    def command(self, script):
        return [sys.executable, '-u', '-c', script]

    def assert_reaped(self, pid):
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_silent_hang_reaches_deadline_and_child_is_reaped(self):
        pid_file = self.root / 'pid'
        script = f'import os,time;from pathlib import Path;Path({str(pid_file)!r}).write_text(str(os.getpid()));time.sleep(30)'
        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            run_ffmpeg(self.command(script), 1, timeout=.3)
        self.assertLess(time.monotonic() - start, 3)
        self.assert_reaped(int(pid_file.read_text()))

    def test_ignored_termination_is_killed_and_reaped(self):
        pid_file = self.root / 'pid'
        script = f'import os,time,signal;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path({str(pid_file)!r}).write_text(str(os.getpid()));time.sleep(30)'
        with self.assertRaises(TimeoutError):
            run_ffmpeg(self.command(script), 1, timeout=.3)
        self.assert_reaped(int(pid_file.read_text()))

    def test_large_stderr_and_partial_progress_lines_do_not_deadlock(self):
        script = ('import os,time;os.write(2,b"x"*2000000);'
                  'os.write(1,b"out_time_us=bad\\nout_time_us=500");'
                  'time.sleep(.05);os.write(1,b"000\\nout_time_us=200000\\nout_time_us=1000000\\n")')
        events = []
        run_ffmpeg(self.command(script), 1, events.append, timeout=3)
        self.assertEqual(events, [.5, 1.])

    def test_callback_failure_terminates_the_child(self):
        pid_file = self.root / 'pid'
        script = f'import os,time;from pathlib import Path;Path({str(pid_file)!r}).write_text(str(os.getpid()));print("out_time_us=500000",flush=True);time.sleep(30)'
        def callback(_):
            raise RuntimeError('UI callback failed')
        with self.assertRaisesRegex(RuntimeError, 'UI callback'):
            run_ffmpeg(self.command(script), 1, callback, timeout=3)
        self.assert_reaped(int(pid_file.read_text()))

    def test_encoding_error_is_logged_with_bounded_redacted_diagnostics(self):
        script = 'import sys;sys.stderr.write("x"*2000000+"\\nBad codec access_token=private-token https://example.test/?code=secret-code\\n");sys.exit(1)'
        with self.assertRaisesRegex(RuntimeError, 'Export failed'):
            run_ffmpeg(self.command(script), 1, timeout=3)
        log = app_logging.LOG_PATH.read_text()
        self.assertIn('Bad codec', log)
        self.assertNotIn('private-token', log)
        self.assertNotIn('secret-code', log)
        self.assertLess(len(log), 12000)

    def test_worker_failure_retains_child_stack_after_temp_files_disappear(self):
        with tempfile.TemporaryDirectory() as folder:
            request = Path(folder) / 'request.json'
            request.write_text('{}')
            script = 'raise ValueError("secret transcript or provider body access_token=private-token")'
            with self.assertRaises(RuntimeError):
                run_local(self.command(script), request, request.with_name('result.json'), dict(os.environ), 3)
        log = app_logging.LOG_PATH.read_text()
        self.assertIn('ValueError', log)
        self.assertIn('<string>:1', log)
        self.assertNotIn('secret transcript', log)
        self.assertNotIn('private-token', log)

    def test_invalid_deadline_never_starts_encoding(self):
        for limit in (0, -1, float('inf'), float('nan')):
            with patch('ffmpeg_export.subprocess.Popen') as start:
                with self.assertRaises(ValueError):
                    run_ffmpeg([], 1, timeout=limit)
                start.assert_not_called()
