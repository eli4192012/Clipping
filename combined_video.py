"""Saved clip assemblies and bounded, local FFmpeg exports. No analysis or inference."""
import hashlib
import json
import math
import re
import uuid
from pathlib import Path
from project_store import read, write

VERSION = 'combined-video-1'
FORMATS = {'Wide · 16:9': (1280, 720), 'Vertical · 9:16': (720, 1280)}
FPS = 30


def clip_id(video):
    return hashlib.sha256(str(Path(video).resolve()).encode()).hexdigest()[:20]


def register_clip(folder, video, captions, title, project_title):
    """Index the exact finished export, preserving all source and edit records."""
    path = Path(folder)/'finished-clips.json'
    saved = read(path, {})
    key = clip_id(video)
    item = dict(id=key, video=str(Path(video).resolve()), captions=str(Path(captions).resolve()),
                title=str(title).strip() or 'Saved clip', project=project_title)
    if saved.get(key) != item:
        saved[key] = item
        write(path, saved)
    return item


def media_info(video, root=None):
    import av
    video = Path(video)
    stat = video.stat()
    key = fingerprint([str(video.resolve()), stat.st_size, stat.st_mtime_ns])
    cache = Path(root)/'work/assembly-media'/(key+'.json') if root else None
    saved = read(cache, None) if cache else None
    if saved:
        return saved
    with av.open(str(video)) as media:
        if not media.streams.video:
            raise ValueError('A selected file has no video stream.')
        stream = media.streams.video[0]
        length = float(media.duration/av.time_base) if media.duration else float((stream.duration or 0)*stream.time_base)
        if not math.isfinite(length) or length <= 0:
            raise ValueError('A selected clip has no readable duration.')
        result = dict(duration=length, width=stream.width, height=stream.height, audio=bool(media.streams.audio))
    if cache:
        write(cache, result)
    return result


def _old_title(video):
    ass = Path(video).with_suffix('.ass')
    if ass.is_file():
        for line in ass.read_text(errors='replace').splitlines():
            parts = line.split(',', 9)
            if line.startswith('Dialogue:') and len(parts) == 10 and parts[3] == 'Title':
                text = re.sub(r'\{[^}]*\}', '', parts[9]).replace('\\N', ' ')
                if text.strip():
                    return text.strip()
    from datetime import datetime
    return 'Saved clip · '+datetime.fromtimestamp(Path(video).stat().st_mtime).strftime('%b %d, %H:%M:%S')


def saved_clips(root):
    """Include old exports as well as newly indexed clips, without rerendering them."""
    root = Path(root)
    items = {}
    for folder in (root/'data').iterdir():
        if not folder.is_dir():
            continue
        project = read(folder/'project.json', {}).get('title', 'Saved project')
        for manifest in folder.glob('render-*.json'):
            paths = read(manifest, [])
            if isinstance(paths, list) and len(paths) == 2 and Path(paths[0]).is_file():
                key = clip_id(paths[0])
                items[key] = dict(id=key, video=paths[0], captions=paths[1], project=project)
        for key, item in read(folder/'finished-clips.json', {}).items():
            if isinstance(item, dict) and Path(item.get('video', '')).is_file():
                items[key] = item
    for video in (root/'exports').glob('clip-*.mp4'):
        key = clip_id(video)
        items.setdefault(key, dict(id=key, video=str(video.resolve()), captions=str(video.with_suffix('.srt').resolve()), project='Saved exports'))
    clips, errors = [], []
    for item in items.values():
        try:
            clips.append(dict(item, title=item.get('title') or _old_title(item['video']),
                              **media_info(item['video'], root)))
        except (OSError, ValueError, RuntimeError) as error:
            errors.append(str(error))
    clips.sort(key=lambda item: Path(item['video']).stat().st_mtime, reverse=True)
    return clips, errors


def new_draft():
    return dict(id=uuid.uuid4().hex[:16], title='Combined video', clips=[], format='Wide · 16:9', background='blur')


def save_draft(root, draft):
    if not re.fullmatch(r'[a-f0-9]{16}', draft['id']):
        raise ValueError('Invalid saved combination.')
    write(Path(root)/'data/assemblies'/(draft['id']+'.json'), draft)


def drafts(root):
    return [d for p in sorted((Path(root)/'data/assemblies').glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
            if isinstance(d := read(p, None), dict) and d.get('id') and isinstance(d.get('clips'), list)]


def move_clip(draft, index, direction):
    result = dict(draft, clips=list(draft['clips']))
    other = index+direction
    if 0 <= index < len(result['clips']) and 0 <= other < len(result['clips']):
        result['clips'][index], result['clips'][other] = result['clips'][other], result['clips'][index]
    return result


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:24]


def file_state(path):
    path = Path(path)
    stat = path.stat()
    return [str(path.resolve()), stat.st_size, stat.st_mtime_ns]


def _cues(path):
    if not path or not Path(path).is_file():
        return []
    pattern = r'(\d{2,}):(\d{2}):(\d{2})[,\.](\d{3})'
    cues = []
    for block in re.split(r'\n\s*\n', Path(path).read_text(encoding='utf-8-sig').replace('\r\n', '\n').strip()):
        lines = block.splitlines()
        at = next((i for i, line in enumerate(lines) if '-->' in line), None)
        if at is None:
            if block.strip():
                raise ValueError('A clip subtitle file is not valid SRT.')
            continue
        times = re.findall(pattern, lines[at])
        if len(times) != 2:
            raise ValueError('A clip subtitle timestamp is invalid.')
        values = [int(h)*3600+int(m)*60+int(s)+int(ms)/1000 for h, m, s, ms in times]
        if not 0 <= values[0] < values[1]:
            raise ValueError('A clip subtitle end must follow its start.')
        text = '\n'.join(lines[at+1:]).strip()
        if text:
            cues.append((*values, text))
    return cues


def join_captions(clips, durations):
    from engine import srt_timestamp
    lines, offset = [], 0.
    for clip, length in zip(clips, durations):
        for start, end, text in _cues(clip.get('captions')):
            start, end = min(start, length), min(end, length)
            if end > start:
                lines.append(f'{len(lines)+1}\n{srt_timestamp(offset+start)} --> {srt_timestamp(offset+end)}\n{text}\n')
        offset += length
    return '\n'.join(lines)


def assembly_fingerprint(draft):
    states = []
    for clip in draft['clips']:
        captions = clip.get('captions')
        states.append([file_state(clip['video']), file_state(captions) if captions and Path(captions).is_file() else None, clip['title']])
    return fingerprint([VERSION, states, FORMATS[draft['format']], draft['background'], FPS])


def _run(command, report, length):
    from ffmpeg_export import run_ffmpeg
    run_ffmpeg(command, length, report)


def _normalize(video, info, target, canvas, background, report):
    import imageio_ffmpeg
    width, height = canvas
    length = math.ceil(info['duration']*FPS-1e-6)/FPS
    start = '[0:v:0]setpts=PTS-STARTPTS,setsar=1,'
    if background == 'blur' and abs(info['width']/info['height']-width/height) > .01:
        graph = (start+'split=2[bg][fg];[bg]'+f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},boxblur=20:2[back];'
                 '[fg]'+f'scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2[front];'
                 '[back][front]overlay=(W-w)/2:(H-h)/2:shortest=1,')
    else:
        graph = start+f'scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x10141c,'
    graph += f'fps={FPS},tpad=stop_mode=clone:stop_duration={length:.6f},trim=duration={length:.6f},setsar=1,format=yuv420p[v]'
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y', '-threads', '2', '-i', str(video)]
    if not info['audio']:
        command += ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=48000']
    command += ['-filter_complex_threads', '2', '-filter_threads', '2', '-filter_complex', graph,
                '-map', '[v]', '-map', '0:a:0' if info['audio'] else '1:a:0',
                '-af', f'aresample=48000,asetpts=PTS-STARTPTS,apad,atrim=duration={length:.6f}',
                '-t', f'{length:.6f}', '-map_metadata', '-1', '-map_chapters', '-1',
                '-threads', '2', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-bf', '0',
                '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', '-progress', 'pipe:1', '-nostats', str(target)]
    _run(command, report, length)


def export_combination(root, draft, progress=lambda value, label: None):
    import imageio_ffmpeg
    root = Path(root)
    clips = draft['clips']
    if len(clips) < 2:
        raise ValueError('Add at least two clips to combine.')
    if draft['format'] not in FORMATS or draft.get('background') not in ('blur', 'dark'):
        raise ValueError('Choose a supported video format and background.')
    canvas = FORMATS[draft['format']]
    progress(0., 'Checking the selected clips')
    states, infos = [], []
    for clip in clips:
        infos.append(media_info(clip['video'], root))
        captions = clip.get('captions')
        _cues(captions)  # Validate before doing any encoding.
        states.append([file_state(clip['video']), file_state(captions) if captions and Path(captions).is_file() else None, clip['title']])
    key = assembly_fingerprint(draft)
    cache = root/'work/assembly-renders'/key
    saved = read(cache/'result.json', None)
    if saved and all(Path(saved[k]).is_file() for k in ('video', 'captions', 'chapters', 'manifest')):
        progress(1., 'Reused the saved combined video')
        return saved
    cache.mkdir(parents=True, exist_ok=True)
    parts = root/'work/assembly-renders/parts'
    parts.mkdir(parents=True, exist_ok=True)
    total = sum(info['duration'] for info in infos)
    completed, durations, paths = 0., [], []
    for index, (clip, info, state) in enumerate(zip(clips, infos, states)):
        part_key = fingerprint([VERSION, state[0], canvas, draft['background'], FPS])
        target = parts/(part_key+'.mkv')
        label = f'Preparing clip {index+1} of {len(clips)}'
        if not target.is_file():
            temporary = parts/(part_key+'-'+uuid.uuid4().hex+'.mkv')
            try:
                _normalize(clip['video'], info, temporary, canvas, draft['background'],
                           lambda at: progress(.05+.7*(completed+min(at, info['duration']))/total, label))
                media_info(temporary)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        paths.append(target)
        durations.append(media_info(target)['duration'])
        completed += info['duration']
        progress(.05+.7*completed/total, f'Clip {index+1} of {len(clips)} ready')
    captions = cache/'combined.srt'
    captions.write_text(join_captions(clips, durations), encoding='utf-8')
    offset, chapters = 0., []
    for clip, length in zip(clips, durations):
        chapters.append(dict(title=clip['title'], start=offset, end=offset+length, video=clip['video']))
        offset += length
    def escape(text):
        return re.sub(r'([\\=;#])', r'\\\1', ' '.join(str(text).split()))
    metadata = cache/'chapters.ffmetadata'
    metadata.write_text(';FFMETADATA1\n'+''.join(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={round(c['start']*1000)}\nEND={round(c['end']*1000)}\ntitle={escape(c['title'])}\n" for c in chapters))
    listing = cache/'parts.ffconcat'
    listing.write_text('ffconcat version 1.0\n'+''.join(f"file '../parts/{p.name}'\n" for p in paths))
    exports = root/'exports'
    exports.mkdir(parents=True, exist_ok=True)
    video = exports/('combined-'+key+'.mp4')
    temporary = cache/('output-'+uuid.uuid4().hex+'.mp4')
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y', '-threads', '2',
               '-f', 'concat', '-safe', '0', '-i', str(listing), '-f', 'ffmetadata', '-i', str(metadata)]
    if captions.read_text().strip():
        command += ['-i', str(captions), '-map', '2:s:0', '-c:s', 'mov_text', '-metadata:s:s:0', 'language=eng']
    command += ['-map', '0:v:0', '-map', '0:a:0', '-map_metadata', '1', '-map_chapters', '1',
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2',
                '-threads', '2', '-movflags', '+faststart', '-progress', 'pipe:1', '-nostats', str(temporary)]
    try:
        _run(command, lambda at: progress(.78+.17*min(1, at/offset), 'Joining clips and writing the combined video'), offset)
        output_info = media_info(temporary)
        temporary.replace(video)
    finally:
        temporary.unlink(missing_ok=True)
    final_srt = video.with_suffix('.srt')
    final_srt.write_text(captions.read_text(), encoding='utf-8')
    chapter_file = video.with_suffix('.chapters.txt')
    def timestamp(seconds):
        seconds = int(seconds)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        return f'{hours:02}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'
    chapter_file.write_text('\n'.join(timestamp(c['start'])+' '+c['title'] for c in chapters)+'\n')
    manifest = video.with_suffix('.assembly.json')
    result = dict(version=VERSION, fingerprint=key, video=str(video), captions=str(final_srt),
                  chapters=str(chapter_file), manifest=str(manifest), duration=output_info['duration'],
                  width=canvas[0], height=canvas[1], timeline=chapters)
    write(manifest, dict(result, clips=clips, format=draft['format'], background=draft['background']))
    write(cache/'result.json', result)
    progress(1., 'Combined video saved')
    return result
