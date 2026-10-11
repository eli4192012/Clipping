"""Open checked edits after an interruption without inference or a cache reset."""
import hashlib
import json
from pathlib import Path

from project_store import read, write, save_run
from upgrades import transcript_file


class _MissingReview(Exception):
    pass


def _cached_only():
    raise _MissingReview()


def recover_checked_edits(project, settings):
    """A separate partial selection, using only this run's approved cached edits."""
    if not settings.get('shorts_editor') or settings['mode']=='Sports':return None
    folder=Path(project['folder'])
    transcript=read(transcript_file(folder,settings),None)
    if not isinstance(transcript,dict) or not {'sentences','words'}<=transcript.keys():return None
    from local_editor import cache_folder, selected_editor, IDENTITIES
    cache=folder/'topic-reviews-v37'
    identity=None
    if settings.get('editor_model'):
        cache=cache_folder(cache,settings['editor_model'])
        identity=IDENTITIES[selected_editor(settings,large=True)]
    if settings['mode']=='Interview':
        from topic_cache import editorial_interview_sources
        candidates=editorial_interview_sources(transcript['sentences'],settings['maximum'])
    else:
        inputs=[transcript['sentences'],settings['minimum'],settings['maximum'],settings['mode'],
                settings.get('quality','Balanced'),settings.get('categories',[]),'shorts-proposals-1','proposals-v58']
        key=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
        candidates=read(cache/('proposals-'+key+'.json'),None)
    if not isinstance(candidates,list):return None
    from shorts_editor import edit_candidate
    completed=[]
    for candidate in candidates:
        try:
            edit=edit_candidate(candidate,transcript['sentences'],transcript['words'],settings['maximum'],
                settings.get('quality','Balanced'),cache/'shorts',_cached_only,
                editor_identity=identity,minimum=settings['minimum'],mode=settings['mode'])
        except (_MissingReview,ValueError,TypeError,KeyError,AttributeError):continue
        plan=edit.get('edit_plan',{})
        if edit.get('passed') is True and plan.get('meaning_preserved') is True and plan.get('standalone_context_check',{}).get('passed') is True:
            completed.append(edit)
    if not completed:return None
    from audience_quality import annotate
    from modes import select_highlights
    from jobs import analysis_path
    exclusions=[]
    clips=select_highlights(annotate(completed,settings['mode']),project['duration'],settings['mode'],None,
        diagnostics=exclusions,coverage=settings.get('coverage',1.),strict=settings.get('quality')=='Higher quality')
    final=analysis_path(project,settings)
    recovered=final.with_name(final.stem+'-recovered.json').resolve()
    report=dict(partial_analysis=True,recovered_edits=len(completed),source_candidates=len(candidates),
        drafts=len(completed),kept=len(clips),exclusions=exclusions,
        note='Recovered checked speech edits. Full analysis and any remaining visual/sound review are unfinished.')
    if read(recovered,None)!=clips or read(recovered.with_suffix('.diagnostics.json'),None)!=report:
        write(recovered,clips);write(recovered.with_suffix('.diagnostics.json'),report)
        save_run(project,settings,recovered)
    return dict(result=str(recovered),**report)


def resume_saved_analysis(root, project, settings):
    """Queue the same settings; never interrupt another run or override a pause."""
    from clip_queue import QueueStore, ensure_runner
    store=QueueStore(root)
    item,_=store.add(project,settings,export_clips=True)
    store.auto_start()
    ensure_runner(root)
    return item
