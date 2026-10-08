"""Direct YouTube import. No search quota, cookies, or account credentials."""
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import imageio_ffmpeg
from yt_dlp import YoutubeDL
from engine import ROOT, duration
YOUTUBE_IMPORT_API = 2


class UnfinishedVideo(ValueError):
    pass


def normalize_url(value):
    value = value.strip()
    if '://' not in value:
        value = 'https://' + value
    parsed = urlparse(value)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        raise ValueError('Paste a valid YouTube video link.')
    host = (parsed.hostname or '').lower()
    parts = parsed.path.strip('/').split('/')
    if host == 'youtu.be':
        video_id = parts[0]
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        elif len(parts) == 2 and parts[0] in ('shorts', 'embed', 'live'):
            video_id = parts[1]
        else:
            video_id = ''
    else:
        video_id = ''
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise ValueError('Use a YouTube video or Shorts link, not a channel or playlist link.')
    return 'https://www.youtube.com/watch?v=' + video_id, video_id


class AppLogger:
    """yt-dlp must never write to the launching terminal's possibly closed pipe."""
    def debug(self,message): pass
    def info(self,message): pass
    def warning(self,message): pass
    def error(self,message): pass


def options():
    node = shutil.which('node') or '/opt/homebrew/bin/node'
    return {'quiet': True, 'no_warnings': True, 'noplaylist': True,
            'noprogress': True, 'logger': AppLogger(),
            'socket_timeout': 25, 'retries': 2, 'extractor_retries': 2,
            'js_runtimes': {'node': {'path': node}},
            'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe()}


def lookup(value):
    url, video_id = normalize_url(value)
    with YoutubeDL(options()) as downloader:
        info = downloader.extract_info(url, download=False)
    if not info or info.get('is_live') or info.get('live_status') in ('is_live', 'is_upcoming', 'post_live'):
        raise UnfinishedVideo('Use a finished video. Live and upcoming streams are not supported.')
    return {'id': video_id, 'url': url, 'title': info.get('title') or video_id,
            'channel': info.get('uploader') or '', 'channel_id': info.get('channel_id') or '',
            'published': info.get('release_timestamp') or info.get('timestamp'),
            'duration': info.get('duration') or 0}


def download(metadata, progress=lambda message: None, root=None):
    url, video_id = normalize_url(metadata['url'])
    folder = Path(root or ROOT) / 'data' / ('youtube-' + video_id)
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder / 'import.json'
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        source = folder / Path(saved['filename']).name
        if source.exists():
            duration(source)
            return source, folder
    def hook(event):
        if event['status'] == 'downloading':
            total = event.get('total_bytes') or event.get('total_bytes_estimate')
            downloaded = event.get('downloaded_bytes', 0)
            if downloaded > 4 * 1024**3:
                raise ValueError('Import exceeds 4 GB. Upload a smaller local copy instead.')
            progress(f'Downloading video… {downloaded / total:.0%}' if total else 'Downloading video…')
        elif event['status'] == 'finished':
            progress('Preparing the local video…')
    opts = options()
    opts.update({'format': 'bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b[height<=720]',
                 'merge_output_format': 'mp4', 'outtmpl': str(folder / 'source.%(ext)s'),
                 'max_filesize': 4 * 1024**3, 'progress_hooks': [hook]})
    with YoutubeDL(opts) as downloader:
        downloader.extract_info(url, download=True)
    sources = [p for p in folder.glob('source.*') if p.suffix in ('.mp4', '.mkv', '.webm', '.mov')]
    if not sources:
        raise ValueError('YouTube did not provide a downloadable video within the size limit.')
    source = max(sources, key=lambda p: p.stat().st_mtime)
    duration(source)
    manifest.write_text(json.dumps({**metadata, 'filename': source.name}, indent=2))
    return source, folder
