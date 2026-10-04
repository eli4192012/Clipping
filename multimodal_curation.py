"""Evidence-weighted local curation; source integrity always outranks interest."""
import hashlib
import json
import math
import time
from pathlib import Path
from project_store import read,write
from edit_timeline import ranges_for,validate_ranges,timeline_duration,remap_words
from sound_analysis import signature

VERSION='multimodal-curation-3'
WEIGHTS={'Interview':dict(speech=.75,visuals=.1,sound=.15),
         'Podcast':dict(speech=.65,visuals=.2,sound=.15),
         'Sports':dict(speech=.25,visuals=.45,sound=.3),
         'Music':dict(speech=.2,visuals=.35,sound=.45),
         'Gaming':dict(speech=.4,visuals=.4,sound=.2)}


def cache_tag(settings):
    if not settings.get('multimodal_curation'):return ''
    from sound_analysis import installed
    return '-'+VERSION+'-n'+str(settings.get('curation_windows',3))+f'-s{int(installed())}v{int((vision_model()/".ready").exists())}'


def vision_model():
    from upgrades import VISION4
    return VISION4


def fingerprint(candidate):
    return hashlib.sha256(json.dumps([ranges_for(candidate),candidate.get('text','')],sort_keys=True).encode()).hexdigest()[:24]


def genre(settings):
    if settings['mode'] in ('Interview','Sports'):return settings['mode']
    return next((c for c in settings.get('categories',[]) if c in ('Music','Gaming')),'Podcast')


def frame_times(ranges):
    """Sample the retained timeline, including discontinuous edits."""
    length=timeline_duration(ranges);times=[]
    for fraction in (.1,.5,.9):
        target=length*fraction
        for r in ranges:
            span=r['end']-r['start']
            if target<span:
                times.append(round(min(r['end']-.001,r['start']+target),6));break
            target-=span
    return list(dict.fromkeys(times))


def sample_frames(source,ranges,folder):
    import av
    frames=[];folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    with av.open(str(source)) as media:
        for timestamp in frame_times(ranges):
            output=folder/(str(timestamp)+'.jpg');actual=None
            media.seek(int(timestamp*av.time_base))
            for frame in media.decode(video=0):
                if frame.time is None or frame.time<timestamp:continue
                actual=float(frame.time)
                if not any(r['start']<=actual<r['end'] for r in ranges):break
                picture=frame.to_image();picture.thumbnail((448,448));picture.save(output)
                frames.append(dict(time=round(actual,6),path=str(output)));break
    return frames


def visual_scan(project,progress):
    from modes import scan_visuals
    source=signature(project['source']);key=hashlib.sha256(json.dumps([source,'motion-v1'],sort_keys=True).encode()).hexdigest()[:24]
    path=Path(project['folder'])/'multimodal-curation'/('motion-'+key+'.json');saved=read(path,None)
    if isinstance(saved,dict) and saved.get('source')==source:return saved['samples']
    progress(0,'Scanning motion and camera changes')
    samples=scan_visuals(project['source'])
    if signature(project['source'])!=source:raise ValueError('The source changed during visual scanning.')
    write(path,dict(source=source,samples=samples));return samples


def fuse(candidate,mode,sound,samples,observations,settings):
    """Conservative supporting priority, not a retention or emotion prediction."""
    from audience_quality import validated_review
    review=validated_review(candidate.get('audience_review'),candidate.get('text',''))
    speech=(sum(review[k]['rating']*w for k,w in [('opening',1),('clarity',2),('value',2),('payoff',3)])/16) if review else None
    measured=[s for s in samples if any(r['start']<=s['time']<r['end'] for r in ranges_for(candidate))]
    observed=[f for f in observations if f.get('status')=='Observed']
    kind=genre(settings);weights=WEIGHTS[kind]
    # A speech format can have a worthwhile quiet answer. Energy is not a verdict.
    sound_score=None
    if sound.get('available'):
        reaction=sound['reaction_fraction'];speech_fraction=sound['speech_fraction'];quiet=sound.get('quiet_fraction') or 0
        sound_score=(.5+.3*sound['music_fraction']+.1*reaction if kind=='Music' else
                     .5+.3*reaction if kind in ('Sports','Gaming') else
                     .5+.15*speech_fraction+.1*reaction-.15*quiet)
    visual_score=None
    if observed:
        talking=sum(f['shot'] in ('talking_heads','close_up') for f in observed)/len(observed)
        known_action=[f for f in observed if f['action_visible'] is not None]
        action=sum(f['action_visible'] is True for f in known_action)/len(known_action) if known_action else None
        reaction=sum(f['reaction_visible'] is True for f in observed)/len(observed)
        if kind not in ('Sports','Gaming','Music') or action is not None:
            visual_score=.5+.3*(action if kind in ('Sports','Gaming','Music') else talking)+.1*reaction
    values=dict(speech=speech,visuals=visual_score,sound=sound_score)
    known={k:v for k,v in values.items() if v is not None};weight=sum(weights[k] for k in known)
    combined=sum(weights[k]*v for k,v in known.items())/weight if weight else None
    # Only supporting signals can nudge rank. The original speech assessment,
    # pass state and deterministic vetoes remain authoritative.
    support={k:v for k,v in known.items() if k!='speech'}
    delta=sum(weights[k]*(v-.5)*4 for k,v in support.items())
    quality=candidate.get('audience_quality',{}).get('score',0)
    return dict(genre=kind,weights=weights,signals=values,combined_estimate=round(combined,3) if combined is not None else None,
        available_weight=round(weight,3),priority_adjustment=round(delta,3),ranking_score=quality+delta,
        speech_basis='Quoted editorial review' if review else 'No grounded speech rating; existing integrity checks still apply',
        sound=sound,visual=dict(samples=observations,motion_samples=len(measured),
            average_motion=round(sum(s['motion'] for s in measured)/len(measured),4) if measured else None,
            camera_changes=sum(bool(s.get('cut')) for s in measured)),
        limitations=['Sound labels and sampled frames are uncertain observations.',
            'Three sampled frames cannot establish a completed sports play.',
            'No emotion model, audience prediction or analytics training is used.'])


def valid_priority(candidate):
    data=candidate.get('multimodal_curation',{})
    value=data.get('ranking_score')
    if data.get('source'):
        try:
            if signature(data['source']['path'])!=data['source']:return False
        except (OSError,KeyError):return False
    return (data.get('version')==VERSION and data.get('fingerprint')==fingerprint(candidate)
            and type(value) in (int,float) and math.isfinite(value))


def curate(project,transcript,candidates,settings,progress=lambda p,label:None):
    """Review copies before coverage/overlap selection. Never apply boundaries."""
    import copy
    from audience_quality import selection_key
    from sound_analysis import scan,summarize,VERSION as sound_version,WEIGHTS_SHA
    from upgrades import worker
    VISION=vision_model()
    source=signature(project['source']);folder=Path(project['folder'])/'multimodal-curation'
    limit=max(1,min(6,int(settings.get('curation_windows',3))))
    model=dict(path=str(VISION),config=signature(VISION/'config.json') if (VISION/'config.json').exists() else None)
    base=[{k:v for k,v in c.items() if k!='multimodal_curation'} for c in candidates]
    key=hashlib.sha256(json.dumps([VERSION,source,transcript,base,limit,genre(settings),settings.get('categories',[]),model,sound_version,WEIGHTS_SHA],sort_keys=True).encode()).hexdigest()[:24]
    path=folder/('review-'+key+'.json');saved=read(path,None)
    cached_frames=([f for c in saved.get('candidates',[]) for f in c.get('multimodal_curation',{}).get('visual',{}).get('samples',[])]
                   if isinstance(saved,dict) else [])
    if (isinstance(saved,dict) and saved.get('version')==VERSION and saved.get('source')==source and saved.get('complete')
            and all(Path(f['path']).is_file() for f in cached_frames)):
        progress(1,'Reusing the multimodal review');return saved['candidates'],saved
    begun=time.monotonic();result=copy.deepcopy(base);failures=[]
    for c in result:
        ranges=validate_ranges(ranges_for(c),project['duration'])
        if settings['mode']=='Interview':
            from final_package import sentences
            from interview_integrity import speech_question_count
            words=remap_words(transcript.get('words',[]),ranges)
            if speech_question_count(sentences(words),words)>1:
                c.update(boundary_rejected=True,passed=False,concern='Multimodal review detected multiple interview questions.')
    progress(.02,'Reading source-timed sound evidence')
    try:audio=scan(project,lambda p,label:progress(.02+.38*p,label))
    except (ValueError,RuntimeError,TimeoutError,OSError) as error:
        audio=dict(status='Unavailable',frames=[],levels=[]);failures.append('Sound: '+str(error).splitlines()[-1][:220])
    progress(.42,'Scanning motion and camera changes')
    try:samples=visual_scan(project,lambda p,label:progress(.42,label))
    except (ValueError,RuntimeError,OSError) as error:samples=[];failures.append('Visual scan: '+str(error)[:180])
    eligible=[c for c in sorted(result,key=selection_key,reverse=True) if not c.get('boundary_rejected')][:limit]
    for c in result:c['multimodal_curation']=fuse(c,settings['mode'],summarize(audio,ranges_for(c)),samples,[],settings)
    # Review high-value existing moments first. Visual results are cached per cut.
    for i,c in enumerate(eligible):
        progress(.5+.45*i/max(1,len(eligible)),f'Visually reviewing moment {i+1} of {len(eligible)}')
        fp=fingerprint(c);vkey=hashlib.sha256(json.dumps([VERSION,source,fp,model],sort_keys=True).encode()).hexdigest()[:24]
        vpath=folder/('visual-'+vkey+'.json');observations=read(vpath,None)
        try:
            if not isinstance(observations,list) or any(not Path(f['path']).is_file() or f.get('status')!='Observed' for f in observations):
                if not (VISION/'.ready').exists():raise RuntimeError('The local vision model is not installed.')
                frames=sample_frames(project['source'],ranges_for(c),folder/'frames'/vkey)
                if not frames:raise ValueError('No retained video frames could be sampled.')
                observations=worker('curation_visual',dict(frames=frames,model_path=str(VISION)),timeout=300,
                    progress=lambda p,label:progress(.5+.45*(i+p)/max(1,len(eligible)),label))
                write(vpath,observations)
            if any(f.get('status')!='Observed' for f in observations):failures.append('Some visual samples could not be interpreted.')
        except (ValueError,RuntimeError,TimeoutError,OSError) as error:
            observations=[];failures.append('Visual moment '+str(i+1)+': '+str(error).splitlines()[-1][:220])
        c['multimodal_curation']=fuse(c,settings['mode'],c['multimodal_curation']['sound'],samples,observations,settings)
    for c in result:
        c['multimodal_curation'].update(version=VERSION,fingerprint=fingerprint(c),source=source,
            ranges=validate_ranges(ranges_for(c),project['duration']),visual_model='Qwen3-VL · 4B · local sampled frames',
            reviewed_visuals=c in eligible,failures=list(dict.fromkeys(failures)))
    if signature(project['source'])!=source:raise ValueError('The source changed during curation. No combined report was saved.')
    report=dict(version=VERSION,source=source,candidates=result,visual_moments=len(eligible),total_moments=len(result),
        failures=list(dict.fromkeys(failures)),seconds=round(time.monotonic()-begun,3),complete=not failures,
        sound_model=audio.get('model',audio.get('status')),emotion='Not used',analytics='Not used')
    write(path,report);progress(1,'Multimodal review ready');return result,report
