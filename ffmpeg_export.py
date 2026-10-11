"""Encoding progress and a wall-clock watchdog independent of subprocess output."""
import math
import os
import selectors
import signal
import subprocess
import tempfile
import time

from app_logging import log_exception, log_ffmpeg_failure


def export_timeout(duration):
    return max(180., float(duration) * 12 + 60)


def stop_process(process):
    """Reap the child, escalating if it ignores termination; also stop its group."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=2)
    # A worker can exit before one of its subprocesses; don't leave that group running.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_ffmpeg(command, duration, report=lambda seconds: None, timeout=None):
    """Commands must include ``-progress pipe:1 -nostats``. Report encoded seconds.

    Selectable stdout never blocks the deadline. File-backed stderr cannot fill
    an unread pipe, and only its tail is read into memory on failure.
    """
    from resource_limits import inherited_lock_fds
    limit = export_timeout(duration) if timeout is None else float(timeout)
    if not math.isfinite(limit) or limit <= 0:
        raise ValueError('Choose a finite positive export time limit.')
    process = None
    with tempfile.TemporaryFile() as errors, selectors.DefaultSelector() as events:
        try:
            begun = time.monotonic()
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors,
                                       start_new_session=True, pass_fds=inherited_lock_fds())
            events.register(process.stdout, selectors.EVENT_READ)
            pending, last = b'', -1.
            while True:
                remaining = limit - (time.monotonic() - begun)
                if remaining <= 0:
                    raise TimeoutError('Export reached its time limit. Retry or choose a shorter video.')
                ready = events.select(min(.1, remaining))
                for key, _ in ready:
                    block = os.read(key.fd, 65536)
                    if not block:
                        events.unregister(key.fileobj)
                        continue
                    pending += block
                    lines = pending.split(b'\n')
                    pending = lines.pop()[-65536:]
                    for line in lines:
                        if line.startswith(b'out_time_us='):
                            try:
                                seconds = max(0., int(line.split(b'=', 1)[1]) / 1_000_000)
                            except ValueError:
                                continue
                            if seconds > last:
                                report(seconds)
                                last = seconds
                code = process.poll()
                if code is not None and (not ready or not events.get_map()):
                    break
            if code:
                errors.seek(0, os.SEEK_END)
                errors.seek(max(0, errors.tell() - 8000))
                log_ffmpeg_failure(errors.read().decode('utf-8', errors='replace'))
                raise RuntimeError('Export failed. Details are saved in work/logs/app.log.')
        except BaseException:
            log_exception('FFmpeg export stopped')
            if process is not None:
                stop_process(process)
            raise
        finally:
            if process is not None:
                if process.poll() is None:
                    stop_process(process)
                process.stdout.close()


def ass_filter(path):
    """Escape a filename through both FFmpeg option and filtergraph parsing."""
    value = str(path)
    for characters in ("\\:'", "\\'[],;"):
        value = ''.join('\\' + c if c in characters else c for c in value)
    return 'ass=filename=' + value
