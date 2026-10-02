"""Source ranges and caption timing share one local, non-destructive timeline."""
import math


def validate_ranges(ranges, total):
    if not isinstance(ranges, list) or not ranges or len(ranges) > 24:
        raise ValueError('An edit needs 1–24 source ranges.')
    result = []
    previous = -1
    for item in ranges:
        start, end = item.get('start'), item.get('end')
        if (type(start) not in (int, float) or type(end) not in (int, float)
                or not math.isfinite(start) or not math.isfinite(end)
                or not 0 <= start < end <= total + .001 or start < previous):
            raise ValueError('Edit ranges must be finite, ordered and inside the source.')
        result.append(dict(start=float(start), end=float(end)))
        previous = end
    return result


def timeline_duration(ranges):
    return sum(r['end'] - r['start'] for r in ranges)


def remap_words(words, ranges):
    """Copy words onto output time, including corrected captions without rewriting speech."""
    offset = 0.
    result = []
    for segment_id, r in enumerate(ranges):
        for w in words:
            if w['end'] > r['start'] and w['start'] < r['end']:
                result.append(dict(w, source_start=w['start'], source_end=w['end'], segment_id=segment_id,
                    start=offset + max(w['start'], r['start']) - r['start'],
                    end=offset + min(w['end'], r['end']) - r['start']))
        offset += r['end'] - r['start']
    return result


def ranges_for(candidate):
    plan = candidate.get('edit_plan', {})
    return plan.get('ranges') or [dict(start=candidate['start'], end=candidate['end'])]


def edited_duration(candidate):
    return timeline_duration(ranges_for(candidate))


def speech_text(words, ranges):
    return ' '.join(w['text'] for w in remap_words(words, ranges))


def concat_filter(ranges, audio=True):
    """Trim both streams at the same boundaries and reset each segment's timestamps."""
    n = len(ranges)
    labels = ''.join(f'[vs{i}]' for i in range(n))
    filters = [f'[0:v]split={n}{labels}'] if n > 1 else ['[0:v]null[vs0]']
    if audio:
        labels = ''.join(f'[as{i}]' for i in range(n))
        filters.append(f'[0:a]asplit={n}{labels}' if n > 1 else '[0:a]anull[as0]')
    for i, r in enumerate(ranges):
        filters.append(f"[vs{i}]trim=start={r['start']:.9f}:end={r['end']:.9f},setpts=PTS-STARTPTS[v{i}]")
        if audio:
            filters.append(f"[as{i}]atrim=start={r['start']:.9f}:end={r['end']:.9f},asetpts=PTS-STARTPTS[a{i}]")
    inputs = ''.join(f'[v{i}]' + (f'[a{i}]' if audio else '') for i in range(n))
    filters.append(inputs + f'concat=n={n}:v=1:a={int(audio)}[cutv]' + ('[cuta]' if audio else ''))
    return ';'.join(filters)
