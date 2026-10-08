"""One local video at a time, including exports, outside Streamlit reruns."""
import argparse
import fcntl
import os
import signal
import time
from pathlib import Path

from clip_queue import QueueStore


def process_item(store, item):
    from jobs import analyze, estimate_seconds
    from queue_exports import export_suggestions
    source = Path(item['project']['source'])
    stat = source.stat()
    if [stat.st_size, stat.st_mtime_ns] != item['source_state']:
        raise ValueError('The source video changed after it was queued. Add the updated project again.')
    scale = .75 if item['export_clips'] else 1.
    last = -1.

    def progress(fraction, label):
        nonlocal last
        fraction = max(last, min(.99, float(fraction)))
        last = fraction
        store.update(item['id'], progress=fraction, label=label)

    # Estimates apply to the actual analysis phase, not the time waiting for its turn.
    store.update(item['id'], estimate=estimate_seconds(item['project'], item['settings']))
    result = analyze(item['project'], item['settings'], lambda p, label: progress(scale*p, label))
    store.update(item['id'], result=result)
    if item['export_clips']:
        export_suggestions(item['project'], item['settings'], result,
                           lambda p, label: progress(.75+.24*p, label),
                           lambda exports: store.update(item['id'], exports=exports))


def run(root, processor=process_item, poll=.5):
    from resource_limits import configure
    from app_logging import log_exception, redact
    configure()
    root = Path(root).resolve()
    store = QueueStore(root)
    runner_path = root/'work/clip-queue-runner.lock'
    runner_path.parent.mkdir(parents=True, exist_ok=True)
    with runner_path.open('a') as runner:
        try:
            fcntl.flock(runner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        store.recover()
        while store.enabled():
            with (root/'work/heavy-job.lock').open('a') as heavy:
                while store.enabled():
                    try:
                        fcntl.flock(heavy, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        time.sleep(poll)
                if not store.enabled():
                    break
                item = store.claim()
                if item is None:
                    break
                # Model/FFmpeg children retain this lock if the coordinator is killed.
                os.environ['CLIPPING_HEAVY_LOCK_FD'] = str(heavy.fileno())
                try:
                    processor(store, item)
                except (InterruptedError, KeyboardInterrupt):
                    store.set_enabled(False)
                    store.recover()
                    break
                except Exception as error:
                    log_exception('Queued video failed')
                    store.finish(item['id'], redact(str(error)) or type(error).__name__)
                else:
                    store.finish(item['id'])
                finally:
                    os.environ.pop('CLIPPING_HEAVY_LOCK_FD', None)
            # The heavy lock is released between videos, allowing manual jobs their turn.


def interrupted(signum, frame):
    raise InterruptedError('Local queue interrupted; saved work is retained.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, interrupted)
    # Temporary idle-sleep assertion, released automatically when this runner exits.
    import subprocess
    if Path('/usr/bin/caffeinate').is_file():
        subprocess.Popen(['/usr/bin/caffeinate', '-i', '-w', str(os.getpid())], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run(args.root)
