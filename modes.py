"""Mode-specific selection and conservative final highlight limits."""
import re

PROFILES = {
    'Interview': {'lengths': (20, 65), 'coverage': .40,
        'description': 'Exactly one question and its complete answer. Never merges follow-ups or pads to a preferred length; skips exchanges that need missing context.',
        'review': 'INTERVIEW: Require exactly one main subject, an identified subject, a complete question and a complete answer. A new interviewer setup may be a declarative sentence BEFORE a question mark. Reject any new unfinished setup or question. A short complete answer is valid. Do not approve unexplained he/she/they references.'},
    'Podcast': {'lengths': (30, 80), 'coverage': .40,
        'description': 'Complete stories and arguments. Allows more setup and looks for a conclusion or payoff.',
        'review': 'PODCAST: Require one coherent story or argument with setup, development, and payoff. Reject tangents and unresolved promises.'},
    'Sports': {'lengths': (10, 35), 'coverage': .35,
        'description': 'Short action highlights using visual changes, motion, and commentary cues. Boundaries need your review; this is not a play-recognition model.',
        'review': ''},
}
VERSION = 10


def speech_candidates(sentences, minimum, maximum, mode):
    if mode == "Interview":
        from topics import interview_topics
        return interview_topics(sentences, maximum)
    candidates = []
    for i, first in enumerate(sentences):
        for j in range(i, len(sentences)):
            last = sentences[j]
            length = last['end'] - first['start']
            if length > maximum:
                break
            if length < minimum or last['text'].rstrip().endswith('?'):
                continue
            text = ' '.join(s['text'] for s in sentences[i:j+1])
            opening = first['text'].lower()
            score = 1 - abs(length - minimum * 1.3) / maximum
            score -= 4 if re.match(r'^(and|but|so|because|that|this|it|they|he|she)\b', opening) else 0
            if mode == 'Interview':
                score += 5 if '?' in first['text'] and j > i else 0
                # Do not start inside an answer when the question can fit.
                if i and sentences[i-1]['text'].rstrip().endswith('?'):
                    continue
                # A second question means a new exchange; avoid bundling it.
                if any('?' in s['text'] for s in sentences[i+1:j+1]):
                    continue
                score += 2 if re.search(r'\b(because|reason|answer|learned)\b', text.lower()) else 0
            else:
                score += 3 if re.search(r'\b(once|when|story|imagine|first|problem)\b', opening) else 0
                score += 4 if re.search(r'\b(lesson|finally|realized|result|in the end|turned out|therefore)\b', last['text'].lower()) else 0
            candidates.append(dict(first=i, last=j, start=first['start'], end=last['end'], text=text, rank=score))
    # Keep alternative boundaries for local review, but avoid near-identical drafts.
    shortlist = []
    for item in sorted(candidates, key=lambda c: c['rank'], reverse=True):
        if all(intersection(item, old) / min(span(item), span(old)) < .8 for old in shortlist):
            shortlist.append(item)
        if len(shortlist) == 12:
            break
    return shortlist


def span(item):
    from edit_timeline import edited_duration
    return edited_duration(item)


def intersection(a, b):
    from edit_timeline import ranges_for
    return sum(max(0,min(x['end'],y['end'])-max(x['start'],y['start'])) for x in ranges_for(a) for y in ranges_for(b))


def select_highlights(candidates, total, mode, limit=3, diagnostics=None, coverage=None, strict=False):
    """Apply limits AFTER review and boundary adjustment, including rejected drafts."""
    budget = total * (PROFILES[mode]['coverage'] if coverage is None else max(0,min(1,coverage)))
    selected, used = [], 0
    from audience_quality import selection_key,weak_value
    for item in sorted(candidates, key=selection_key, reverse=True):
        length = span(item)
        reason=None
        if item.get('boundary_rejected'):reason='Incomplete exchange boundaries'
        elif strict and not item.get('passed',False):reason='Failed completeness review'
        elif weak_value(item):reason='Local review found neither useful content nor a resolved payoff'
        elif limit is not None and len(selected)>=limit:reason='Clip count limit'
        elif not 0 <= item['start'] < item['end'] <= total:reason='Invalid boundaries'
        elif used+length>budget:reason='Total footage budget'
        if reason:
            if diagnostics is not None:diagnostics.append(dict(start=item['start'],end=item['end'],reason=reason))
            continue
        if any(intersection(item, old) > 0 for old in selected):
            if diagnostics is not None:diagnostics.append(dict(start=item['start'],end=item['end'],reason='Overlaps another clip'))
            continue
        # Replays with substantially identical commentary are likely duplicate moments.
        words = set(re.findall(r'\w+', item['text'].lower()))
        if item['text'] != 'No spoken commentary in this segment.' and words and any(len(words & set(re.findall(r'\w+', old['text'].lower()))) / max(1, len(words | set(re.findall(r'\w+', old['text'].lower())))) > .8 for old in selected):
            if diagnostics is not None:diagnostics.append(dict(start=item['start'],end=item['end'],reason='Similar commentary / possible replay'))
            continue
        selected.append(item)
        used += length
    return selected


def scan_visuals(path):
    """Sample twice per second: histogram scene changes and coarse image motion.

    These are editing signals, not evidence of a snap, whistle, or completed play.
    """
    import av
    import numpy as np
    samples, previous, previous_hist = [], None, None
    next_time = 0
    with av.open(str(path)) as media:
        stream = media.streams.video[0]
        for frame in media.decode(stream):
            if frame.time is None or frame.time < next_time:
                continue
            timestamp = float(frame.time)
            next_time = timestamp + .48
            pixels = frame.reformat(width=96, height=54, format='gray').to_ndarray().astype(float)
            hist = np.histogram(pixels, bins=16, range=(0, 256))[0].astype(float)
            hist /= hist.sum()
            motion = float(np.abs(pixels-previous).mean()/255) if previous is not None else 0
            change = float(np.abs(hist-previous_hist).sum()/2) if previous_hist is not None else 0
            samples.append({'time': timestamp, 'motion': motion, 'cut': change > .32})
            previous, previous_hist = pixels, hist
    return samples


def sports_candidates(sentences, samples, total, minimum, maximum):
    if not samples:
        return []
    import numpy as np
    # Favor low-motion runs and shot transitions over speech punctuation.
    threshold = float(np.quantile([s['motion'] for s in samples], .3))
    boundaries = [0.0]
    for i, sample in enumerate(samples[1:-1], 1):
        quiet = all(x['motion'] <= threshold for x in samples[i-1:i+2])
        if (sample['cut'] or quiet) and sample['time'] - boundaries[-1] >= 2:
            boundaries.append(sample['time'])
    boundaries.append(total)
    candidates = []
    for start_index, start in enumerate(boundaries):
        for end in boundaries[start_index+1:]:
            length = end-start
            if length > maximum:
                break
            if length < minimum:
                continue
            inside = [s for s in samples if start <= s['time'] <= end]
            if not inside:
                continue
            indices = [i for i,s in enumerate(sentences) if s['end'] > start and s['start'] < end]
            text = ' '.join(sentences[i]['text'] for i in indices)
            motion = sum(s['motion'] for s in inside)/len(inside)
            if motion < .015:
                continue
            cue = bool(re.search(r'\b(touchdown|intercept|fumble|scores?|goal|sack|save|home run|basket|three pointer)\b',text.lower()))
            # Prefer activity with recovery space; never equate motion with play completion.
            score = motion*15 + (3 if cue else 0) - abs(length-20)/maximum
            candidates.append(dict(first=indices[0] if indices else -1,last=indices[-1] if indices else -1,
                start=start,end=end,text=text or 'No spoken commentary in this segment.',rank=score,
                title='Action highlight',passed=False,
                reason='Selected using visual boundaries and motion' + (' with a commentary highlight cue.' if cue else '.'),
                concern='Visual signals do not confirm a complete play. Watch the lead-in and outcome before exporting.'))
    return candidates


def refine_sports_boundaries(candidates, samples, sentences, total, lead=2.0, tail=2.0):
    """Add context and seek sustained settling after activity, without claiming play recognition.

    A camera cut alone is not an ending. If activity remains high, prefer a later
    low-motion run within eight seconds. Selection budgets are applied afterward.
    """
    if not samples:
        return []
    import numpy as np
    threshold = min(.055, max(.012, float(np.quantile([s['motion'] for s in samples], .40))))
    settled = []
    for i in range(2, len(samples)):
        window = samples[i-2:i+1]
        if window[-1]['time']-window[0]['time'] >= .8 and all(s['motion'] <= threshold and not s['cut'] for s in window):
            settled.append(window[-1]['time'])
    refined = []
    for candidate in candidates:
        item = dict(candidate)
        original_end = item['end']
        start = max(0.0, item['start']-lead)
        end = min(total, original_end+tail)
        later = next((t for t in settled if original_end <= t <= min(total, original_end+8)), None)
        notes = [f'Added up to {lead:g}s of lead-in and {tail:g}s of aftermath.']
        if later is not None:
            end = min(total, max(end, later+tail))
            notes.append('Ending includes a sustained lower-motion interval.')
        else:
            notes.append('No sustained lower-motion ending found nearby; check the outcome carefully.')
        # Keep the last intersecting commentary sentence if it ends nearby.
        for sentence in sentences:
            if sentence['start'] < end < sentence['end'] <= end+3:
                end = min(total, sentence['end']+.2)
                break
        item.update(start=start, end=end, boundary_notes=notes)
        relevant = [i for i,s in enumerate(sentences) if s['end']>start and s['start']<end]
        if relevant:
            item.update(first=relevant[0], last=relevant[-1],
                        text=' '.join(sentences[i]['text'] for i in relevant))
        item['rank'] += .5 if later is not None else -.5
        refined.append(item)
    return refined
