"""Local publishing records. Credentials are deliberately stored elsewhere."""
import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager, closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data' / 'social.sqlite3'

@contextmanager
def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB, timeout=15)) as db, db:
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
        yield db
    DB.chmod(0o600)

def accounts():
    with connection() as db:
        return [json.loads(r['data']) for r in db.execute('SELECT data FROM accounts')]

def save_account(account):
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO accounts VALUES (?,?)', (account['id'], json.dumps(account)))

def remove_account(account_id):
    with connection() as db:
        db.execute('DELETE FROM accounts WHERE id=?', (account_id,))

def get(draft_id):
    with connection() as db:
        row = db.execute('SELECT data FROM drafts WHERE id=?', (draft_id,)).fetchone()
        return json.loads(row['data']) if row else None

def drafts(folder=None):
    with connection() as db:
        rows = [json.loads(r['data']) for r in db.execute('SELECT data FROM drafts')]
    return sorted([r for r in rows if folder is None or r['folder'] == str(folder)], key=lambda r:r['updated'], reverse=True)

def save(draft):
    draft = dict(draft, updated=time.time())
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO drafts VALUES (?,?)', (draft['id'], json.dumps(draft)))
    return draft

def identity(folder, run, candidate, account_id, render_id):
    from clip_usage import clip_key
    return hashlib.sha256(f'{folder}:{clip_key(run,candidate)}:{account_id}:{render_id}'.encode()).hexdigest()[:32]

def validate(draft):
    if draft.get("project_deleted") or not Path(draft["folder"]).is_dir():
        raise ValueError("This project was deleted. Its saved drafts cannot be published.")
    if not Path(draft['video']).is_file():
        raise ValueError('The rendered video is missing. Open the clip editor to render it again.')
    stat=Path(draft['video']).stat()
    if stat.st_size==0:
        raise ValueError('The video file is empty. Render the clip again.')
    if draft.get('file_size',stat.st_size)!=stat.st_size or draft.get('file_mtime',stat.st_mtime_ns)!=stat.st_mtime_ns:
        raise ValueError('This video changed after the draft was saved. Open the clip editor and create a fresh draft.')
    if draft['platform'] == 'youtube':
        title = draft['title'].strip()
        if not title or len(title)>100 or '<' in title or '>' in title:
            raise ValueError('YouTube titles need 1–100 characters and cannot contain < or >.')
        if len(draft['description'].encode('utf-8'))>5000:
            raise ValueError('The YouTube description exceeds 5,000 bytes.')
        if draft.get('privacy') not in ('private','unlisted','public') or type(draft.get('made_for_kids')) is not bool:
            raise ValueError('Choose visibility and whether this video is made for kids.')
    elif draft['platform'] == 'instagram':
        if len(draft['description'])>2200 or draft['description'].count('#')>30:
            raise ValueError('Instagram captions must fit 2,200 characters and 30 hashtags.')
    else:
        raise ValueError('Choose YouTube or Instagram.')


def save_draft(draft):
    """Do not let a stale browser overwrite an upload already in progress."""
    draft=dict(draft,updated=time.time())
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT data FROM drafts WHERE id=?',(draft['id'],)).fetchone()
        if row and json.loads(row['data'])['status']!='Draft':
            raise ValueError('This draft already has a posting attempt. Refresh to check its status.')
        db.execute('INSERT OR REPLACE INTO drafts VALUES (?,?)',(draft['id'],json.dumps(draft)))
    return draft


def claim(draft_id, updated):
    """Freeze the reviewed snapshot before any account refresh/network operation."""
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT data FROM drafts WHERE id=?',(draft_id,)).fetchone()
        current=json.loads(row['data']) if row else None
        if not current or current['updated']!=updated:
            raise ValueError('This draft changed after review. Refresh and review it again.')
        current.update(status='Starting',updated=time.time())
        db.execute('UPDATE drafts SET data=? WHERE id=?',(json.dumps(current),draft_id))
