"""Controlled local comparisons of a saved cut before and after opening/ending AI."""
import hashlib
import json
import re
import time
from pathlib import Path

from edit_timeline import remap_words, timeline_duration, validate_ranges
from project_store import read, write

VERSION = 'before-after-2'
SUPPORTED = ('before-after-1', VERSION)
CHOICES = ('Not rated', 'After is better', 'Before is better', 'About the same', 'Neither is good')


def directory(root):
    return Path(root) / 'data' / 'before-after'


def signature(path):
    path = Path(path).resolve(); stat = path.stat()
    return dict(path=str(path), size=stat.st_size, mtime_ns=stat.st_mtime_ns)


def current(asset):
    try: return signature(asset['path']) == asset
    except (OSError, KeyError, TypeError): return False


def identity(spec):
    from ending_review import VERSION as ending_version, lessons
    from opening_hooks import VERSION as opening_version, style_lessons
    from social_copy import VERSION as posting_version
    source = signature(spec['project']['source']); transcript = signature(spec['transcript'])
    body = [VERSION, ending_version, opening_version, posting_version, spec, source, transcript,
            lessons(spec['root']), style_lessons(spec['root'])]
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:24]


def snapshot(project, transcript, words, ranges, video, captions, opening, posting):
    import av
    from final_package import sentences, tokens
    from boundary_editor import check_boundaries
    from interview_integrity import speech_question_count
    ranges = validate_ranges(ranges, project['duration'])
    heard = remap_words(words, ranges)
    text = ' '.join(w['text'] for w in heard)
    with av.open(str(video)) as media:
        stream = media.streams.video[0]
        length = float(media.duration / av.time_base)
        width, height = stream.width, stream.height
    expected = timeline_duration(ranges)
    if abs(length - expected) > .15:
        raise ValueError('The exported duration does not match its source ranges.')
    caption_source = Path(captions).read_text().strip()
    cues=[]
    for block in re.split(r'\n\s*\n',caption_source) if caption_source else []:
        lines=block.splitlines()
        if len(lines)<3 or not lines[0].strip().isdigit() or '-->' not in lines[1]:
            raise ValueError('The comparison has an invalid subtitle cue.')
        cues.append(lines)
    caption_text = ' '.join(' '.join(cue[2:]) for cue in cues)
    if tokens(caption_text) != tokens(text):
        raise ValueError('The subtitles do not match this comparison’s final speech.')
    times = [int(h)*3600+int(m)*60+int(s)+int(ms)/1000
             for h,m,s,ms in re.findall(r'(\d+):(\d+):(\d+),(\d+)', '\n'.join(cue[1] for cue in cues))]
    if any(t > length + .005 for t in times):
        raise ValueError('A subtitle extends past the comparison video.')
    groups = sentences(heard)
    questions = speech_question_count(groups,heard)
    warnings = []
    for r in ranges:
        warnings += check_boundaries(words, transcript['sentences'], r['start'], r['end'], project['duration'])['warnings']
    return dict(source=signature(project['source']), video=signature(video), captions=signature(captions),
                ranges=ranges, duration=length, width=width, height=height, final_transcript=text,
                first_sentence=groups[0]['text'] if groups else '', last_sentence=groups[-1]['text'] if groups else '',
                opening_text=opening, posting=posting, detected_questions=questions,
                boundary_warnings=list(dict.fromkeys(warnings)), subtitles_match=True)


def valid_report(report):
    if not isinstance(report, dict) or report.get('version') not in SUPPORTED: return False
    try:
        if not current(report['source']) or not current(report['transcript']): return False
        before, after = report['before'], report['after']
        for side in (before, after):
            if side['source'] != report['source'] or not all(current(side[k]) for k in ('video', 'captions')): return False
        # A comparison must retain the same moment and only trim its suffix.
        from ending_review import prefix_ranges
        expected = prefix_ranges(before['ranges'], after['ranges'][-1]['end'])
        if after['ranges'] != expected: return False
        from final_package import tokens
        a, b = tokens(before['final_transcript']), tokens(after['final_transcript'])
        return b == a[:len(b)] and (bool(b) or not a and after['ranges']==before['ranges'])
    except (KeyError, IndexError, TypeError, ValueError): return False


def reports(root):
    result = []
    for path in directory(root).glob('*.json'):
        item = read(path, None)
        required={'id','name','source','transcript','source_title','mode','editor','baseline_note','before','after','stages','observations'}
        side_keys={'source','video','captions','duration','width','height','ranges','final_transcript','first_sentence','last_sentence','opening_text','posting','detected_questions','boundary_warnings'}
        if (isinstance(item, dict) and item.get('version') in SUPPORTED and required<=item.keys()
                and all(isinstance(item.get(k),dict) and side_keys<=item[k].keys() for k in ('before','after'))):
            result.append(dict(item, path=str(path), available=valid_report(item)))
    return sorted(result, key=lambda r:r.get('created_at', 0), reverse=True)


def save_rating(root, report_id, choice, notes):
    if not re.fullmatch(r'[a-f0-9]{24}', report_id) or choice not in CHOICES:
        raise ValueError('Choose a saved comparison and a valid rating.')
    if not valid_report(read(directory(root)/(report_id+'.json'), None)):
        raise ValueError('This comparison’s source or assets changed. Create a fresh comparison before rating it.')
    saved = dict(choice=choice, notes=str(notes)[:4000], updated_at=time.time())
    write(directory(root)/'ratings'/(report_id+'.json'), saved)
    return saved


def build(spec, progress=lambda p,label:None):
    """Render a controlled baseline and review a copy. Never apply project edits."""
    from engine import export_clip
    from ending_review import context as ending_context, get_ending, cached as cached_ending
    from opening_hooks import context as opening_context, get_hook, cached_hook
    from social_copy import get_copy, identity as copy_identity, posting_error
    from final_package import get_package
    from local_editor import LABELS
    root = Path(spec['root']); project = spec['project']; mode = spec['mode']
    source = Path(project['source']); tp = Path(spec['transcript'])
    key = identity(spec); output = directory(root)/(key+'.json')
    saved = read(output, None)
    if valid_report(saved): progress(1, 'Reusing the saved comparison'); return saved
    initial_source, initial_transcript = signature(source), signature(tp)
    transcript = read(tp, {})
    words = spec.get('caption_words') or transcript['words']
    ranges = validate_ranges(spec['ranges'], project['duration'])
    # This rendering profile is shared; opening text and source ending are the
    # only video variables. No automatic camera plan or extra discovery pass.
    style = dict(layout=spec.get('layout','Portrait · full picture'), burn=True,
                 position=.5, second=.75, pacing='Off', conversation='Off', semantic_emphasis=False,
                 packaging_version=1, title=spec.get('opening_text',''))
    cache = directory(root)/'work'/key; cache.mkdir(parents=True, exist_ok=True)
    stages = []
    def stage(name, start, reused, status='passed', error=''):
        stages.append(dict(name=name, seconds=round(time.monotonic()-start,3), cached=reused, status=status, error=error))
    def render(which, cuts, options, fraction):
        progress(fraction, 'Rendering '+which)
        manifest = cache/(which+'-render.json'); stored = read(manifest, None); started=time.monotonic()
        reused = isinstance(stored, list) and len(stored)==2 and all(Path(p).is_file() for p in stored)
        if reused: video, captions = map(Path, stored)
        else:
            video, captions = export_clip(source, cuts[0]['start'], cuts[-1]['end'], words,
                                          style['layout']!='Original', presentation=options, ranges=cuts)
            write(manifest, [str(video), str(captions)])
        stage(which+' render', started, reused)
        return video, captions
    before_video, before_captions = render('Before', ranges, style, .05)
    before = snapshot(project, transcript, words, ranges, before_video, before_captions, style['title'], spec.get('posting',{}))
    after_ranges = ranges; after_opening = style['title']; after_posting = before['posting']
    ending = opening = None
    settings = dict(mode=mode, editor_model=spec.get('editor_model','qwen3-4b'))
    if mode!='Sports':
        def package_for(cuts):
            candidate=dict(text=' '.join(w['text'] for w in remap_words(words,cuts)),passed=False)
            return get_package(cache,source,candidate,words,cuts,mode)
        def review_opening(label,package,cuts):
            nonlocal opening,after_opening
            started=time.monotonic();reused=False
            try:
                info=opening_context(root,package,remap_words(words,cuts),settings)
                reused=cached_hook(cache,package,info) is not None
                opening=get_hook(cache,package,info);after_opening=opening['opening_text']
                stage(label,started,reused)
            except (ValueError,RuntimeError) as error:
                if cuts!=ranges:opening=None;after_opening=''
                stage(label,started,reused,'failed',str(error).splitlines()[-1][:400])
        package=package_for(ranges)
        progress(.2,'Reviewing opening text')
        review_opening('Opening text',package,ranges)
        progress(.4, 'Reviewing the ending of this same moment'); started=time.monotonic(); reused=False
        try:
            data = ending_context(root, transcript, ranges, project['duration'], settings, after_opening, str(initial_source))
            reused = cached_ending(cache, data) is not None
            ending = get_ending(cache, data)
            after_ranges = ending['ranges']; stage('Ending review',started,reused)
        except (ValueError, RuntimeError) as error: stage('Ending review',started,reused,'failed',str(error).splitlines()[-1][:400])
        if after_ranges!=ranges:
            package=package_for(after_ranges)
            progress(.55,'Checking opening text against the final cut')
            review_opening('Final-cut opening text',package,after_ranges)
        progress(.65, 'Checking titles and description'); started=time.monotonic(); reused=False
        try:
            copy_key,_ = copy_identity(package,settings)
            reused = (cache/'ai-social-copy-v520'/(copy_key+'.json')).exists()
            after_posting = get_copy(cache,package,settings); stage('Posting text',started,reused)
        except (ValueError,RuntimeError) as error:
            # A title for the old, longer speech is not automatically safe for
            # the shorter cut. Show the failure and leave new copy empty.
            after_posting = {}; stage('Posting text',started,reused,'failed',posting_error(error))
    else:
        stages.append(dict(name='AI review',seconds=0,cached=False,status='skipped',error='Sports boundaries and text need manual review.'))
    if after_ranges==ranges and after_opening==style['title']:
        after_video,after_captions=before_video,before_captions
        stages.append(dict(name='After render',seconds=0,cached=True,status='passed',error='Unchanged cut and opening reuse the baseline render.'))
    else: after_video,after_captions=render('After',after_ranges,dict(style,title=after_opening),.85)
    after = snapshot(project,transcript,words,after_ranges,after_video,after_captions,after_opening,after_posting)
    if signature(source)!=initial_source or signature(tp)!=initial_transcript:
        raise ValueError('The source or transcript changed during comparison. No report was saved.')
    report=dict(version=VERSION,id=key,name=spec['name'],created_at=time.time(),source=initial_source,transcript=initial_transcript,
                source_title=project['title'],mode=mode,editor=LABELS[settings['editor_model']],
                baseline_note='Reconstructed from the saved cut and opening, using the same rendering profile as After. Existing discovery is held fixed.',
                before=before,after=after,stages=stages,ending_review=ending,opening_review=opening,
                observations=spec.get('observations',[]))
    if not valid_report(report): raise ValueError('The comparison does not preserve the same source moment.')
    write(output,report); progress(1,'Comparison ready'); return report
