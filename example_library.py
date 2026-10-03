"""Local editorial references. This library does not change AI decisions."""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from project_store import write

SCHEMA_VERSION = 1
LABELS = ('Good pattern', 'Mixed example', 'Avoid this pattern')
FORMATS = ('Interview', 'Podcast', 'On-field sports', 'Other')
STATUSES = ('Needs review', 'Ready for future reference', 'Excluded')


def directory(root):
    return Path(root) / 'data' / 'example-library'


def load(root):
    path = directory(root) / 'library.json'
    if not path.exists():
        return dict(schema_version=SCHEMA_VERSION, examples=[], imports=[])
    try:
        bank = json.loads(path.read_text())
        examples = bank['examples']
        if bank['schema_version'] != SCHEMA_VERSION or not isinstance(examples, list):
            raise ValueError('Unsupported example library format.')
        ids = [e['id'] for e in examples]
        if len(ids) != len(set(ids)) or any(not isinstance(e, dict) for e in examples):
            raise ValueError('Invalid example records.')
        for record in examples:
            _validate_choices(record)
            if not isinstance(record['analytics'], dict) or not isinstance(record['observations'], dict):
                raise ValueError('Invalid example notes or analytics.')
            if any(not isinstance(record['observations'][key], list) or
                   any(not isinstance(line, str) for line in record['observations'][key])
                   for key in ('strengths', 'cautions')):
                raise ValueError('Invalid example observations.')
        return bank
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise ValueError('The saved example library could not be read. Its file was preserved.') from error


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def import_review(root, review):
    """Import reviewed assets once; repeated imports preserve all existing edits."""
    bank = load(root)
    seen = {e['id'] for e in bank['examples']}
    pending = []
    for row in review['examples']:
        identity = row['sha256']
        if identity in seen:
            continue
        source = Path(row['source'])
        if _hash(source) != identity:
            raise ValueError('A supplied clip changed since its review: ' + source.name)
        transcript = json.loads(Path(row['transcript']).read_text())
        frames = Path(row['frames']).read_bytes()
        observations = copy.deepcopy(row['editorial_observations'])
        record = dict(
            id=identity, name=row['filename'].removesuffix('.mp4'),
            posted_title=row.get('actual_post_title') or '', opening_text=row.get('opening_text', ''),
            content_format=row.get('content_format', 'Other'),
            label=row.get('label', 'Mixed example'), status='Needs review',
            source=str(source.resolve()), duration=row['duration'],
            source_sha256=identity, source_bytes=row['bytes'],
            transcript=transcript, transcript_text=row['text'],
            transcript_reviewed=False, frame_sheet='assets/' + identity + '.jpg',
            observations=observations, notes='', analytics=copy.deepcopy(row.get('analytics') or {}),
            analytics_match=copy.deepcopy(row.get('association') or {}), analytics_match_confirmed=False,
            analytics_period=review.get('export_period_from_filename', []),
            performance_label=row.get('performance_label', 'User-supplied example'),
            created=_now(), updated=_now())
        _validate_choices(record)
        pending.append((record, frames))
        seen.add(identity)
    # Validate all source assets before saving any records or copying frame sheets.
    for record, frames in pending:
        target = directory(root) / record['frame_sheet']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(frames)
        bank['examples'].append(record)
    archive = review.get('archive_sha256')
    if archive and not any(i.get('archive_sha256') == archive for i in bank.get('imports', [])):
        bank.setdefault('imports', []).append(dict(
            archive_sha256=archive, period=review.get('export_period_from_filename', []),
            exported_totals=review.get('exported_channel_totals', {}),
            limitations=review.get('limitations', [])))
    if pending:
        write(directory(root) / 'library.json', bank)
    return len(pending)


def _validate_choices(record):
    for field, choices in (('label', LABELS), ('content_format', FORMATS), ('status', STATUSES)):
        if record[field] not in choices:
            raise ValueError('Choose a valid ' + field.replace('_', ' ') + '.')


def save_notes(root, identity, **changes):
    allowed = {'name', 'posted_title', 'opening_text', 'content_format', 'label', 'status',
               'notes', 'observations', 'analytics_match_confirmed', 'transcript_reviewed'}
    if set(changes) - allowed:
        raise ValueError('Reference notes cannot replace the original media, transcript or analytics.')
    bank = load(root)
    record = next((e for e in bank['examples'] if e['id'] == identity), None)
    if record is None:
        raise ValueError('This example is no longer in the library.')
    record.update(copy.deepcopy(changes))
    if not record['name'].strip():
        raise ValueError('Give the example a name.')
    _validate_choices(record)
    record['updated'] = _now()
    write(directory(root) / 'library.json', bank)
    return record


def add_clip(root, data, filename, name, posted_title='', content_format='Other',
             strengths='', cautions='', transcript_text=''):
    """Store a new supplied clip without transcription, inference or rendering."""
    if not data or not name.strip():
        raise ValueError('Choose a clip and give the example a name.')
    bank = load(root)
    identity = hashlib.sha256(data).hexdigest()
    existing = next((e for e in bank['examples'] if e['id'] == identity), None)
    if existing:
        return existing, False
    extension = Path(filename).suffix.lower()
    if extension not in ('.mp4', '.mov', '.m4v', '.webm', '.mkv'):
        raise ValueError('Choose a supported video file.')
    # Probe supplied bytes before storing them as a playable example.
    import av
    import io
    try:
        with av.open(io.BytesIO(data)) as media:
            if not media.streams.video:
                raise ValueError('This file has no video stream.')
            stream = media.streams.video[0]
            duration = float(media.duration / av.time_base) if media.duration else float(stream.duration * stream.time_base)
    except (av.error.FFmpegError, TypeError, ZeroDivisionError) as error:
        raise ValueError('This video could not be read. Choose a playable clip.') from error
    target = directory(root) / 'assets' / (identity + extension)
    record = dict(id=identity, name=name.strip(), posted_title=posted_title.strip(), opening_text='',
                  content_format=content_format, label='Mixed example', status='Needs review',
                  source=str(target.resolve()), duration=duration, source_sha256=identity,
                  source_bytes=len(data), transcript={}, transcript_text=transcript_text.strip(),
                  transcript_reviewed=False, frame_sheet=None,
                  observations=dict(strengths=strengths.splitlines(), cautions=cautions.splitlines(), role=''),
                  notes='', analytics={}, analytics_match={}, analytics_match_confirmed=False,
                  analytics_period=[], performance_label='User-supplied example', created=_now(), updated=_now())
    _validate_choices(record)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    bank['examples'].append(record)
    write(directory(root) / 'library.json', bank)
    return record, True


def available_references(root):
    """Future callers can request human-marked references; no pipeline calls this yet."""
    return [e for e in load(root)['examples'] if e['status'] == 'Ready for future reference']
