"""UI-independent analysis and honest stage progress."""
import json
import time
from pathlib import Path
from engine import transcribe
from analysis_settings import AnalysisSettings
from modes import VERSION,speech_candidates,sports_candidates,scan_visuals,refine_sports_boundaries,select_highlights
from vision_sports import visual_candidates
from upgrades import signature,transcript_file,worker,scene_times,apply_scene_context,VISION4
CURATION_API=2


def analysis_path(project, settings):
    from content_categories import cache_tag
    mode=AnalysisSettings.read(settings).mode
    stat=Path(project['source']).stat()
    source_tag=f'{stat.st_size}-{stat.st_mtime_ns}'
    variant='vision'+str(settings['windows']) if mode=='Sports' and settings['vision'] else 'ai' if settings['semantic'] else 'basic'
    from shorts_context import SELECTION_TAG
    editorial=SELECTION_TAG if settings.get('shorts_editor') and mode!='Sports' else ''
    from local_editor import cache_tag as editor_tag
    from multimodal_curation import cache_tag as curation_tag
    return Path(project['folder'])/f"clips-v{VERSION}-{mode}-{settings['minimum']}-{settings['maximum']}-all-{variant}-c{settings.get('coverage',1.0 if mode!='Sports' else .35)}-v514{editorial}-{signature(settings)}-{source_tag}{cache_tag(settings)}{editor_tag(settings)}{curation_tag(settings)}.json"


def timing_key(settings):
    """Separate measured estimates when the actual editorial workload changes."""
    from local_editor import cache_tag as editor_tag
    from multimodal_curation import cache_tag as curation_tag
    mode=settings['mode']
    from shorts_context import SELECTION_TAG
    return mode+str(settings['vision'])+str(settings['semantic'])+str(settings['windows'])+signature(settings)+(SELECTION_TAG if settings.get('shorts_editor') and mode!='Sports' else '')+editor_tag(settings)+curation_tag(settings)


def estimate_seconds(project, settings):
    folder=Path(project['folder'])
    if analysis_path(project,settings).exists():return 1
    history=folder/'ui-timing.json'
    key=timing_key(settings)
    if history.exists():
        from project_store import read
        import math
        history_data=read(history,{})
        measured=history_data.get(key) if isinstance(history_data,dict) else None
        if isinstance(measured,(int,float)) and math.isfinite(measured) and measured>0:return measured
    transcription=0 if transcript_file(folder,settings).exists() else project['duration']*.5+15
    review=settings['windows']*240 if settings['mode']=='Sports' and settings['vision'] else 10
    if settings['semantic'] and settings['mode']!='Sports':
        from project_store import read
        transcript=read(transcript_file(folder,settings),{})
        sentences=transcript.get('sentences',[])
        if settings['mode']=='Interview' and sentences:
            from topics import interview_topics
            if settings.get('shorts_editor'):
                from topic_cache import editorial_interview_sources
                count=len(editorial_interview_sources(sentences,settings['maximum']))
            else:count=sum(not c.get('context_uncertain') for c in interview_topics(sentences,settings['maximum']))
            proposal_seconds=0
        else:
            windows=max(1,(max(1,len(sentences))-24+47)//48) if sentences else max(1,round(project['duration']/240))
            count=windows*6
            proposal_seconds=windows*(45 if settings.get('shorts_editor') or settings.get('quality')=='Higher quality' else 20)
        review=proposal_seconds+count*(60 if settings.get('shorts_editor') else (25 if settings.get('quality')=='Higher quality' else 12))
    extra=project['duration']*.05+settings.get('curation_windows',3)*45 if settings.get('multimodal_curation') else 0
    return max(15,transcription+review)+(120 if settings.get('alignment') or settings.get('speakers') else 0)+extra


def get_transcript(project,settings,progress):
    folder=Path(project['folder']);source=Path(project['source'])
    from project_store import read,write
    def cached(options):
        canonical=transcript_file(folder,options)
        paths=[canonical]+[folder/('transcript-'+signature(dict(options,scenes=flag))+'.json') for flag in (False,True)]
        for path in dict.fromkeys(paths):
            result=read(path,None)
            if isinstance(result,dict) and {'words','sentences','language'}<=result.keys():
                if path!=canonical:write(canonical,result)
                return result
        return None
    transcript_path=transcript_file(folder,settings)
    progress(.01,'Preparing your video')
    transcript=cached(settings)
    if transcript is not None:return transcript
    raw_options=dict(settings,alignment=False,speakers=False,scenes=False)
    transcript=cached(raw_options)
    if transcript is None:
        import av
        with av.open(str(source)) as media:has_audio=bool(media.streams.audio)
        progress(.05,'Transcribing speech locally')
        transcript=(worker('transcription',{'source':str(source)}) if settings.get('quality')=='Higher quality' else transcribe(source,lambda p:progress(.05+.4*p,'Transcribing speech'))) if has_audio else {'language':'none','words':[],'sentences':[]}
        write(transcript_file(folder,raw_options),transcript)
    else:progress(.45,'Reusing saved speech transcription')
    if transcript.get('language')!='none' and (settings.get('speakers') or settings.get('alignment')):
        progress(.48,'Aligning words and identifying speakers')
        transcript=worker('speech_details',dict(source=str(source),transcript=transcript,speakers=settings.get('speakers'),alignment=settings.get('alignment')))
    write(transcript_path,transcript)
    return transcript


def analyze(project,settings,progress):
    begun=time.monotonic();folder=Path(project['folder']);source=Path(project['source'])
    saved=analysis_path(project,settings)
    if saved.exists():
        from project_store import save_run
        save_run(project,settings,saved)
        progress(1,'Reused completed analysis')
        return str(saved)
    transcript=get_transcript(project,settings,progress)
    progress(.56,'Finding complete moments')
    mode=settings['mode'];minimum=settings['minimum'];maximum=settings['maximum'];total=project['duration']
    diagnostics={}
    from project_store import read,write
    import hashlib
    selection_inputs=dict(settings)
    for key in ('coverage','min_clips','portrait','auto_mode','video_type','category_selection','multimodal_curation','curation_windows'):selection_inputs.pop(key,None)
    from shorts_context import SELECTION_TAG
    review_version='reviewed-v514'+(SELECTION_TAG if settings.get('shorts_editor') and mode!='Sports' else '')
    cache_key=hashlib.sha256(json.dumps([str(source.resolve()),source.stat().st_size,source.stat().st_mtime_ns,transcript,selection_inputs,review_version],sort_keys=True).encode()).hexdigest()
    reviewed_path=folder/('reviewed-'+cache_key+'.json')
    prior=read(reviewed_path,None)
    if isinstance(prior,dict) and isinstance(prior.get('candidates'),list):
        candidates=prior['candidates'];diagnostics=prior.get('diagnostics',{})
        progress(.93,'Reusing reviewed moments; applying your selection settings')
    else:
        if mode=='Sports' and settings['vision']:
            progress(.57,'Scanning action across the video')
            visual=folder/'visual-v3.json'
            samples=json.loads(visual.read_text()) if visual.exists() else scan_visuals(source)
            visual.write_text(json.dumps(samples))
            candidates=visual_candidates(source,transcript['sentences'],total,folder,limit=settings['windows'],minimum=minimum,maximum=maximum,
                progress=lambda p,label:progress(.6+.3*p,label), model_path=VISION4 if settings.get('quality')=='Higher quality' else None,words=transcript['words'],samples=samples,diagnostics=diagnostics)
        elif mode=='Sports':
            visual=folder/'visual-v3.json'
            progress(.6,'Scanning visual transitions')
            samples=json.loads(visual.read_text()) if visual.exists() else scan_visuals(source)
            visual.write_text(json.dumps(samples))
            candidates=refine_sports_boundaries(sports_candidates(transcript['sentences'],samples,total,minimum,maximum),samples,transcript['sentences'],total)
        elif settings['semantic']:
            progress(.62,'Grouping topics and checking complete conversations locally')
            candidates=worker('topics',dict(sentences=transcript['sentences'],words=transcript['words'] if settings.get('shorts_editor') else [],shorts_editor=settings.get('shorts_editor',False),minimum=minimum,maximum=maximum,mode=mode,quality=settings.get('quality','Balanced'),editor_model=settings.get('editor_model'),cache_dir=str(folder/'topic-reviews-v37'),categories=settings.get('categories',[])),timeout=3600,progress=lambda p,label:progress(.62+.31*p,label))
        else:
            candidates=speech_candidates(transcript['sentences'],minimum,maximum,mode)
        if settings['semantic'] and mode!='Sports' and candidates and not all(c.get('topic_group') for c in candidates):
            progress(.65,'Reviewing meaning with the selected local model')
            candidates=worker('review',dict(sentences=transcript['sentences'],candidates=candidates,mode=mode,quality=settings.get('quality','Balanced'),editor_model=settings.get('editor_model'),categories=settings.get('categories',[])))
        elif mode!='Sports' and not settings['semantic']:
            for c in candidates:
                c.update(title=c.get('title',c['text'][:65]),passed=False,reason=c.get('reason','Selected from transcript boundaries.'),concern='Local meaning review was not enabled.')
        if mode=='Sports' and settings.get('scenes'):
            progress(.93,'Finding scene boundaries')
            candidates=apply_scene_context(candidates,scene_times(source,folder/'scene-cuts-v2.json'),total)
        if candidates and not any(c.get('shorts_editor_error') for c in candidates):write(reviewed_path,dict(candidates=candidates,diagnostics=diagnostics))
    progress(.94,'Checking openings, useful content and payoff')
    if mode=='Interview':
        from interview_integrity import verify,topic_title
        for c in candidates:
            if c.get('edit_plan') or settings.get('shorts_editor'):continue
            c['title']=topic_title(c['text'])
            if c.get('context_uncertain') or not verify(c,transcript['sentences']):
                c.update(passed=False,boundary_rejected=True,concern='Requires exactly one complete question-and-answer exchange without trailing setup.')
        from interview import protect_endings
        candidates=[c if c.get('edit_plan') or settings.get('shorts_editor') else protect_endings([c],transcript['words'],total)[0] for c in candidates]
    from audience_quality import annotate
    candidates=annotate(candidates,mode)
    if settings.get('multimodal_curation') and candidates:
        from multimodal_curation import curate
        candidates,curation=curate(project,transcript,candidates,settings,lambda p,label:progress(.945+.04*p,label))
        diagnostics['multimodal_curation']={k:v for k,v in curation.items() if k!='candidates'}
    progress(.99,'Ranking distinct complete moments and saving results')
    exclusions=[]
    before_count=len(candidates)
    all_drafts=list(candidates)
    candidates=select_highlights(candidates,total,mode,None,diagnostics=exclusions,coverage=settings.get('coverage',1.0 if mode!='Sports' else .35),strict=mode!='Sports' and settings.get('quality')=='Higher quality')
    path=analysis_path(project,settings);path.write_text(json.dumps(candidates,ensure_ascii=False,indent=2))
    diagnostics.update(kept=len(candidates),drafts=before_count,exclusions=exclusions)
    if settings.get('shorts_editor') and mode!='Sports':
        diagnostics['editorial_failures']=[dict(start=c['start'],end=c['end'],text=c['text'],reason=c['shorts_editor_error']) for c in all_drafts if c.get('shorts_editor_error')]
    path.with_suffix('.diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    if mode=='Sports':
        diagnostics.update(kept=len(candidates),drafts=before_count,exclusions=exclusions)
        for event in diagnostics.get('events',[]):
            draft=next((c for c in all_drafts if c.get('event_anchor')==event['anchor']),None)
            if draft is not None:
                event['status']='Kept' if draft in candidates else 'Excluded: '+next((e['reason'] for e in exclusions if e['start']==draft['start'] and e['end']==draft['end']),'selection limit')
        if not settings['vision']:diagnostics.update(found=before_count,reviewed=0,review_succeeded=0,note='Motion-only drafts; local AI frame review disabled.')
        path.with_suffix('.diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
    history=folder/'ui-timing.json';data=read(history,{})
    if not isinstance(data,dict):data={}
    key=timing_key(settings)
    if not isinstance(prior,dict):
        data[key]=time.monotonic()-begun;write(history,data)
    from project_store import save_run
    save_run(project,settings,path)
    progress(1,'Ready to review')
    return str(path)
