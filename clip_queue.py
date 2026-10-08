"""Durable local FIFO clipping queue; project/settings snapshots are immutable."""
import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

ACTIVE = ('queued', 'running')
QUEUE_API = 2


class SourceSkipped(ValueError):
    """A watched upload is no longer eligible, rather than a processing failure."""


class QueueStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.path = self.root/'data/clipping-queue.sqlite3'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS control (id INTEGER PRIMARY KEY, enabled INTEGER NOT NULL);
                INSERT OR IGNORE INTO control (id,enabled) VALUES (1, 0);
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY, position INTEGER NOT NULL, state TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, project TEXT NOT NULL, settings TEXT NOT NULL,
                    source_state TEXT NOT NULL, export_clips INTEGER NOT NULL,
                    created REAL NOT NULL, started REAL, finished REAL, attempts INTEGER NOT NULL DEFAULT 0,
                    progress REAL NOT NULL DEFAULT 0, label TEXT NOT NULL DEFAULT 'Waiting', estimate REAL NOT NULL DEFAULT 0,
                    result TEXT, exports TEXT NOT NULL DEFAULT '[]', error TEXT NOT NULL DEFAULT '');
            ''')
            db.execute('BEGIN IMMEDIATE')
            if 'paused' not in {r[1] for r in db.execute('PRAGMA table_info(control)')}:
                db.execute('ALTER TABLE control ADD COLUMN paused INTEGER NOT NULL DEFAULT 0')
                db.execute("UPDATE control SET paused=1 WHERE enabled=0 AND EXISTS (SELECT 1 FROM items WHERE state IN ('queued','running'))")
            columns = {r[1] for r in db.execute('PRAGMA table_info(items)')}
            if 'remote' not in columns:db.execute("ALTER TABLE items ADD COLUMN remote TEXT NOT NULL DEFAULT ''")
            if 'origin_key' not in columns:db.execute('ALTER TABLE items ADD COLUMN origin_key TEXT')
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS queue_origin ON items(origin_key)')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def decode(row):
        if row is None:
            return None
        item = dict(row)
        for field in ('project', 'settings', 'source_state', 'exports'):
            item[field] = json.loads(item[field])
        item['export_clips'] = bool(item['export_clips'])
        item['remote'] = json.loads(item['remote']) if item['remote'] else None
        return item

    def items(self):
        with self.connection() as db:
            return [self.decode(row) for row in db.execute('SELECT * FROM items ORDER BY position, created')]

    def get(self, identity):
        with self.connection() as db:
            return self.decode(db.execute('SELECT * FROM items WHERE id=?', (identity,)).fetchone())

    def enabled(self):
        with self.connection() as db:
            return bool(db.execute('SELECT enabled FROM control WHERE id=1').fetchone()[0])

    def set_enabled(self, enabled):
        with self.connection() as db:
            db.execute('UPDATE control SET enabled=?,paused=? WHERE id=1', (int(bool(enabled)), int(not enabled)))

    def paused(self):
        with self.connection() as db:
            return bool(db.execute('SELECT paused FROM control WHERE id=1').fetchone()[0])

    def auto_start(self):
        """Watching can restart an idle queue, but never override an explicit pause."""
        with self.connection() as db:
            db.execute("UPDATE control SET enabled=1 WHERE paused=0 AND EXISTS (SELECT 1 FROM items WHERE state='queued')")

    def idle(self):
        with self.connection() as db:
            db.execute('UPDATE control SET enabled=0 WHERE id=1')

    def add_youtube(self, metadata, settings):
        """Persist the import before any download. Unique IDs survive crashes and retries."""
        from analysis_settings import AnalysisSettings
        from youtube_import import normalize_url
        AnalysisSettings.read(settings)
        url, video_id = normalize_url(metadata['url'])
        remote = dict(metadata, id=video_id, url=url)
        folder = self.root/'data'/('youtube-'+video_id)
        project = dict(folder=str(folder), source='', title=metadata['title'], duration=metadata['duration'])
        key = 'youtube:'+video_id
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT * FROM items WHERE origin_key=?', (key,)).fetchone()
            if prior:return self.decode(prior), False
            # A manually queued/completed project also counts as already handled.
            prior = next((r for r in db.execute("SELECT * FROM items WHERE state!='cancelled'")
                          if Path(json.loads(r['project'])['folder']).resolve()==folder), None)
            if prior:
                db.execute('UPDATE items SET origin_key=? WHERE id=?', (key, prior['id']))
                return self.decode(db.execute('SELECT * FROM items WHERE id=?', (prior['id'],)).fetchone()), False
            identity = uuid.uuid4().hex
            position = db.execute('SELECT COALESCE(MAX(position),0)+1 FROM items').fetchone()[0]
            db.execute('''INSERT INTO items (id,position,state,fingerprint,project,settings,source_state,export_clips,created,remote,origin_key,label)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (identity,position,'queued',key,json.dumps(project),
                          json.dumps(settings),'[]',1,time.time(),json.dumps(remote),key,'Waiting to import from YouTube'))
            return self.decode(db.execute('SELECT * FROM items WHERE id=?', (identity,)).fetchone()), True

    def prepared(self, identity, project):
        stat = Path(project['source']).stat()
        with self.connection() as db:
            db.execute("UPDATE items SET project=?,source_state=? WHERE id=? AND state='running'",
                       (json.dumps(project),json.dumps([stat.st_size,stat.st_mtime_ns]),identity))
        return self.get(identity)

    def configured(self, identity, settings):
        from analysis_settings import AnalysisSettings
        AnalysisSettings.read(settings)
        with self.connection() as db:
            db.execute("UPDATE items SET settings=? WHERE id=? AND state='running'",(json.dumps(settings),identity))
        return self.get(identity)

    def add(self, project, settings, export_clips=True):
        from analysis_settings import AnalysisSettings
        AnalysisSettings.read(settings)
        project = dict(project)
        folder = Path(project['folder']).resolve()
        if folder.parent != (self.root/'data').resolve() or not folder.is_dir():
            raise ValueError('Choose an imported project in this app.')
        source = Path(project['source']).resolve()
        stat = source.stat()
        if not source.is_file():
            raise ValueError('The source video is missing.')
        from engine import duration
        project.update(folder=str(folder), source=str(source), duration=project.get('duration') or duration(source))
        source_state = [stat.st_size, stat.st_mtime_ns]
        encoded = json.dumps([str(folder), str(source), source_state, settings], sort_keys=True)
        fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute("SELECT * FROM items WHERE fingerprint=? AND state IN ('queued','running')", (fingerprint,)).fetchone()
            if prior:
                return self.decode(prior), False
            identity = uuid.uuid4().hex
            position = db.execute('SELECT COALESCE(MAX(position),0)+1 FROM items').fetchone()[0]
            db.execute('''INSERT INTO items (id,position,state,fingerprint,project,settings,source_state,export_clips,created)
                          VALUES (?,?,?,?,?,?,?,?,?)''', (identity, position, 'queued', fingerprint,
                          json.dumps(project), json.dumps(settings), json.dumps(source_state), int(bool(export_clips)), time.time()))
            return self.decode(db.execute('SELECT * FROM items WHERE id=?', (identity,)).fetchone()), True

    def claim(self):
        """Call only while owning both the runner lock and the heavy-job lock."""
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT enabled FROM control WHERE id=1').fetchone()[0]:
                return None
            row = db.execute("SELECT * FROM items WHERE state='queued' ORDER BY position,created LIMIT 1").fetchone()
            if row is None:
                db.execute('UPDATE control SET enabled=0 WHERE id=1')
                return None
            db.execute("UPDATE items SET state='running',started=?,finished=NULL,attempts=attempts+1,progress=0,label='Starting',error='' WHERE id=?", (time.time(), row['id']))
            return self.decode(db.execute('SELECT * FROM items WHERE id=?', (row['id'],)).fetchone())

    def update(self, identity, **fields):
        allowed = {'progress', 'label', 'result', 'exports', 'estimate'}
        if not fields or not fields.keys() <= allowed:
            raise ValueError('Unsupported queue progress update.')
        values = [json.dumps(value) if key == 'exports' else value for key, value in fields.items()]
        with self.connection() as db:
            db.execute('UPDATE items SET '+','.join(key+'=?' for key in fields)+" WHERE id=? AND state='running'", (*values, identity))

    def finish(self, identity, error=''):
        with self.connection() as db:
            db.execute("UPDATE items SET state=?,finished=?,progress=CASE WHEN ?='' THEN 1 ELSE progress END,label=?,error=? WHERE id=? AND state='running'",
                       ('failed' if error else 'done', time.time(), error, 'Needs attention' if error else 'Complete', error[:2000], identity))

    def skip(self, identity, reason):
        with self.connection() as db:
            db.execute("UPDATE items SET state='skipped',finished=?,label='Skipped',error=? WHERE id=? AND state='running'",
                       (time.time(),reason[:2000],identity))

    def recover(self):
        """Only the process holding the exclusive runner lock may recover a lost run."""
        with self.connection() as db:
            db.execute("UPDATE items SET state='queued',started=NULL,progress=0,label='Resuming saved work' WHERE state='running'")

    def retry(self, identity):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT fingerprint FROM items WHERE id=? AND state='failed'", (identity,)).fetchone()
            if not row:
                return False
            duplicate = db.execute("SELECT 1 FROM items WHERE fingerprint=? AND state IN ('queued','running')", (row[0],)).fetchone()
            if duplicate:
                raise ValueError('This video with these settings is already waiting or processing.')
            position = db.execute('SELECT COALESCE(MAX(position),0)+1 FROM items').fetchone()[0]
            db.execute("UPDATE items SET state='queued',position=?,started=NULL,finished=NULL,progress=0,label='Waiting to retry',error='' WHERE id=?", (position, identity))
            return True

    def remove(self, identity):
        with self.connection() as db:
            return bool(db.execute("UPDATE items SET state='cancelled',finished=?,label='Removed from queue' WHERE id=? AND state='queued'", (time.time(), identity)).rowcount)

    def move(self, identity, direction):
        if direction not in (-1, 1):
            raise ValueError('Choose up or down.')
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = db.execute("SELECT id,position FROM items WHERE state='queued' ORDER BY position,created").fetchall()
            index = next((i for i, row in enumerate(rows) if row['id'] == identity), -1)
            other = index+direction
            if index < 0 or not 0 <= other < len(rows):
                return False
            db.execute('UPDATE items SET position=? WHERE id=?', (rows[other]['position'], identity))
            db.execute('UPDATE items SET position=? WHERE id=?', (rows[index]['position'], rows[other]['id']))
            return True

    def active_for(self, folder):
        return any(Path(item['project']['folder']).resolve() == Path(folder).resolve() and item['state'] in ACTIVE for item in self.items())


def runner_alive(root):
    import fcntl
    path = Path(root)/'work/clip-queue-runner.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
    return False


def ensure_runner(root, closed_lid=False):
    """Launch independently of the browser; concurrent launches safely elect one runner."""
    import subprocess
    import sys
    root = Path(root).resolve()
    store = QueueStore(root)
    if not store.enabled() or runner_alive(root):
        return
    if not any(item['state'] in ACTIVE for item in store.items()):
        store.idle()
        return
    with (root/'work/clip-queue-runner.log').open('a') as log:
        command = [sys.executable, str(Path(__file__).with_name('queue_runner.py')), '--root', str(root)]
        if closed_lid:command.append('--closed-lid')
        subprocess.Popen(command,
                         cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)


def resume_enabled_queue(root):
    """Do not create runtime files merely by opening an app that has no queue."""
    if (Path(root)/'data/clipping-queue.sqlite3').exists():
        ensure_runner(root)
