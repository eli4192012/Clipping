"""Project selection, saved posting copy and explicit one-button publishing."""
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo,available_timezones
import streamlit as st
import social_store as store
import social_publish as publisher
import publishing_workspace as workspace
from project_store import library, read
PUBLISHING_FORM_API = 8


def _go_editor(row, go):
    run=Path(row['run'])
    candidates=read(run,None)
    if not isinstance(candidates,list):return
    index=next((i for i,c in enumerate(candidates) if c['start']==row['candidate']['start'] and c['end']==row['candidate']['end']),None)
    if index is None:return
    project=read(Path(row['folder'])/'project.json',{})
    st.session_state.update(project=project,settings=row['settings'],result_path=str(run),clip_index=index)
    go('editor')


def _status(draft,prefix='workspace'):
    st.write('**'+draft['status']+'** · '+draft['account_name'])
    if draft.get('url'):st.link_button('Open on '+draft['platform'].title(),draft['url'])
    if draft.get('error'):st.warning(draft['error'])
    from social_schedule_ui import schedule_panel
    if schedule_panel(draft,prefix):return
    if draft['status']=='Published':
        st.success('Published. This clip is marked Used.')
        if draft['platform']=='youtube':st.caption('YouTube visibility: '+draft.get('actual_privacy','unknown'))
        return
    if draft['status']!='Draft':
        if st.button('Check post status',key=prefix+'-check-'+draft['id']):
            try:
                with st.spinner('Checking the post…'):publisher.check(draft['id'])
                st.rerun()
            except Exception as error:st.error(str(error))
        allowed=draft['platform']=='youtube' and draft['status']=='Uploading' or draft['platform']=='instagram' and draft['status']=='Ready'
        if allowed and st.button('Continue this upload',key=prefix+'-continue-'+draft['id']):
            try:
                with st.spinner('Continuing the saved upload…'):publisher.publish(draft['id'],expected_updated=draft['updated'],prevent_duplicate=True)
                st.rerun()
            except Exception as error:st.error(str(error))
        if draft['status']=='Failed':st.caption('Open Publishing history to reset this confirmed failure. Uncertain uploads must be checked first.')


@st.fragment(run_every=3)
def show(root, go):
    # A running Streamlit process may still hold the old publisher signature.
    if getattr(publisher,'PUBLISH_WORKSPACE_API',0)<3:
        import importlib
        importlib.reload(publisher)
    root=Path(root)
    st.markdown('<div class="eyebrow">YOUR POSTING DESK</div>',unsafe_allow_html=True)
    st.title('Publishing')
    st.write('Choose projects, check the video and posting text, then publish a clip with one button.')
    config=workspace.preferences(root)
    entries=library(root/'data');options={str(Path(e['project']['folder']).resolve()):e for e in entries}
    selected=st.multiselect('Projects to include',list(options),default=[p for p in config.get('projects',[]) if p in options],
        format_func=lambda p:options[p]['project']['title'],key='publishing-projects')
    if selected!=config.get('projects',[]):workspace.save_preferences(root,projects=selected)
    accounts=[a for a in store.accounts() if a['platform'] in ('youtube','instagram')]
    account=None;privacy=config.get('privacy','private');kids=config.get('made_for_kids');feed=config.get('share_to_feed',True)
    if accounts:
        ids=[a['id'] for a in accounts]
        destination=st.selectbox('Publish to',ids,index=ids.index(config.get('account_id')) if config.get('account_id') in ids else 0,
            format_func=lambda key:next(a['name']+' · '+a['platform'].title() for a in accounts if a['id']==key))
        account=next(a for a in accounts if a['id']==destination)
        if account.get('connection_error'):
            st.warning(account['connection_error'])
            if st.button('Reconnect in Accounts'):go('accounts')
        if account['platform']=='youtube':
            a,b=st.columns(2)
            privacy=a.selectbox('YouTube visibility',['private','unlisted','public'],index=['private','unlisted','public'].index(privacy if privacy in ('private','unlisted','public') else 'private'))
            audience=b.selectbox('Made for kids?',['Choose…','No','Yes'],index=0 if kids is None else 2 if kids else 1)
            kids=None if audience=='Choose…' else audience=='Yes'
            st.caption('The selected visibility applies to new posts. YouTube may keep uploads private until the Google API project passes its audit.')
        else:
            privacy='public';feed=st.checkbox('Also share Reels to Instagram feed',value=feed)
        workspace.save_preferences(root,account_id=destination,privacy=privacy,made_for_kids=kids,share_to_feed=feed)
    else:
        st.info('Connect YouTube or Instagram once to enable publishing. You can prepare clips and text now.')
        if st.button('Connect a social account'):go('accounts')
    from social_schedule import local_zone,posting_time
    zones=list(dict.fromkeys([local_zone(),'America/Chicago','America/New_York','America/Denver','America/Los_Angeles','UTC',*sorted(available_timezones())]))
    saved_zone=config.get('schedule_timezone',local_zone())
    zone=st.selectbox('Scheduling timezone',zones,index=zones.index(saved_zone) if saved_zone in zones else 0)
    workspace.save_preferences(root,schedule_timezone=zone)
    if not selected:
        st.info('Select the projects whose clips you want here. Your selection is saved for next time.')
        return
    rows,errors=workspace.catalog(root,selected)
    for error in errors:st.warning(error)
    cached={row['id']:workspace.posting_text(row) for row in rows}
    try:workspace.queue_text(root,rows,copies=cached)
    except Exception as error:st.warning('Could not start automatic posting text: '+str(error))
    a,b,c=st.columns(3)
    if a.button('Prepare missing clips & AI text',type='primary'):
        try:
            items=workspace.queue_preparation(root,[options[p] for p in selected])
            if items:st.success(f'{len(items)} project(s) queued for local preparation. Completed clips and text are reused.')
            else:st.warning('These projects need completed analysis first. Open them or check the video queue.')
        except Exception as error:st.error(str(error))
    if b.button('Retry missing AI text'):
        try:
            items=workspace.queue_text(root,rows,retry=True)
            if items:st.success('Missing AI text queued again. Saved text is kept.')
            else:st.info('No missing text to retry, or preparation is already queued.')
        except Exception as error:st.error(str(error))
    if c.button('View preparation progress'):go('queue')
    st.caption('AI titles, inline hashtags and descriptions are prepared automatically for finished clips. Local preparation continues when you leave this page. Review the text, then publish.')
    from clip_queue import QueueStore
    queue=QueueStore(root)
    preparations=[i for i in queue.items() if (i['settings'].get('publishing_prepare') or i['settings'].get('publishing_text')) and str(Path(i['project']['folder']).resolve()) in selected]
    latest_preparations={}
    for item in sorted(preparations,key=lambda i:i['created']):
        latest_preparations[str(Path(item['project']['folder']).resolve())]=item
    current=next((i for i in latest_preparations.values() if i['state']=='running'),None)
    if current:
        st.info(current['project']['title']+' · '+current['label'])
        st.progress(max(0.,min(1.,current['progress'])))
    waiting=sum(i['state']=='queued' for i in latest_preparations.values())
    if waiting:
        st.caption(f'{waiting} project(s) waiting for local posting preparation.')
        if not queue.enabled():st.caption('The video queue is paused. Open preparation progress and continue the queue to generate text.')
    failed=[item for item in latest_preparations.values() if item['state']=='failed' and
            any(not all(cached[r['id']].values()) for r in rows if r['folder']==str(Path(item['project']['folder']).resolve()))]
    if failed:
        with st.expander(f'Preparation issues · {len(failed)} project(s)'):
            for item in failed:st.warning('Preparation needs attention: '+item['error'])
    if not rows:st.info('No finished exports yet. Use Prepare missing clips & AI text, or finish analysis in the video queue.')
    attempts={row['id']:workspace.attempts_for(row,account['id']) if account else [] for row in rows}
    for row in rows:
        draft=next((d for d in attempts[row['id']] if d['status']=='Draft'),None)
        if draft:cached[row['id']]=dict(title=draft['title'],description=draft['description'])
    ready=[row for row in rows if all(cached[row['id']].values()) and not any(d['status']!='Draft' for d in attempts[row['id']])]
    missing=[row for row in rows if not all(cached[row['id']].values()) and not any(d['status']!='Draft' for d in attempts[row['id']])]
    needs_review=sum(bool(workspace.text_status(row).get('error')) for row in missing)
    a,b,c,d=st.columns(4)
    a.metric('Ready clips',len(ready));b.metric('Preparing text',len(missing)-needs_review)
    c.metric('Text needs review',needs_review);d.metric('Posting attempts',sum(bool(attempts[r['id']]) for r in rows))
    ready_tab,prepare_tab,scheduled_tab,history_tab=st.tabs(['Ready to post','Needs preparation','Scheduled posts','Posting history'])
    for name,tab,collection in (('Ready',ready_tab,ready),('Preparation',prepare_tab,missing)):
        with tab:
            if not collection:st.info('No clips in this list.')
            if len(collection)>12:
                pages=(len(collection)+11)//12;page_key='publishing-clip-page-'+name
                if st.session_state.get(page_key,1)>pages:st.session_state[page_key]=pages
                page=st.number_input(name+' clip page',min_value=1,max_value=pages,value=1,step=1,key=page_key)
                st.caption(f'Showing clips {(page-1)*12+1}–{min(page*12,len(collection))} of {len(collection)}')
                collection=collection[(page-1)*12:page*12]
            for row in collection:
                key=row['id'];copy=cached[key];draft=next((d for d in attempts[key] if d['status']=='Draft'),None)
                with st.container(border=True):
                    st.caption(row['project_title'])
                    st.subheader(copy['title'] or row['title'])
                    if read(Path(row['run']).with_suffix('.diagnostics.json'),{}).get('partial_analysis'):
                        st.warning('Recovered speech edit: full analysis and visual/sound review are unfinished.')
                    if st.checkbox('Preview video',key='publish-preview-'+key):st.video(row['video'])
                    if not copy['title'] or not copy['description']:
                        status=workspace.text_status(row)
                        if status.get('error'):st.warning('AI text needs review: '+status['error'])
                        else:st.caption('AI posting text is prepared automatically in the video queue. You can also write it here.')
                    if draft:
                        st.caption('Saved draft for '+draft['account_name']+' · '+draft.get('privacy','public'))
                        copy=dict(title=draft['title'],description=draft['description'])
                        if draft['platform']=='instagram':copy['description']=copy['description'].removeprefix(copy['title']+'\n\n')
                    schedule=st.checkbox('Schedule this post',key='schedule-clip-'+key+'-'+(account['id'] if account else 'none'),disabled=not account)
                    if schedule:
                        st.caption('Upload to YouTube now; it stays private until the selected public release time.' if account['platform']=='youtube'
                            else 'Instagram will post at this time while your Mac is awake and online. More than an hour late needs rescheduling.')
                    with st.form('publish-clip-'+key):
                        title=st.text_input('Title with hashtags',value=copy['title'],max_chars=100)
                        description=st.text_area('Description about this clip',value=copy['description'],height=110)
                        st.caption('Titles include #fyp. Instagram uses the title and description together as its Reel caption.')
                        if schedule:
                            now=datetime.now(ZoneInfo(zone));default=(now+timedelta(hours=1)).replace(second=0,microsecond=0)
                            input_key='schedule-date-'+key+'-'+account['id']+'-'+zone
                            initial_day,initial_clock=st.session_state.setdefault(input_key,(default.date(),default.time()))
                            a,b=st.columns(2)
                            post_day=a.date_input('Post date',value=initial_day,min_value=min(initial_day,now.date()),key=input_key+'-day')
                            post_clock=b.time_input('Post time',value=initial_clock,step=60,key=input_key+'-clock')
                            st.caption('Posting timezone: '+zone)
                        a,b=st.columns(2)
                        save=a.form_submit_button('Save posting text')
                        post=b.form_submit_button(('Schedule to ' if schedule else 'Publish to ')+account['name'] if account else 'Connect an account to publish',
                            type='primary',disabled=not account or account['platform']=='youtube' and kids is None)
                    if save:
                        try:workspace.save_text(row,title,description);st.rerun()
                        except ValueError as error:st.error(str(error))
                    if post:
                        progress=st.progress(0,text='Starting upload…')
                        try:
                            update=lambda p,label:progress.progress(max(0.,min(1.,p)),text=label)
                            if schedule:
                                workspace.schedule_clip(row,account,title,description,draft.get('made_for_kids',kids) if draft else kids,
                                    posting_time(post_day,post_clock,zone),zone,feed,update)
                            else:
                                workspace.publish_clip(row,account,title,description,
                                    draft.get('privacy',privacy) if draft else privacy,
                                    draft.get('made_for_kids',kids) if draft else kids,feed,update)
                            st.rerun()
                        except Exception as error:st.error(str(error))
                    if Path(row['run']).is_file() and st.button('Open clip editor',key='publishing-editor-'+key):_go_editor(row,go)
    drafts=[d for d in store.drafts() if str(Path(d['folder']).resolve()) in selected and (not account or d['account_id']==account['id'])]
    with scheduled_tab:
        schedules=[d for d in drafts if d.get('publish_at') and d['status'] not in ('Draft','Published','Failed') and '-attempt-' not in d['id']]
        if not schedules:st.info('Choose Schedule this post on a ready clip to pick a date and time.')
        for draft in schedules:
            with st.expander(draft['title']+' · '+draft['status']):_status(draft,'workspace-scheduled')
    with history_tab:
        if not drafts:st.info('Posts and upload status for these projects will appear here.')
        if drafts and st.button('Refresh post status'):
            failures=[]
            with st.spinner('Checking saved posting attempts…'):
                for draft in drafts:
                    if draft['status'] in ('Draft','Published','Failed','Schedule failed') or draft['status']=='Scheduled' and draft.get('schedule_provider')=='local':continue
                    try:publisher.check(draft['id'])
                    except Exception as error:failures.append(draft['title']+': '+str(error))
            if failures:st.warning('\n'.join(failures))
            else:st.rerun()
        for draft in drafts:
            with st.expander(draft['title']+' · '+draft['status']):_status(draft)
