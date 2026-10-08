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


def run(root, processor=process_item, poll=.5, closed_lid=False):
    from resource_limits import configure
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
        power = None
        if closed_lid:
            from queue_power import QueuePower
            power = QueuePower(root)
            try:power.start()
            except (OSError,RuntimeError) as error:
                from project_store import write
                write(root/'work/queue-power.json',dict(phase='error',message=str(error),token=power.token))
                power.stop();store.set_enabled(False);return
        try:
            process_queue(root, store, processor, poll, power)
        finally:
            if power is not None:power.stop()


def process_queue(root, store, processor, poll, power=None):
    from app_logging import log_exception, redact
    from queue_power import status
    while store.enabled():
        with (root/'work/heavy-job.lock').open('a') as heavy:
            while store.enabled():
                if power is not None and status(root).get('phase') != 'active':
                    store.set_enabled(False)
                    break
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
        # Release the heavy lock between videos, allowing manual jobs their turn.


def interrupted(signum, frame):
    raise InterruptedError('Local queue interrupted; saved work is retained.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--closed-lid', action='store_true')
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, interrupted)
    # Temporary idle-sleep assertion, released automatically when this runner exits.
    import subprocess
    if Path('/usr/bin/caffeinate').is_file():
        subprocess.Popen(['/usr/bin/caffeinate', '-i', '-w', str(os.getpid())], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run(args.root, closed_lid=args.closed_lid)
