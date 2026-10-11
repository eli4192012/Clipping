"""Private, rotating diagnostics without request payloads or exception messages."""
import logging
import os
import re
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / 'work' / 'logs' / 'app.log'
_LOCK = threading.Lock()


class PrivateRotatingHandler(RotatingFileHandler):
    def _open(self):
        descriptor = os.open(self.baseFilename, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        os.fchmod(descriptor, 0o600)
        return os.fdopen(descriptor, 'a', encoding='utf-8')


def redact(text):
    """For FFmpeg diagnostics only; authentication failures never include messages."""
    text = re.sub(r'https?://[^\s<>]+', '[URL removed]', str(text))
    text = re.sub(r'(?i)\bBearer\s+\S+', 'Bearer [removed]', text)
    text = re.sub(r'(?i)([\"\']?(?:access_token|refresh_token|client_secret|api_key|password|authorization|code)[\"\']?\s*[:=]\s*)[^\s,;]+', r'\1[removed]', text)
    return text


def _write(context, details):
    # A logging failure must never hide the original failure or break a fallback.
    try:
        with _LOCK:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            LOG_PATH.parent.chmod(0o700)
            handler = PrivateRotatingHandler(LOG_PATH, maxBytes=1_048_576, backupCount=3)
            handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
            try:
                handler.emit(logging.LogRecord('clipping', logging.ERROR, '', 0,
                    '%s\n%s', (context, details), None))
            finally:
                handler.close()
    except (OSError, ValueError):
        pass


def log_exception(context):
    """Keep exception types and call locations, excluding messages, source and locals.

    Provider exceptions may contain tokens or returned bodies; model exceptions
    may contain transcript text. Neither is appropriate for general error logs.
    """
    error = sys.exception()
    if error is None:
        return
    details, seen = [], set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        details.append(type(error).__name__)
        for frame in traceback.extract_tb(error.__traceback__):
            details.append(f'  {frame.filename}:{frame.lineno} in {frame.name}')
        error = error.__cause__ or (None if error.__suppress_context__ else error.__context__)
    _write(context, '\n'.join(details))


def log_worker_failure(stderr):
    # Keep child-process traceback locations before its temporary folder is removed.
    locations = re.findall(r'^\s*File "([^"]+)", line (\d+), in ([^\n]+)', stderr, re.M)
    types = re.findall(r'^([A-Za-z_][\w.]*(?:Error|Exception))(?::|$)', stderr, re.M)
    details = '\n'.join(f'  {path}:{line} in {name}' for path, line, name in locations)
    _write('Local worker failed', '\n'.join(types) + '\n' + details)


def log_ffmpeg_failure(details):
    _write('FFmpeg export failed', redact(details[-8000:]))
