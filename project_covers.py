"""Small, local project covers. Decode one keyframe once per source revision."""
import base64
import hashlib
import html
import io
from pathlib import Path


def cover_bytes(source, folder):
    source, folder = Path(source), Path(folder)
    try:
        stat = source.stat()
        key = hashlib.sha256(f'{source.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:cover2'.encode()).hexdigest()[:20]
        cache = folder / '.covers'
        target = cache / (key + '.jpg')
        if target.is_file():
            return target.read_bytes()
        import av
        from PIL import ImageOps
        with av.open(str(source)) as video:
            stream = video.streams.video[0]
            stream.codec_context.thread_count = 1
            # Seeking to a keyframe avoids decoding minutes of footage on the dashboard.
            seconds = min(120.0, (float(video.duration or 0) / av.time_base) * .15)
            origin = stream.start_time or 0
            video.seek(origin + int(seconds / stream.time_base), stream=stream, backward=True)
            frame = next(video.decode(stream))
            picture = ImageOps.fit(frame.to_image(), (640, 360))
        output = io.BytesIO()
        picture.save(output, format='JPEG', quality=82)
        data = output.getvalue()
        cache.mkdir(exist_ok=True)
        import uuid
        temporary = cache / (key + '.' + uuid.uuid4().hex + '.tmp')
        temporary.write_bytes(data)
        temporary.replace(target)
        return data
    except (OSError, ValueError, IndexError, StopIteration):
        return None


def cover_html(project):
    data = cover_bytes(project['source'], project['folder'])
    label = html.escape(project['title'], quote=True)
    if data:
        image = f'<img src="data:image/jpeg;base64,{base64.b64encode(data).decode()}" alt="Video cover: {label}">'
    else:
        image = '<div class="cover-placeholder">▷<span>Video preview unavailable</span></div>'
    seconds = project.get('duration')
    badge = ''
    if isinstance(seconds, (int, float)) and seconds > 0:
        minutes, seconds = divmod(int(seconds), 60)
        badge = f'<span class="cover-duration">{minutes}:{seconds:02}</span>'
    return f'<div class="project-cover">{image}{badge}</div>'
