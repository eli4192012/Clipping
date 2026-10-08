"""Public channel discovery via the existing yt-dlp dependency. No OAuth or API key."""
import math
import re
import time
from urllib.parse import quote, unquote, urlparse

from youtube_import import YoutubeDL, options

CHANNEL_ID = r'UC[A-Za-z0-9_-]{22}'
VIDEO_ID = r'[A-Za-z0-9_-]{11}'
UPLOAD_LIMIT = 50
RECENT_SECONDS = 48*60*60


def normalize_channel(value):
    value = value.strip()
    if value.startswith('@'):value = 'https://www.youtube.com/'+value
    if '://' not in value:value = 'https://'+value
    parsed = urlparse(value)
    if (parsed.scheme not in ('https','http') or parsed.username or parsed.password
            or parsed.hostname not in ('youtube.com','www.youtube.com','m.youtube.com')
            or parsed.port not in (None,80,443)):
        raise ValueError('Paste a public YouTube channel link or @handle.')
    parts = unquote(parsed.path).strip('/').split('/')
    if parts[-1] in ('videos','featured','shorts','streams'):parts.pop()
    valid = (len(parts)==1 and re.fullmatch(r'@[\w.-]+',parts[0])) or (
        len(parts)==2 and ((parts[0]=='channel' and re.fullmatch(CHANNEL_ID,parts[1]))
                          or (parts[0] in ('c','user') and re.fullmatch(r'[\w.-]+',parts[1]))))
    if not valid:raise ValueError('Use a channel link, rather than a video or playlist link.')
    return 'https://www.youtube.com/'+quote('/'.join(parts),safe='/@')+'/videos'


def discover(value, limit=UPLOAD_LIMIT):
    url = normalize_channel(value)
    opts = options()
    opts.update(noplaylist=False, extract_flat=True, playlistend=limit)
    with YoutubeDL(opts) as downloader:
        info = downloader.extract_info(url,download=False)
    channel_id = info.get('channel_id') if isinstance(info,dict) else None
    if not channel_id or not re.fullmatch(CHANNEL_ID,channel_id):
        raise ValueError('This channel could not be found. Check its public channel link.')
    entries = []
    for raw in info.get('entries') or []:
        if not isinstance(raw,dict) or not re.fullmatch(VIDEO_ID,raw.get('id') or ''):continue
        entries.append(dict(id=raw['id'],url='https://www.youtube.com/watch?v='+raw['id'],
                            title=raw.get('title') or raw['id'],live_status=raw.get('live_status')))
    return dict(id=channel_id,name=info.get('channel') or info.get('uploader') or channel_id,
                url='https://www.youtube.com/channel/'+channel_id+'/videos',entries=entries)


def eligible(metadata, newest_id, now=None):
    """Use the full video's timestamp, never rounded channel-page dates."""
    now = time.time() if now is None else now
    published = metadata.get('published')
    if type(published) not in (int,float) or not math.isfinite(published) or published<=0:
        raise ValueError('YouTube did not provide a publication time; this video was not queued.')
    return published<=now and (now-published<=RECENT_SECONDS or metadata['id']==newest_id)


def automatic_settings(settings, detected):
    """Resolve the per-video mode without changing the saved channel preferences."""
    from modes import PROFILES
    mode = detected['mode']
    if mode not in PROFILES:raise ValueError('The detector returned an unsupported clip mode.')
    categories = detected.get('categories') or [mode]
    speech_min = settings.get('watch_speech_minimum',settings['minimum'])
    speech_max = settings.get('watch_speech_maximum',settings['maximum'])
    speech_coverage = settings.get('watch_speech_coverage',settings.get('coverage',1.))
    minimum,maximum = PROFILES['Sports']['lengths'] if mode=='Sports' else (speech_min,speech_max)
    return dict(settings,mode=mode,categories=categories,category_selection=['Let AI detect'],auto_mode=True,
                video_type=detected,minimum=minimum,maximum=maximum,semantic=mode!='Sports',
                vision=mode=='Sports' and 'American football' in categories and settings.get('watch_sports_vision',False),
                shorts_editor=mode!='Sports',scenes=mode=='Sports',coverage=.35 if mode=='Sports' else speech_coverage,
                watch_speech_minimum=speech_min,watch_speech_maximum=speech_max,watch_speech_coverage=speech_coverage)


def prepare_item(store, item):
    """Imports run under the queue's heavy-job lock, before local analysis."""
    from clip_queue import SourceSkipped
    from youtube_import import lookup, download, UnfinishedVideo
    from project_store import write
    remote = item['remote']
    try:metadata = lookup(remote['url'])
    except UnfinishedVideo as error:raise SourceSkipped(str(error)) from error
    if metadata.get('channel_id') != remote.get('channel_id'):
        raise ValueError('This upload no longer matches the connected source channel.')
    newest = remote['id']
    if time.time()-(metadata.get('published') or 0)>RECENT_SECONDS:
        channel = discover('https://www.youtube.com/channel/'+remote['channel_id'])
        newest = None
        for entry in channel['entries']:
            if entry.get('live_status') in ('is_live','is_upcoming','post_live'):continue
            try:latest = metadata if entry['id']==metadata['id'] else lookup(entry['url'])
            except UnfinishedVideo:continue
            if latest.get('duration') and latest.get('published') and latest['published']<=time.time():
                newest = entry['id'];break
    if not eligible(metadata,newest):
        raise SourceSkipped('This video is now older than two days and is no longer the newest upload.')
    store.update(item['id'],label='Downloading from YouTube')
    source, folder = download(metadata,lambda text: store.update(item['id'],label=text),root=store.root)
    project = dict(source=str(source),folder=str(folder),title=metadata['title'],
                   channel=metadata['channel'],duration=metadata['duration'])
    # A previously imported project's preferences and manual work remain authoritative.
    if not (folder/'project.json').exists():write(folder/'project.json',project)
    if not (folder/'ui-settings.json').exists():write(folder/'ui-settings.json',item['settings'])
    item = store.prepared(item['id'],project)
    store.update(item['id'],progress=.08,label='Video imported; preparing local analysis')
    return item
