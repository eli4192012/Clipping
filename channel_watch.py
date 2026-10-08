"""Durable public-channel watching. Discovery is light; imports use the serial queue."""
import argparse
import fcntl
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from clip_queue import QueueStore, ensure_runner
from youtube_channels import discover, eligible, CHANNEL_ID
from youtube_import import lookup, UnfinishedVideo

POLL_SECONDS = 300


class WatchStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.path = self.root/'data/channel-watch.sqlite3'
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS channels (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL, settings TEXT NOT NULL,
                    enabled INTEGER NOT NULL, created REAL NOT NULL, checked REAL,
                    next_check REAL NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'Waiting for first check', error TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS videos (
                    channel_id TEXT NOT NULL, id TEXT NOT NULL, title TEXT NOT NULL,
                    state TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '', queue_id TEXT,
                    error TEXT NOT NULL DEFAULT '', retry_at REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (channel_id,id));
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path,timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:yield db
        finally:db.close()

    @staticmethod
    def decode(row):
        if row is None:return None
        item = dict(row)
        if 'settings' in item:
            item['settings'] = json.loads(item['settings']);item['enabled'] = bool(item['enabled'])
        if 'metadata' in item:item['metadata'] = json.loads(item['metadata']) if item['metadata'] else None
        return item

    def channels(self):
        with self.connection() as db:
            return [self.decode(r) for r in db.execute('SELECT * FROM channels ORDER BY created')]

    def get(self, channel_id):
        with self.connection() as db:
            return self.decode(db.execute('SELECT * FROM channels WHERE id=?',(channel_id,)).fetchone())

    def connect(self, channel, settings):
        import re
        from analysis_settings import AnalysisSettings
        AnalysisSettings.read(settings)
        if not re.fullmatch(CHANNEL_ID,channel['id']):raise ValueError('Invalid YouTube channel ID.')
        with self.connection() as db:
            db.execute('''INSERT INTO channels (id,name,url,settings,enabled,created) VALUES (?,?,?,?,1,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name,url=excluded.url,settings=excluded.settings,
                    enabled=1,next_check=0,status='Waiting for next check',error='' ''',
                (channel['id'],channel['name'],channel['url'],json.dumps(settings),time.time()))

    def set_enabled(self, channel_id, enabled):
        with self.connection() as db:
            db.execute("UPDATE channels SET enabled=?,next_check=0,status=?,error='' WHERE id=?",
                       (int(bool(enabled)),'Waiting for next check' if enabled else 'Paused',channel_id))

    def request_check(self, channel_id):
        with self.connection() as db:
            db.execute('UPDATE channels SET next_check=0 WHERE id=?',(channel_id,))
            db.execute("UPDATE videos SET retry_at=0 WHERE channel_id=? AND state IN ('error','waiting')",(channel_id,))

    def update(self, channel_id, **fields):
        if not fields or not fields.keys()<={'checked','next_check','status','error','failures'}:
            raise ValueError('Invalid watcher status update.')
        with self.connection() as db:
            db.execute('UPDATE channels SET '+','.join(k+'=?' for k in fields)+' WHERE id=? AND enabled=1',(*fields.values(),channel_id))

    def videos(self, channel_id):
        with self.connection() as db:
            return [self.decode(r) for r in db.execute('SELECT * FROM videos WHERE channel_id=? ORDER BY rowid DESC',(channel_id,))]

    def record(self, channel_id, entry, state, metadata=None, error='', retry_at=0):
        with self.connection() as db:
            db.execute('''INSERT INTO videos (channel_id,id,title,state,metadata,error,retry_at) VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(channel_id,id) DO UPDATE SET title=excluded.title,state=excluded.state,
                    metadata=excluded.metadata,error=excluded.error,retry_at=excluded.retry_at''',
                (channel_id,entry['id'],entry['title'],state,json.dumps(metadata) if metadata else '',error[:2000],retry_at))

    def enqueue(self, channel_id, metadata):
        # Pause and enqueue serialize. A crash between the two DB commits is safe:
        # queue origin_key deduplicates the next attempt, including completed jobs.
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            channel = self.decode(db.execute('SELECT * FROM channels WHERE id=?',(channel_id,)).fetchone())
            if not channel or not channel['enabled']:return None
            item, _ = QueueStore(self.root).add_youtube(metadata,channel['settings'])
            db.execute("UPDATE videos SET state='queued',queue_id=?,error='' WHERE channel_id=? AND id=?",
                       (item['id'],channel_id,metadata['id']))
            return item


def check_channel(store, channel, now, discovery=discover, inspector=lookup):
    channel_id = channel['id']
    store.update(channel_id,status='Checking recent uploads',next_check=now+POLL_SECONDS)
    found = discovery(channel['url'])
    if found['id']!=channel_id:raise ValueError('The saved channel link resolved to a different channel.')
    history = {r['id']:r for r in store.videos(channel_id)}
    candidates = []
    newest = None
    for index, entry in enumerate(found['entries']):
        if not store.get(channel_id)['enabled']:return
        if entry.get('live_status') in ('is_live','is_upcoming','post_live'):continue
        prior = history.get(entry['id'])
        if newest is None:newest = entry['id']
        if prior and (prior['queue_id'] or prior['retry_at']>now):
            if prior['state']=='waiting' and entry['id']==newest:newest = None
            continue
        if prior and prior['state']=='old' and entry['id']!=newest:continue
        store.update(channel_id,status=f"Checking upload {index+1} of {len(found['entries'])}")
        try:
            metadata = (prior or {}).get('metadata') or inspector(entry['url'])
            if metadata.get('channel_id')!=channel_id:raise ValueError('Upload does not belong to this channel.')
            if not metadata.get('duration'):raise UnfinishedVideo('Video is still processing or has no duration.')
            keep = eligible(metadata,newest,now)
            if metadata['published']>now:raise UnfinishedVideo('Upload has not been published yet.')
        except UnfinishedVideo as error:
            # A premiere can become eligible on a later check.
            if entry['id']==newest:newest = None
            store.record(channel_id,entry,'waiting',error=str(error),retry_at=now+POLL_SECONDS)
        except Exception as error:
            from app_logging import redact, log_exception
            log_exception('Channel upload lookup failed')
            store.record(channel_id,entry,'error',error=redact(str(error)) or type(error).__name__,retry_at=now+POLL_SECONDS)
        else:
            store.record(channel_id,entry,'ready' if keep else 'old',metadata)
            if keep:candidates.append(metadata)
    # Process recent uploads oldest first, then preserve FIFO across later polls.
    added = 0
    for metadata in sorted(candidates,key=lambda m:m['published']):
        if store.enqueue(channel_id,metadata):added += 1
    current = store.get(channel_id)
    if current['enabled']:
        store.update(channel_id,checked=now,failures=0,error='',next_check=now+POLL_SECONDS,
                     status=f'{added} uploads sent to the queue' if added else 'Watching for new uploads')


def tick(store, now=None, discovery=discover, inspector=lookup, launch=ensure_runner):
    now = time.time() if now is None else now
    for channel in store.channels():
        if not channel['enabled'] or channel['next_check']>now:continue
        try:check_channel(store,channel,now,discovery,inspector)
        except Exception as error:
            from app_logging import redact, log_exception
            log_exception('YouTube channel check failed')
            failures = channel['failures']+1
            store.update(channel['id'],failures=failures,error=redact(str(error)) or type(error).__name__,
                         status='Could not check channel; will retry',next_check=now+min(3600,POLL_SECONDS*2**min(failures-1,4)))
    queue = QueueStore(store.root)
    queue.auto_start()
    launch(store.root)


def watcher_alive(root):
    path = Path(root)/'work/channel-watch.lock'
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return True
    return False


def ensure_watcher(root):
    root = Path(root).resolve()
    if not (root/'data/channel-watch.sqlite3').exists():return
    if not any(c['enabled'] for c in WatchStore(root).channels()) or watcher_alive(root):return
    with (root/'work/channel-watch.log').open('a') as log:
        subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--root',str(root)],cwd=root,
                         stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)


def run(root, poll=2, check=tick):
    store = WatchStore(root)
    path = store.root/'work/channel-watch.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        # Retry an interrupted scan promptly on app restart, keeping all receipts.
        for channel in store.channels():
            if channel['enabled']:store.request_check(channel['id'])
        while any(c['enabled'] for c in store.channels()):
            check(store)
            time.sleep(poll)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM,lambda *args:sys.exit(0))
    if Path('/usr/bin/caffeinate').is_file():
        subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(os.getpid())],stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    run(args.root)
