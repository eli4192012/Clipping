from resource_limits import configure
configure()
import hashlib
import html
import json
from pathlib import Path
import streamlit as st
from engine import ROOT,SPEECH,EDITOR,duration,export_clip
from interview import interview_content
from vision_sports import VISION,football_hint
from modes import PROFILES
from youtube_import import lookup,download,normalize_url
from jobs import analyze,analysis_path,estimate_seconds
from ui_jobs import run_job,clock
from review_ui import review_form,review_history
from upgrades import TURBO,EDITOR4,VISION4,SPEAKERS,transcript_file
from local_editor import QWEN35,CHOICES,LABELS,installed,preferred_editor

st.set_page_config(page_title='Clipping · Your local studio',page_icon=str(ROOT/'assets/mark.svg'),layout='wide',initial_sidebar_state='expanded')
version=json.loads((ROOT/'version.json').read_text())
release=f"v{version['major']}.{version['minor']}"
from studio_ui import install,brand as studio_brand
install(st)
@st.dialog('What changed',width='large')
def release_report():
    st.markdown((ROOT/'RELEASE_NOTES.md').read_text())
    validation=ROOT/f"V{version['major']}{version['minor']}_VALIDATION.md"
    if validation.exists():
        with st.expander('Test results and limitations'):
            st.markdown(validation.read_text())
    benchmark=ROOT/'TRANSNET_BENCHMARK.md'
    if benchmark.exists():
        with st.expander('TransNet V2 benchmark'):
            st.markdown(benchmark.read_text())

with st.container(key='release-header'):
    brand,version_button=st.columns([8,1])
    brand.markdown('<span class="header-label">Clipping / Local video studio</span>',unsafe_allow_html=True)
    if version_button.button(release,help='Open the release report',use_container_width=True):release_report()
st.session_state.setdefault('page','library')
page=st.session_state.page
stages=['source','settings','processing','complete','results','editor']
active=0 if page=='source' else 1 if page=='settings' else 2 if page=='processing' else 3
if page not in ('library','source','accounts','social_history','combine','examples'):
    st.markdown('<nav class="steps" aria-label="Project progress">'+ '<span class="step-connector" aria-hidden="true">—</span>'.join(f'<span class="step {"active" if i==active else "done" if i<active else ""}" '+('aria-current="step"' if i==active else '')+f'><span class="step-number">{"✓" if i<active else f"{i+1:02}"}</span>{name}</span>' for i,name in enumerate(['Add video','Make it yours','Find moments','Review clips']))+'</nav>',unsafe_allow_html=True)


def go(page):
    st.session_state.page=page
    st.rerun()


def set_project(source,folder,title):
    project={'source':str(source),'folder':str(folder),'title':title,'duration':duration(source)}
    st.session_state.project=project
    (Path(folder)/'project.json').write_text(json.dumps(project))
    saved_settings=Path(folder)/'ui-settings.json'
    if saved_settings.exists():st.session_state.settings=json.loads(saved_settings.read_text())
    else:st.session_state.pop('settings',None)
    st.session_state.pop('result_path',None)
    go('settings')

with st.sidebar:
    st.markdown(studio_brand(),unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">WORKSPACE</div>',unsafe_allow_html=True)
    if page!='processing' and st.button('My projects',icon=':material/home:',use_container_width=True,type='primary' if page=='library' else 'secondary'):go('library')
    if page!='processing' and st.button('＋ New project',icon=':material/add_circle:',use_container_width=True,type='primary' if page=='source' else 'secondary'):go('source')
    if page!='processing' and st.button('Combine clips',icon=':material/playlist_add:',use_container_width=True,type='primary' if page=='combine' else 'secondary'):go('combine')
    if page!='processing' and st.button('Example library',icon=':material/bookmarks:',use_container_width=True,type='primary' if page=='examples' else 'secondary'):go('examples')
    if page!='processing' and st.button('Accounts',icon=':material/group:',use_container_width=True):go('accounts')
    if page!='processing' and st.button('Publishing history',icon=':material/history:',use_container_width=True):go('social_history')
    st.divider()
    with st.expander('Local tools & status'):
        for name,ready in [('Speech',(SPEECH/'model.bin').exists()),('Meaning',(EDITOR/'.ready').exists()),('Sports vision',(VISION/'.ready').exists()),('Turbo speech',(TURBO/'.ready').exists()),('Qwen3.5 AI editor',installed(QWEN35)),('4B meaning',(EDITOR4/'.ready').exists()),('4B sports vision',(VISION4/'.ready').exists()),('Word alignment',(ROOT/'models/alignment/.ready').exists()),('Speaker detection',(SPEAKERS/'.ready').exists())]:
            st.write(f"{'✓' if ready else '○'} {name}")
        st.caption('Missing a model? Run Download Models.command in the Clipping folder.')
    st.markdown('<div class="studio-note"><strong><span class="local-dot"></span>Local by default.</strong><br>Only clips you choose to publish leave this Mac.</div>',unsafe_allow_html=True)

if page=='examples':
    from example_library_ui import show as show_examples
    show_examples(ROOT)
    st.stop()

if page=='combine':
    from combined_video_ui import show as show_combined_video
    show_combined_video(ROOT)
    st.stop()

if page=='accounts':
    from social_ui import accounts_screen
    accounts_screen()
    st.stop()
if page=='social_history':
    from social_ui import history_screen
    history_screen()
    st.stop()

if page=='source':
    st.markdown('<div class="eyebrow">YOUR NEXT GOOD MOMENT</div>',unsafe_allow_html=True)
    st.markdown('<h1>Less footage.<br>More story.</h1>',unsafe_allow_html=True)
    st.write('Bring a video. Find its best moments. Make them yours.')
    with st.container(border=True):
        input_mode=st.radio('Bring your video',['YouTube link','Upload a file'],horizontal=True)
        if input_mode=='Upload a file':
            upload=st.file_uploader('Choose a video',type=['mp4','mov','m4v','mkv','webm'])
            if upload and st.button('Continue with this video',type='primary'):
                digest=hashlib.sha256(upload.getbuffer()).hexdigest()[:24];folder=ROOT/'data'/digest;folder.mkdir(exist_ok=True)
                source=folder/('source'+Path(upload.name).suffix.lower())
                if not source.exists():source.write_bytes(upload.getbuffer())
                try:set_project(source,folder,upload.name)
                except Exception as error:st.error(str(error))
        else:
            link=st.text_input('YouTube video link',placeholder='Paste a watch or Shorts link…')
            if st.button('Find video',type='primary'):
                st.session_state.pop('youtube_info',None)
                try:
                    with st.spinner('Finding your video…'):st.session_state.youtube_info=lookup(link)
                except Exception as error:st.error(f'Could not find the video: {error}')
            try:current,_=normalize_url(link)
            except ValueError:current=None
            info=st.session_state.get('youtube_info')
            if info and current==info['url']:
                st.subheader(info['title']);st.caption(f"{info['channel']} · {clock(info['duration'])}")
                if st.button('Import & continue',type='primary'):
                    status=st.empty()
                    try:
                        source,folder=download(info,status.info);set_project(source,folder,info['title'])
                    except Exception as error:st.error(f'Import failed: {error}')
            st.caption('Use videos you own or are permitted to download and edit. Internet is needed for YouTube imports and social publishing.')
    if st.button('Open my saved projects →'):go('library')
    st.stop()

if page=='library':
    from project_store import library,read
    from datetime import datetime
    from studio_ui import hero,stat_card
    from project_covers import cover_html
    st.markdown(hero(),unsafe_allow_html=True)
    notice=st.session_state.pop('deleted_project_notice',None)
    if notice:st.success(notice)
    all_projects=library(ROOT/'data')
    from creator_profile import show as show_creator_profile
    show_creator_profile(ROOT/'data')
    a,b,c=st.columns(3)
    a.markdown(stat_card('Projects',len(all_projects),'All your video projects','▱'),unsafe_allow_html=True)
    b.markdown(stat_card('Saved runs',sum(len(e['runs']) for e in all_projects),'Completed analysis runs','▷',True),unsafe_allow_html=True)
    c.markdown(stat_card('Storage','On this Mac','Keep your content local','▥'),unsafe_allow_html=True)
    query=st.text_input('Search projects',placeholder='Find a video by name…',label_visibility='collapsed',key='project-search').strip().lower()
    entries=[e for e in all_projects if query in e['project']['title'].lower()]
    if not entries:st.info('No matching projects yet. Import a video to start one.')
    for entry in entries:
        p=entry['project'];runs=entry['runs'];identity=p['folder']
        with st.container(key='project-card-'+hashlib.sha256(identity.encode()).hexdigest()[:12]):
            cover,details,actions=st.columns([2.4,5.3,1.25])
            cover.markdown(cover_html(p),unsafe_allow_html=True)
            stamp=datetime.fromtimestamp(entry['updated']).strftime('%b %d, %Y')
            extension=Path(p['source']).suffix.lstrip('.').upper() or 'VIDEO'
            details.markdown(f'<div class="project-title">{html.escape(p["title"])}</div><div class="project-runs">{len(runs)} saved analysis {"run" if len(runs)==1 else "runs"}</div><div class="project-meta"><span>{html.escape(extension)}</span><span>Updated {stamp}</span><span>Saved locally</span></div>',unsafe_allow_html=True)
            if not entry['available']:st.warning('Source video is missing from disk. The project record is preserved; restore the source to continue.')
            choice=0
            if len(runs)>1:
                with st.expander('Choose a saved run'):
                    choice=st.selectbox('Saved run',range(len(runs)),format_func=lambda i,runs=runs:f"{datetime.fromtimestamp(runs[i]['saved_at']).strftime('%b %d, %Y %H:%M')} · {runs[i]['settings']['mode']} · {runs[i]['count']} clips",key='run-'+identity)
            if actions.button('Open',key='clips-'+identity,type='primary',use_container_width=True,disabled=not entry['available']):
                if runs:
                    if 'duration' not in p:p['duration']=duration(Path(p['source']))
                    st.session_state.project=p;st.session_state.settings=runs[choice]['settings'];st.session_state.result_path=runs[choice]['result'];go('complete')
                else:set_project(Path(p['source']),Path(p['folder']),p['title'])
            with st.expander('Project options'):
                if st.button('Continue / change settings',key='settings-'+identity,disabled=not entry['available']):set_project(Path(p['source']),Path(p['folder']),p['title'])
                from project_delete import confirm_delete
                confirm_delete(p)
    st.stop()

project=st.session_state.get('project')
if not project:go('source')
folder=Path(project['folder']);source=Path(project['source']);total=project['duration'];digest=folder.name
st.caption(project['title'])

if page=='settings':
    from project_covers import cover_html
    from project_store import runs_for
    from studio_ui import setup_heading
    previous=st.session_state.get('settings',{})
    main,preview=st.columns([2.2,1],gap='medium')
    with preview:
        with st.container(key='setup-preview'):
            st.markdown(cover_html(project),unsafe_allow_html=True)
            st.caption(Path(project['source']).suffix.lstrip('.').upper()+' · '+clock(total))
            st.markdown(f'<div class="project-title">{html.escape(project["title"])}</div>',unsafe_allow_html=True)
            st.caption(f'{len(runs_for(project))} saved analysis runs')
            st.caption('Saved on this Mac')
    with main:
        st.markdown('<div class="eyebrow">PROJECT SETUP</div>',unsafe_allow_html=True)
        st.title('Shape your clips.')
        st.write('Choose the kind of moment. We’ll handle the first cut.')
        quality_card,auto_card=st.columns(2,gap='small')
        with quality_card:
            with st.container(key='setup-quality'):
                st.markdown(setup_heading('Processing quality','Choose the best balance for your Mac.','⚙'),unsafe_allow_html=True)
                quality=st.radio('Processing quality',['Balanced','Higher quality'],index=1 if previous.get('resource_defaults')==1 and previous.get('quality')=='Higher quality' else 0,label_visibility='collapsed')
                st.caption('Balanced keeps your Mac responsive. Higher quality uses more memory and may slow other apps.')
        with auto_card:
            with st.container(key='setup-auto'):
                st.markdown(setup_heading('Automatic detection','Let Clipping choose the right video type.','✦',True),unsafe_allow_html=True)
                st.caption('Choose up to two types below, or let the local detector choose.')
    from content_categories import OPTIONS,AUTO,validate,guidance,route,update_selection
    defaults=previous.get('category_selection') or ([AUTO] if previous.get('auto_mode',True) else [previous.get('mode','Interview')])
    with st.container(key='category-picker'):
        picker_key='categories-'+digest
        st.session_state.setdefault(picker_key+'-accepted',defaults)
        selected=st.pills('Video types · select up to 2',OPTIONS,selection_mode='multi',default=defaults,key=picker_key,on_change=update_selection,args=(picker_key,))
        try:selected=validate(selected)
        except ValueError as error:
            st.warning(str(error));st.stop()
    automatic=selected==[AUTO]
    detection=None
    with st.container(key='setup-detection'):
        if automatic:
            from video_type import detect
            detection=run_job('detect-'+digest,lambda update:detect(project,update),45)
            categories=detection.get('categories',[detection['mode']])
            mode=route(categories)
            st.info('Detected: '+', '.join(categories)+' · '+detection['confidence']+' confidence. '+detection['reason'])
            for note in detection.get('notes',[]):st.caption(note)
        else:
            categories=selected
            mode=route(categories)
        st.caption(guidance(categories))
        if any(c in categories for c in ['Sports','Basketball','Soccer','Music','Gaming','Movies','Drama shows']) and mode!='Sports':
            st.caption('These types guide local transcript analysis. Visual action and musical phrase completion are not automatically verified; review the boundaries.')
    with st.container(key='setup-output'):
        st.subheader('Clip preferences')
        st.caption(PROFILES[mode]['description'])
        want_minimum=st.checkbox('Set a minimum clip target',value=bool(previous.get('min_clips')))
        min_clips=int(st.number_input('Minimum clips to aim for',min_value=1,value=max(1,int(previous.get('min_clips') or 3)),step=1)) if want_minimum else None
        st.caption('No maximum clip count. All suitable, non-overlapping clips are returned within your coverage setting. A minimum is a target, not a reason to add weak clips.')
        portrait=st.toggle('Vertical video · 9:16',value=previous.get('portrait',False))
        shorts_editor=st.toggle('Edit speech into tighter Shorts',value=previous.get('shorts_editor',True),disabled=mode=='Sports') and mode!='Sports'
        if shorts_editor:st.caption('Finds a strong opening, removes unnecessary phrases, and checks the ending locally. Uses the larger local editor in both processing modes. Reuses your transcript; other versions are created on request.')
        st.caption('Portrait interviews default to automatic framing: a tighter person crop when suitable, otherwise the full picture over blurred video. Adjust the layout when reviewing.')
        with st.expander('Advanced settings · duration, coverage & models'):
            editor_default=previous.get('editor_model') if previous.get('editor_model') in CHOICES else preferred_editor()
            editor_model=st.selectbox('AI editor',CHOICES,index=CHOICES.index(editor_default),format_func=lambda key:LABELS[key],disabled=mode=='Sports')
            if mode!='Sports':st.caption('Runs on this Mac. Qwen3.5 is available to compare; Qwen3 remains recommended after our saved-video checks. Changing editors reuses speech transcription and creates separate editing results.')
            minimum,maximum=st.slider('Preferred duration (seconds)',5,180,(previous['minimum'],previous['maximum']) if previous.get('mode')==mode else PROFILES[mode]['lengths'],step=5,key='duration-'+mode)
            st.caption('Complete interviews can be shorter. Sports drafts may extend for context. Suggestions do not overlap.')
            coverage=st.slider('Maximum share of the source to keep (%)',10,100,int((previous.get('coverage',.35 if mode=='Sports' else 1.0) if previous.get('mode')==mode else (.35 if mode=='Sports' else 1.0))*100),step=5) / 100
            st.caption('100% permits every distinct topic; clips still cannot overlap. This is a ceiling, not a target.')
            semantic=st.checkbox('Review meaning with local AI',value=mode!='Sports',disabled=True)
            if quality=='Higher quality' and mode!='Sports':st.caption('Only topics that pass completeness review are included. The result may contain fewer clips than requested.')
            vision=st.checkbox('Experimental football frame review',value=previous.get('vision',True),disabled=mode!='Sports')
            windows=st.slider('Event windows to inspect',1,12,previous.get('windows',6) if previous.get('sports_discovery_version')==3 else 6,disabled=mode!='Sports' or not vision)
            scenes=st.checkbox('Use scene detection for sports',value=previous.get('scenes',True),disabled=mode!='Sports')
            speakers=st.checkbox('Detect speaker changes',value=previous.get('speakers',False) and (SPEAKERS/'.ready').exists(),disabled=not (SPEAKERS/'.ready').exists() or mode=='Sports')
            alignment=st.checkbox('Precise word alignment',value=previous.get('alignment',False) and (ROOT/'models/alignment/.ready').exists(),disabled=not (ROOT/'models/alignment/.ready').exists())
            if not (SPEAKERS/'.ready').exists():st.caption('Speaker detection needs a one-time gated model download. See the version report for setup status.')
            if not (ROOT/'models/alignment/.ready').exists():st.caption('Word alignment is unavailable until its optional dependencies and model are installed.')
            st.caption('Football vision review may take several minutes per window. All drafts need your review.')
    transcript_path=folder/'transcript.json'
    sentences=json.loads(transcript_path.read_text()).get('sentences',[]) if transcript_path.exists() else []
    if mode!='Sports' and football_hint(project['title'],sentences) and not interview_content(project['title'],sentences):st.warning('For on-field highlights, Sports mode reviews action. Interview mode follows the conversation.')
    if mode=='Sports' and interview_content(project['title'],sentences):st.info('For a sports interview, Interview mode is usually the better fit.')
    settings=dict(resource_defaults=1,shorts_editor=shorts_editor,categories=categories,category_selection=selected,auto_mode=automatic,video_type=detection,coverage=coverage,mode=mode,minimum=minimum,maximum=maximum,min_clips=min_clips,portrait=portrait,semantic=semantic,vision=vision,windows=windows,quality=quality,scenes=scenes,speakers=speakers,alignment=alignment,sports_discovery_version=3)
    if mode!='Sports':settings['editor_model']=editor_model
    from project_store import write,read
    if read(folder/'ui-settings.json',{})!=settings:write(folder/'ui-settings.json',settings)
    st.caption(f'Estimated processing: about {clock(estimate_seconds(project,settings))}. Actual time varies with your Mac and video.')
    ready=((TURBO/'.ready').exists() if quality=='Higher quality' else (SPEECH/'model.bin').exists()) and (not semantic or mode=='Sports' or installed(editor_model)) and (mode!='Sports' or not vision or ((VISION4 if quality=='Higher quality' else VISION)/'.ready').exists())
    if not ready:st.error('A required model is missing. Run Download Models.command first.')
    a,b=st.columns([1,2])
    if a.button('← Change video'):go('source')
    if b.button('Find my clips →',type='primary',disabled=not ready):
        st.session_state.settings=settings;(folder/'ui-settings.json').write_text(json.dumps(settings));go('processing')
    if mode=='Interview' and st.button('Compare the same moment'):
        st.session_state.settings=settings;go('compare')
    existing=analysis_path(project,settings)
    if existing.exists() and st.button('Open previous results for these settings'):
        st.session_state.settings=settings;st.session_state.result_path=str(existing);go('complete')
    st.stop()

settings=st.session_state.settings
if page=='compare':
    from comparison_ui import show
    show(project,settings,go)
if page=='processing':
    st.title('Finding the good parts.')
    st.write('Finding clear openings, complete moments and a worthwhile payoff.')
    st.caption('Selection uses local editing estimates, not a prediction of views or a live trend feed.')
    st.caption('Large-model tasks run one at a time to protect memory. If another video is processing, this job may wait its turn.')
    try:
        key=hashlib.sha256(json.dumps([project,settings],sort_keys=True).encode()).hexdigest()[:20]
        result=run_job(key,lambda update:analyze(project,settings,update),estimate_seconds(project,settings))
        st.session_state.result_path=result;go('complete')
    except Exception as error:
        st.error(f'Processing stopped: {error}')
        st.caption('Your video and completed transcript are saved. You can retry.')
        if st.button('Back to settings'):go('settings')
    st.stop()

path=Path(st.session_state.result_path);candidates=json.loads(path.read_text())
if page=='complete':
    st.markdown('<div class="eyebrow">FIRST CUT, FINISHED</div>',unsafe_allow_html=True)
    st.title('Your moments are ready.' if candidates else 'No clear matches this time.')
    st.progress(1.,text='100% · Analysis complete')
    a,b,c=st.columns(3)
    from edit_timeline import edited_duration
    a.metric('Suggested clips',len(candidates));b.metric('Selected footage',clock(sum(edited_duration(x) for x in candidates)));c.metric('Style',settings['mode'])
    if settings['mode']=='Sports':
        from sports_report_ui import show_report
        show_report(path)
    if settings['mode']!='Sports' and path.with_suffix('.diagnostics.json').exists():
        report=json.loads(path.with_suffix('.diagnostics.json').read_text())
        with st.expander('Why these clips?'):
            st.write(f"Reviewed {report.get('drafts',0)} topics; kept {report.get('kept',0)}.")
            if report.get('exclusions'):st.dataframe(report['exclusions'],hide_index=True,use_container_width=True)
            if report.get('editorial_failures'):
                st.write('These moments did not produce a verified edit. Their original footage is available for review.')
                for n,failure in enumerate(report['editorial_failures']):
                    with st.expander(f"Original moment {n+1} · {failure['start']:.1f}s–{failure['end']:.1f}s"):
                        st.caption(failure['reason'])
                        st.write(failure.get('text',''))
                        if st.checkbox('Watch original moment',key='failed-edit-'+str(path)+str(n)):
                            st.video(str(source),start_time=float(failure['start']),end_time=float(failure['end']))
            st.download_button('Download selection report',json.dumps(report,indent=2),'selection-report.json','application/json')
    target=settings.get('min_clips')
    if target and len(candidates)<target:st.info(f'Found {len(candidates)} suitable clips; your minimum target was {target}. Quality, overlap, source coverage, or the amount of usable content prevented reaching it. Increase coverage or review the selection report; weak clips were not added to fill the target.')
    elif target:st.success(f'Minimum target reached: {len(candidates)} clips found (target {target}).')
    st.write('Open your collection, then choose a clip to preview and edit. Clips are rendered only when you open them.')
    if candidates and st.button('Open my clips →',type='primary'):go('results')
    if not candidates:st.info('No topics passed within these settings. Inspect the selection report, increase the maximum duration, or use Balanced with manual review.')
    if st.button('Adjust settings'):go('settings')
    st.stop()

if page=='results':
    from project_store import read
    report_words=read(transcript_file(folder,settings),{}).get('words',[])
    st.markdown('<div class="eyebrow">CLIP COLLECTION</div>',unsafe_allow_html=True)
    st.title('Your moments.')
    from clip_usage import is_used
    used_count=sum(is_used(folder,path,c) for c in candidates)
    a,b,c=st.columns(3)
    a.metric('Clips',len(candidates));b.metric('Ready to use',len(candidates)-used_count);c.metric('Used',used_count)
    show_used=st.radio('Show clips',['All','Unused','Used'],horizontal=True)
    clip_search=st.text_input('Search clips',placeholder='Find a title or spoken phrase…').strip().lower()
    if st.button('Combine saved clips into a video'):go('combine')
    if st.button('← Overview'):go('complete')
    visible=0
    for i,c in enumerate(candidates):
        used=is_used(folder,path,c)
        if show_used=='Unused' and used or show_used=='Used' and not used:continue
        if clip_search and clip_search not in (c['title']+' '+c['text']).lower():continue
        visible+=1
        with st.container(border=True):
            left,right=st.columns([4,1])
            from edit_timeline import edited_duration
            left.caption(f"CLIP {i+1:02} · {clock(edited_duration(c))} · {'Transcript reviewed' if c['passed'] else 'Needs review'}")
            from clip_usage import checkbox as usage_checkbox
            with right:usage_checkbox(folder,path,c,'list')
            left.subheader(c['title'])
            if c.get('audience_quality'):left.caption(c['audience_quality']['reason'])
            left.write(c['text'][:150]+('…' if len(c['text'])>150 else ''))
            with left.expander('Suggested edit assessment'):
                from final_package import editorial_assessment
                from edit_timeline import ranges_for,remap_words
                st.dataframe(editorial_assessment(c,remap_words(report_words,ranges_for(c)),ranges_for(c),settings['mode']),hide_index=True,width='stretch')
                st.caption('Suggested edit only; saved manual changes and alternate versions are assessed when opened. Unknown dimensions remain unscored.')
            if right.button('Review clip →',key=f'open-{i}'):
                st.session_state.clip_index=i;go('editor')
    if not visible:st.info('No clips match these filters.')
    st.stop()

if page=='editor':
    if st.button('← All clips'):go('results')
    index=st.session_state.clip_index;candidate=dict(candidates[index]);usage_candidate=dict(candidate)
    st.caption(f'CLIP {index+1:02} OF {len(candidates):02}')
    heading=st.empty();preview=st.container()
    edit_tab,look_tab,post_tab,advanced_tab=st.tabs(['Edit','Look','Social media','Advanced'],key='clip-editor-tab-'+str(path)+'-'+str(index),on_change='rerun')
    transcript_path=transcript_file(folder,settings);transcript=json.loads(transcript_path.read_text())
    base_edit_id=f"{candidate['start']}-{candidate['end']}"
    from shorts_ui import choose_edit
    with edit_tab:candidate,variant=choose_edit(folder,path,candidate,transcript,settings)
    candidate=dict(candidate)
    edits_path=path.with_suffix('.edits.json');edits=json.loads(edits_path.read_text()) if edits_path.exists() else {}
    edit_id=base_edit_id+(':'+variant if variant!='Original moment' else '')
    if edit_id in edits:
        manual_start,manual_end=edits[edit_id]
        candidate.update(passed=False,text=' '.join(w['text'] for w in transcript['words'] if w['end']>manual_start and w['start']<manual_end),reason='Manual source boundaries need review; automatic checks apply to the suggested edit.')
        for key in ('audience_review','audience_quality'):candidate.pop(key,None)
    original_title=candidate['title']
    if settings['mode']=='Interview' and not candidate.get('edit_plan'):
        from interview_integrity import topic_title
        candidate['title']=topic_title(candidate['text'])
    heading.title(candidate['title'])
    start,end=edits.get(edit_id,[candidate['start'],candidate['end']])
    active_plan=candidate.get('edit_plan') if edit_id not in edits else None
    render_ranges=active_plan['ranges'] if active_plan else None
    with edit_tab:
        from clip_usage import checkbox as usage_checkbox
        usage_checkbox(folder,path,usage_candidate,'editor')
        st.caption('Transcript review only; listen and review visual content before posting.' if candidate['passed'] else 'Draft · Review the opening and ending before sharing.')
        if candidate.get('edit_plan'):st.caption('Applying manual start/end boundaries exports a continuous source range. Restore suggested boundaries to return to this edited version.')
        from boundary_editor import editor as boundary_editor
        changed=boundary_editor(source,total,start,end,transcript,str(path)+edit_id)
        reset=st.button('Restore suggested boundaries',key='restore-'+str(path)+edit_id)
        if changed is not None or reset:
            s,e=(candidate['start'],candidate['end']) if reset else changed
            if not 0<=s<e<=total:st.error('The end must follow the start, within the source video. The previous cut is kept.')
            else:
                from project_store import write
                if reset:edits.pop(edit_id,None)
                else:edits[edit_id]=[s,e]
                write(edits_path,edits);st.rerun()
        for other in candidates:
            oid=f"{other['start']}-{other['end']}";s,e=edits.get(oid,[other['start'],other['end']])
            from modes import intersection
            current=dict(candidate,start=start,end=end,edit_plan=active_plan or {})
            if oid!=base_edit_id and intersection(current,dict(other,start=s,end=e))>0:st.warning('Your cut overlaps another suggestion.');break
    from polish_ui import caption_editor
    with look_tab:export_words=caption_editor(folder,transcript_path,transcript,start,end,ranges=render_ranges)
    from presentation import LAYOUTS,normalize_layout,default_layout
    from project_store import read,write
    style_path=path.with_suffix('.styles.json');styles=read(style_path,{})
    style=styles.get(edit_id,dict(layout=default_layout(settings.get('portrait',False)),burn=True,position=.5,second=.75,
        pacing='Off' if settings['mode']=='Sports' else 'Subtle',conversation='Off' if settings['mode']=='Sports' else 'Automatic',
        semantic_emphasis=True,emphasis_style='Bold',packaging_version=1))
    if settings['mode']=='Interview' and not active_plan and style.get('title')==original_title:style=dict(style,title=candidate['title'])
    style=dict(style,layout=normalize_layout(style['layout']))
    render_start,render_end=start,end
    if style.get('trim_edges') and not render_ranges:
        from polish import silent_edges
        @st.cache_data(show_spinner=False)
        def edge_times(file,mtime,a,b,words):return silent_edges(file,a,b,words)
        render_start,render_end=edge_times(str(source),source.stat().st_mtime_ns,start,end,transcript['words'])
        with edit_tab:st.caption(f'Quiet-edge adjustment: {start:.2f}–{end:.2f}s → {render_start:.2f}–{render_end:.2f}s. Saved boundaries are unchanged.')
    final_ranges=render_ranges or [dict(start=render_start,end=render_end)]
    from final_package import get_package
    final_candidate=dict(candidate,edit_plan=active_plan or {})
    package=get_package(folder,source,final_candidate,export_words,final_ranges,settings['mode'],read(folder/'confirmed-names.json',[]))
    if 'title' not in style:style['title']=package['hook']
    from edit_timeline import remap_words,timeline_duration
    final_words=remap_words(export_words,final_ranges)
    import packaging_ui
    # An already-running server can retain older posting controls.
    if getattr(packaging_ui,'POST_FORM_API',0)<3:
        import importlib
        importlib.reload(packaging_ui)
    from packaging_ui import look_form,post_form,advanced
    with look_tab:
        updated,apply=look_form(style,package,final_words,settings['mode'],str(path)+edit_id,ranged=bool(render_ranges))
        if apply:styles[edit_id]=updated;write(style_path,styles);st.rerun()
    render_style=dict(style)
    if style.get('packaging_version'):
        render_style['_emphasis']=package['emphasis']
        if style['layout']==LAYOUTS[4]:
            from visual_pacing import inspect_scene,plan_camera
            try:
                if settings['mode']=='Sports':
                    import av
                    with av.open(str(source)) as media:scene=dict(width=media.streams.video[0].width,height=media.streams.video[0].height,samples=[])
                else:scene=inspect_scene(source,final_ranges)
                render_style['_visual_plan']=plan_camera(scene,final_words,final_ranges,package,style,settings['mode'])
            except Exception as error:
                with look_tab:st.warning('Automatic camera planning was unavailable; using full picture. '+str(error))
                render_style['layout']=LAYOUTS[1]
    render_signature=[digest,source.stat().st_mtime_ns,transcript_path.stat().st_mtime_ns,render_start,render_end,render_style,export_words]
    render_signature+=([final_ranges,package['fingerprint'],'v517'] if style.get('packaging_version') else ([render_ranges,'v516'] if render_ranges else ['v55']))
    render_id=hashlib.sha256(json.dumps(render_signature).encode()).hexdigest()[:24]
    manifest=folder/f'render-{render_id}.json';video=None;download_area=None
    try:
        saved=read(manifest,[])
        if len(saved)==2 and all(Path(p).is_file() for p in saved):video,captions=map(Path,saved)
        else:
            def render(update):
                update(.05,'Rendering the selected clip')
                return export_clip(source,render_start,render_end,export_words,settings.get('portrait',False),presentation=render_style,ranges=render_ranges)
            video,captions=run_job('render-'+render_id,render,max(15,timeline_duration(final_ranges)*2))
            write(manifest,[str(video),str(captions)])
        with preview:
            st.video(str(video));st.caption(f'{clock(timeline_duration(final_ranges))} · Extracted clip starts at 0:00')
            download_area=st.container()
        from combined_video import register_clip
        finished_clip=register_clip(folder,video,captions,style.get('title') or candidate['title'],project['title'])
        finished_clip['duration']=timeline_duration(final_ranges)
        with edit_tab:
            if st.button('Add to combined video'):
                from combined_video_ui import add_to_draft
                add_to_draft(ROOT,finished_clip);go('combine')
        with look_tab:
            decision=read(video.with_suffix('.framing.json'),{})
            if decision.get('reason'):st.caption(decision['reason'])
            for warning in decision.get('warnings',[]):st.warning(warning)
    except Exception as error:
        with preview:st.error(f'Could not render the clip: {error}')
    with post_tab:
        posting_copy=post_form(folder,package,settings,active=post_tab.open)
        if posting_copy.get('title'):
            from social_copy import TAG
            heading.title(TAG.sub('',posting_copy['title']).strip())
        if video is not None and video.is_file():
            if download_area is not None:
                from download_names import clip_filename
                download_title=posting_copy.get('title') or candidate['title']
                with download_area:
                    a,b=st.columns(2)
                    a.download_button('↓ Save video',video.read_bytes(),clip_filename(download_title),'video/mp4',type='primary')
                    if captions.read_text().strip():b.download_button('↓ Save subtitles',captions.read_bytes(),clip_filename(download_title,'srt'),'text/plain')
                    st.caption('Download name: '+clip_filename(download_title))
            from clip_thumbnails import show as show_thumbnails
            show_thumbnails(video,folder,style.get('title') or package['hook'])
            from social_ui import composer
            composer(folder,path,final_candidate,video,render_id,posting_copy)
    review_details=dict(quality=settings.get('quality','Balanced'),start=start,end=end,
        visual_pacing=style.get('pacing','Off'),entities=package['entities'],final_transcript=package['final_transcript'])
    if render_ranges:review_details.update(variant=variant,ranges=render_ranges)
    if active_plan:
        original=active_plan['source_moment'];review_details['removed_fraction']=max(0,1-timeline_duration(final_ranges)/(original['end']-original['start']))
        from interview_integrity import question
        review_details['answer_only']=question(original['text'].split('?')[0]+'?') and not question(package['sentences'][0]['text']) if '?' in original['text'] and package['sentences'] else None
    with edit_tab:review_form(folder,str(path),review_details)
    with advanced_tab:
        advanced(package,final_candidate,final_words,final_ranges)
        from audience_quality import show_report as show_audience_report
        show_audience_report(final_candidate)
        review_history(folder)
        with st.expander('Transcript & review notes'):
            st.write(package['final_transcript']);st.write(candidate.get('reason','Original discovered moment.'))
            if candidate.get('concern'):st.warning(candidate['concern'])
            for note in candidate.get('boundary_notes',[]):st.caption(note)
            if candidate.get('storyboard') and Path(candidate['storyboard']).exists():st.image(candidate['storyboard'])
        with st.expander('Watch surrounding context'):
            st.video(str(source),start_time=float(max(0,start-5)),end_time=float(min(total,end+5)))
        with st.expander('Full transcript'):
            for sentence in transcript['sentences']:st.write(f"{sentence['start']:.1f}s · {sentence.get('speaker') or 'Speech'} · {sentence['text']}")
            st.download_button('Save transcript',transcript_path.read_bytes(),'transcript.json','application/json')
