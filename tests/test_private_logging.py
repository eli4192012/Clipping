import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app_logging


class PrivateLoggingTests(unittest.TestCase):
    def test_tracebacks_keep_call_locations_without_exception_payloads(self):
        with tempfile.TemporaryDirectory() as temp, patch('app_logging.LOG_PATH', Path(temp) / 'logs' / 'app.log'):
            try:
                raise ValueError('access_token=secret-token full transcript and provider response')
            except ValueError:
                app_logging.log_exception('Account connection failed')
            text = app_logging.LOG_PATH.read_text()
            self.assertIn('ValueError', text)
            self.assertIn('test_tracebacks_keep_call_locations', text)
            self.assertNotIn('secret-token', text)
            self.assertNotIn('transcript and', text)
            self.assertEqual(stat.S_IMODE(app_logging.LOG_PATH.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(app_logging.LOG_PATH.parent.stat().st_mode), 0o700)

    def test_rotation_stays_bounded_and_private(self):
        handler_type = app_logging.PrivateRotatingHandler
        def handler(path, **_):
            return handler_type(path, maxBytes=250, backupCount=2)
        with tempfile.TemporaryDirectory() as temp, patch('app_logging.LOG_PATH', Path(temp) / 'logs' / 'app.log'), patch('app_logging.PrivateRotatingHandler', side_effect=handler):
            for _ in range(20):
                app_logging._write('Test failure', 'safe details ' * 6)
            files = list(app_logging.LOG_PATH.parent.iterdir())
            self.assertEqual(len(files), 3)
            for file in files:
                self.assertLess(file.stat().st_size, 300)
                self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o600)

    def test_unwritable_log_does_not_interrupt_app_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            blocked = Path(temp) / 'file'
            blocked.write_text('Not a directory')
            with patch('app_logging.LOG_PATH', blocked / 'app.log'):
                try:
                    raise RuntimeError('Original error')
                except RuntimeError:
                    app_logging.log_exception('Failed action')
