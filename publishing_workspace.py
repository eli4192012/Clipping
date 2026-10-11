"""Saved exports, checked posting text and durable local preparation."""
import hashlib
import json
import re
from pathlib import Path

from project_store import read, write
from combined_video import clip_id
import social_store as store
WORKSPACE_API = 5


def preferences(root):
    data=read(Path(root)/'data/publishing-workspace.json',{})
    return data if isinstance(data,dict) else {}


def save_preferences(root, **fields):
    current=preferences(root);updated=dict(current,**fields)
    if updated!=current:write(Path(root)/'data/publishing-workspace.json',updated)


def add_project(root, folder):
    selected=preferences(root).get('projects',[])
    folder=str(Path(folder).resolve())
    save_preferences(root,projects=list(dict.fromkeys([*selected,folder])))


def file_state(video):
    video=Path(video);stat=video.stat()
    return [stat.st_size,stat.st_mtime_ns]


def register_render(folder, run, candidate, package, settings, video, captions, render_id):
    """Save the final speech package belonging to this exact finished video."""
    folder=Path(folder);video=Path(video).resolve();key=clip_id(video)
    row=dict(id=key,folder=str(folder.resolve()),run=str(Path(run).resolve()),
        candidate=dict(start=candidate['start'],end=candidate['end']),
        video=str(video),captions=str(Path(captions).resolve()),render_id=render_id,
        media_state=file_state(video),package=package,settings=dict(settings),title=candidate.get('title','Saved clip'))
    path=folder/'publishing-clips.json';saved=read(path,{})
    if saved.get(key)!=row:write(path,dict(saved,**{key:row}))
    return row


def _plain(text):
    return ' '.join(re.findall(r'\w+',text.casefold()))


def _legacy_package(folder, captions, video, packages):
    from combined_video import _cues
    speech=' '.join(re.sub(r'<[^>]*>|\{[^}]*\}','',cue[2]).replace('\n',' ') for cue in _cues(captions)).strip()
    matching=[p for p in packages if _plain(p.get('final_transcript',''))==_plain(speech)] if speech else []
    if matching:return matching[-1]
    fingerprint=hashlib.sha256(json.dumps([str(Path(video).resolve()),file_state(video),speech]).encode()).hexdigest()[:24]
    return dict(fingerprint=fingerprint,final_transcript=speech,posting={})


def catalog(root, folders):
    """Index registered renders and older saved exports without re-rendering them."""
    root=Path(root);selected={Path(folder).resolve() for folder in folders}
    attempts=store.drafts();rows=[];errors=[]
    for folder in selected:
        if folder.parent!=(root/'data').resolve() or not folder.is_dir():continue
        project=dict(read(folder/'project.json',{}),folder=str(folder));known=read(folder/'publishing-clips.json',{})
        videos={}
        for manifest in folder.glob('render-*.json'):
            paths=read(manifest,None)
            if isinstance(paths,list) and len(paths)==2 and Path(paths[0]).is_file():
                videos[clip_id(paths[0])]=dict(video=paths[0],captions=paths[1],render_id=manifest.stem[7:])
        for key,item in read(folder/'finished-clips.json',{}).items():
            if isinstance(item,dict) and Path(item.get('video','')).is_file():
                videos[key]=dict(videos.get(key,{}),**item)
        for key,item in known.items():
            if isinstance(item,dict) and Path(item.get('video','')).is_file():videos.setdefault(key,item)
        packages=[p for file in sorted((folder/'packaging-v517').glob('*.json'),key=lambda p:p.stat().st_mtime)
                  if isinstance(p:=read(file,None),dict)]
        from project_store import runs_for
        matching_clips={}
        for run in runs_for(project):
            for candidate in read(run['result'],[]):
                matching_clips.setdefault(_plain(candidate['text']),(run,candidate))
        for key,item in videos.items():
            try:
                video=Path(item['video']).resolve();state=file_state(video)
                if not state[0]:continue
                row=known.get(key)
                if not isinstance(row,dict) or row.get('media_state')!=state:
                    draft=next((d for d in attempts if Path(d.get('video','')).resolve()==video and '-attempt-' not in d['id']),None)
                    package=_legacy_package(folder,item.get('captions'),video,packages)
                    match=matching_clips.get(_plain(package['final_transcript']))
                    row=dict(id=key,folder=str(folder),video=str(video),captions=item.get('captions',''),media_state=state,
                        render_id=item.get('render_id',key),package=package,settings=match[0]['settings'] if match else read(folder/'ui-settings.json',{}),
                        run=draft['run'] if draft else match[0]['result'] if match else 'saved-export-'+key+'.json',
                        candidate=draft['candidate'] if draft else dict(start=match[1]['start'],end=match[1]['end']) if match else dict(start=0.,end=max(1.,float(item.get('duration',1.)))),
                        title=item.get('title','Saved clip'))
                rows.append(dict(row,project_title=project.get('title',folder.name)))
            except (OSError,ValueError,TypeError,KeyError) as error:
                errors.append(f"{project.get('title',folder.name)}: {error}")
    # Display the newest look for a registered source clip, while retaining every file.
    latest={}
    from clip_usage import clip_key
    for row in sorted(rows,key=lambda r:r['media_state'][1]):
        key=(row['folder'],clip_key(row['run'],row['candidate']))
        latest[key]=row
    return sorted(latest.values(),key=lambda row:row['media_state'][1],reverse=True),errors


def posting_text(row):
    """Manual board edits and existing clip-editor text take precedence over AI."""
    from social_copy import VERSION,inline_title,cached_copy
    manual=read(Path(row['folder'])/'publishing-text.json',{}).get(row['id'])
    if isinstance(manual,dict) and manual.get('media_state')==row['media_state']:
        return dict(title=manual['title'],description=manual['description'])
    package=row['package']
    saved=read(Path(row['folder'])/'platform-posts-v517.json',{}).get(package['fingerprint'],{}).get('YouTube Shorts',{})
    if isinstance(saved,dict) and (saved.get('copy_origin')=='manual' or saved.get('ai_version')==VERSION):
        text=dict(title=inline_title(saved.get('title',''),[*saved.get('hashtags',[]),'#fyp']) if saved.get('title') else '',description=saved.get('description',''))
        if all(text.values()):return text
        # An incomplete manual edit must stay available for the user to finish.
        if saved.get('copy_origin')=='manual':return text
    cached=cached_copy(row['folder'],package,row.get('settings',{}))
    return dict(title=cached['title'],description=cached['description']) if cached else dict(title='',description='')


def save_text(row, title, description, only_if_missing=False):
    from social_copy import inline_title
    title=inline_title(title,['#fyp']);description=description.strip()
    if not title.strip() or len(title)>100 or '<' in title or '>' in title:raise ValueError('Use a title of 1–100 characters, including hashtags, without < or >.')
    if '#fyp' not in {tag.casefold() for tag in re.findall(r'#[\w]+',title)}:raise ValueError('Leave room for #fyp in the title.')
    if not description:raise ValueError('Add a description about this clip.')
    if len(description.encode('utf-8'))>5000:raise ValueError('The description exceeds 5,000 bytes.')
    import fcntl
    path=Path(row['folder'])/'publishing-text.json'
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if file_state(row['video'])!=row['media_state']:raise ValueError('This export changed while its text was being prepared. Refresh Publishing.')
        saved=read(path,{})
        if only_if_missing:
            # A user may have saved text while the local writer was running.
            current=saved.get(row['id'],{})
            if current.get('media_state')==row['media_state'] and current.get('title') and current.get('description'):
                return dict(title=current['title'],description=current['description'])
            editor=read(Path(row['folder'])/'platform-posts-v517.json',{}).get(row['package']['fingerprint'],{}).get('YouTube Shorts',{})
            if editor.get('copy_origin')=='manual':return posting_text(row)
        write(path,dict(saved,**{row['id']:dict(title=title,description=description,media_state=row['media_state'])}))
    return dict(title=title,description=description)


def prepare_text(row, progress=lambda p,label:None):
    text=posting_text(row)
    if text['title'].strip() and text['description'].strip():
        progress(1,'Reused saved posting text');return text
    editor=read(Path(row['folder'])/'platform-posts-v517.json',{}).get(row['package']['fingerprint'],{}).get('YouTube Shorts',{})
    if editor.get('copy_origin')=='manual':raise ValueError('Your saved manual posting text is incomplete. Finish it in Publishing or Social media.')
    if not row['package'].get('final_transcript','').strip():raise ValueError('This clip has no saved speech. Enter its posting text manually.')
    from social_copy import get_copy
    result=get_copy(Path(row['folder']),row['package'],row['settings'],progress)
    return save_text(row,result['title'],result['description'],only_if_missing=True)


def text_task_key(row):
    from social_copy import identity
    from posting_style import for_clip
    key,_=identity(row['package'],row.get('settings',{}),for_clip(row['folder'],row['package']))
    return hashlib.sha256(json.dumps([row['id'],row['media_state'],key]).encode()).hexdigest()[:24]


def text_status(row, key=None):
    editor=read(Path(row['folder'])/'platform-posts-v517.json',{}).get(row['package']['fingerprint'],{}).get('YouTube Shorts',{})
    if editor.get('copy_origin')=='manual' and not (editor.get('title','').strip() and editor.get('description','').strip()):
        return dict(error='Your saved manual posting text is incomplete. Finish it below or in Social media.')
    saved=read(Path(row['folder'])/'publishing-text-status.json',{}).get(row['id'],{})
    if not saved:return {}
    return saved if saved.get('key')==(key or text_task_key(row)) else {}


def _record_text_status(row, error=''):
    path=Path(row['folder'])/'publishing-text-status.json'
    write(path,dict(read(path,{}),**{row['id']:dict(key=text_task_key(row),error=error)}))


def queue_text(root, rows, retry=False, copies=None):
    """Enqueue missing copy once per export/AI identity; never render or publish."""
    from clip_queue import QueueStore,ensure_runner
    from clip_usage import clip_key
    queue=QueueStore(root);prior=queue.items();drafts=store.drafts();groups={}
    attempted={task['key'] for item in prior for task in item['settings'].get('publishing_text',[])}
    active_folders={str(Path(i['project']['folder']).resolve()) for i in prior if i['state'] in ('queued','running')}
    for row in rows:
        text=copies[row['id']] if copies is not None else posting_text(row)
        if row['folder'] in active_folders or all(text.values()):continue
        editor=read(Path(row['folder'])/'platform-posts-v517.json',{}).get(row['package']['fingerprint'],{}).get('YouTube Shorts',{})
        if editor.get('copy_origin')=='manual':continue
        if any(d['folder']==row['folder'] and (Path(d['video']).resolve()==Path(row['video']).resolve() or clip_key(d['run'],d['candidate'])==clip_key(row['run'],row['candidate']))
               and (d['status']!='Draft' or d.get('title') and d.get('description')) for d in drafts):continue
        key=text_task_key(row)
        if not retry and (key in attempted or text_status(row,key).get('error')):continue
        groups.setdefault(row['folder'],[]).append(dict(id=row['id'],media_state=row['media_state'],key=key))
    items=[]
    for folder,tasks in groups.items():
        row=next(r for r in rows if r['folder']==folder)
        project=dict(read(Path(folder)/'project.json',{}),folder=folder)
        project.setdefault('title',row.get('project_title','Saved clips'))
        settings=dict(row.get('settings',{}),publishing_text=sorted(tasks,key=lambda t:t['id']))
        item,_=queue.add(project,settings,export_clips=False,once=not retry);items.append(item)
    if items:
        queue.auto_start();ensure_runner(root)
    return items


def attempts_for(row, account_id):
    from clip_usage import clip_key
    return [d for d in store.drafts(row['folder']) if d['account_id']==account_id and '-attempt-' not in d['id']
            and (Path(d['video']).resolve()==Path(row['video']).resolve()
                 or clip_key(d['run'],d['candidate'])==clip_key(row['run'],row['candidate']))]


def _save_clip_draft(row, account, title, description, privacy, made_for_kids, share_to_feed=True,
                     publish_at=None,schedule_timezone=None,schedule_provider=None):
    if file_state(row['video'])!=row['media_state']:raise ValueError('This export changed. Refresh the publishing tab before posting.')
    attempts=attempts_for(row,account['id'])
    if any(d['status']!='Draft' for d in attempts):raise ValueError('This clip already has a posting attempt. Check its status before posting again.')
    text=save_text(row,title,description)
    existing=next(iter(attempts),None)
    key=existing['id'] if existing else store.identity(row['folder'],row['run'],row['candidate'],account['id'],row['render_id'])
    draft=dict(existing or {},id=key,folder=row['folder'],run=row['run'],candidate=row['candidate'],
        render_id=row['render_id'],video=row['video'],file_size=row['media_state'][0],file_mtime=row['media_state'][1],
        account_id=account['id'],account_name=account['name'],platform=account['platform'],
        title=text['title'],description=(text['title']+'\n\n'+text['description'].removeprefix(text['title']+'\n\n') if account['platform']=='instagram' else text['description']),
        privacy=privacy,made_for_kids=made_for_kids,share_to_feed=share_to_feed,status='Draft',
        publish_at=publish_at,schedule_timezone=schedule_timezone,schedule_provider=schedule_provider)
    store.validate(draft)
    return store.save_draft(draft)


def publish_clip(row, account, title, description, privacy, made_for_kids, share_to_feed=True, progress=lambda *args:None):
    """One click saves the displayed text and publishes the exact shown export."""
    from social_publish import publish
    draft=_save_clip_draft(row,account,title,description,privacy,made_for_kids,share_to_feed)
    return publish(draft['id'],progress,expected_updated=draft['updated'],prevent_duplicate=True)


def schedule_clip(row,account,title,description,made_for_kids,publish_at,schedule_timezone,share_to_feed=True,progress=lambda *args:None):
    from social_schedule import future_time,ensure_scheduler
    from social_publish import publish,upload_lock
    from zoneinfo import ZoneInfo
    publish_at=future_time(publish_at);ZoneInfo(schedule_timezone)
    if account['platform']=='youtube':
        draft=_save_clip_draft(row,account,title,description,'private',made_for_kids,share_to_feed,
            publish_at,schedule_timezone,'youtube')
        return publish(draft['id'],progress,expected_updated=draft['updated'],prevent_duplicate=True)
    with upload_lock():
        draft=_save_clip_draft(row,account,title,description,'public',made_for_kids,share_to_feed,
            publish_at,schedule_timezone,'local')
        draft=store.save(dict(draft,status='Scheduled'))
    ensure_scheduler(Path(row['folder']).parent.parent)
    return draft


def queue_preparation(root, projects):
    """Reuse completed analyses; the background queue renders and writes locally."""
    from clip_queue import QueueStore,ensure_runner
    store_queue=QueueStore(root);items=[]
    for entry in projects:
        runs=[r for r in entry['runs'] if not read(Path(r['result']).with_suffix('.diagnostics.json'),{}).get('partial_analysis')]
        if not runs:continue
        run=runs[0];settings=dict(run['settings'],publishing_prepare=True,publishing_run=run['result'])
        item,_=store_queue.add(entry['project'],settings,export_clips=True);items.append(item)
    store_queue.auto_start();ensure_runner(root)
    return items


def prepare_project(project, settings, result, outputs, progress=lambda p,label:None):
    """Prepare copies for this queue job's exact exports; successful text is retained."""
    rows,errors=catalog(Path(project['folder']).parent.parent,[project['folder']])
    wanted={Path(o['video']).resolve() for o in outputs}
    rows=[r for r in rows if Path(r['video']).resolve() in wanted or Path(r['run']).resolve()==Path(result).resolve()]
    return prepare_rows(rows,progress,errors)


def prepare_rows(rows, progress=lambda p,label:None, errors=()):
    failures=list(errors)
    for i,row in enumerate(rows):
        try:
            prepare_text(row,lambda p,label:progress((i+p)/max(1,len(rows)),f'Posting text {i+1} of {len(rows)} · '+label))
            _record_text_status(row)
        except Exception as error:
            from app_logging import log_exception
            from social_copy import posting_error
            message=posting_error(error)
            log_exception('Publishing preparation failed');failures.append(row['title']+': '+message)
            _record_text_status(row,message)
        progress((i+1)/max(1,len(rows)),f'Checked posting text {i+1} of {len(rows)}')
    if failures:raise ValueError('Some posting text needs attention. Saved clips and successful text are kept. '+'; '.join(failures))


def prepare_queued_text(root, item, progress=lambda p,label:None):
    rows,errors=catalog(root,[item['project']['folder']])
    by_id={r['id']:r for r in rows};wanted=[]
    for task in item['settings']['publishing_text']:
        row=by_id.get(task['id'])
        if row is None or row['media_state']!=task['media_state']:
            errors.append('An export changed or was removed; refresh Publishing to prepare its current version.')
        else:wanted.append(row)
    return prepare_rows(wanted,progress,errors)
