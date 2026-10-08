"""Manage waiting videos and inspect live progress without blocking navigation."""
import time
from pathlib import Path
import streamlit as st
from clip_queue import QueueStore, ensure_runner, runner_alive
from project_store import library, read
from ui_jobs import clock
QUEUE_FORM_API = 2


def add_project(root, project, settings, export_clips=True):
    item, added = QueueStore(root).add(project, settings, export_clips)
    ensure_runner(root)
    return item, added


def show(root, go):
    root = Path(root)
    store = QueueStore(root)
    st.markdown('<div class="eyebrow">WORK WHILE YOU STEP AWAY</div>', unsafe_allow_html=True)
    st.title('Video queue')
    st.write('Line up videos. We’ll find their clips and export them, one video at a time.')
    st.caption('You can close the browser tab. For lid-closed clipping, turn on the Amphetamine option below, keep your charger connected and leave the Mac on a hard surface with room for airflow. Normal queues prevent idle sleep; closing the lid can still interrupt them. Reopening the app resumes saved work with normal lid-open processing.')
    entries = library(root/'data')
    configured = {}
    for entry in entries:
        project = entry['project']
        settings = read(Path(project['folder'])/'ui-settings.json', {}) or (entry['runs'][0]['settings'] if entry['runs'] else {})
        if entry['available'] and settings:
            configured[project['folder']] = (project, settings)
    with st.expander('Add saved videos', expanded=True):
        if configured:
            with st.form('queue-add-videos'):
                selected = st.multiselect('Videos to add', list(configured), format_func=lambda key: configured[key][0]['title'])
                export = st.checkbox('Export all selected clips automatically', value=True)
                st.caption('Uses each project’s saved settings. Exports suggested clips with default captions and framing; your saved manual edits stay available. Nothing is posted automatically.')
                submitted = st.form_submit_button('Add videos to queue')
            if submitted:
                added, duplicates = 0, 0
                for key in selected:
                    try:
                        _, fresh = add_project(root, *configured[key], export)
                        added += int(fresh); duplicates += int(not fresh)
                    except (OSError, ValueError) as error:
                        st.error(str(error))
                if added:st.success(f'Added {added} '+('video' if added==1 else 'videos')+' to the queue.')
                if duplicates:st.info(f'{duplicates} videos were already waiting or processing with these settings.')
                if not selected:st.info('Choose at least one video to add.')
        else:
            st.info('Import a video and choose its clip settings first, then use Add to queue on the setup screen.')
        if st.button('Import another video'):
            go('source')
    live_queue(root, go)


@st.fragment(run_every=2)
def live_queue(root, go):
    from queue_power import APP_STORE, capability, status
    store = QueueStore(root)
    items = store.items()
    waiting = [item for item in items if item['state']=='queued']
    current = next((item for item in items if item['state']=='running'), None)
    enabled = store.enabled()
    alive = runner_alive(root)
    if enabled and not alive:
        ensure_runner(root)
    a, b, c = st.columns(3)
    a.metric('Waiting videos', len(waiting))
    b.metric('Completed videos', sum(item['state']=='done' for item in items))
    c.metric('Needs attention', sum(item['state']=='failed' for item in items))
    power = status(root)
    if power.get('phase') == 'active':
        st.success(power['message'])
    elif power.get('phase') == 'starting' and alive:
        st.info(power['message'])
    elif power.get('phase') == 'error':
        st.warning(power['message'])
    closed_lid = False
    ready = True
    if not enabled and not current and waiting:
        closed_lid = st.checkbox('Allow lid-closed processing with Amphetamine', key='queue-closed-lid')
        if closed_lid:
            ready, reason = capability()
            st.caption(reason)
            st.caption('Finish Amphetamine’s closed-display warning and any macOS Automation prompts before closing the lid. The session ends when the queue finishes or pauses, with a 24-hour limit. If you unplug the charger or end the session, remaining videos pause after the current one. End any existing Amphetamine session before starting this mode.')
            st.link_button('Amphetamine · free in the Mac App Store', APP_STORE)
    if enabled:
        st.info('Processing the queue.' if current else 'Waiting for the current local job to finish.' if alive else 'Starting the queue…')
        if st.button('Pause after this video' if current else 'Pause queue', key='queue-pause'):
            store.set_enabled(False); st.rerun()
    elif current:
        st.info('The current video will finish, then the queue will pause.')
        if st.button('Continue queue', key='queue-start'):
            store.set_enabled(True); ensure_runner(root); st.rerun()
    elif waiting:
        st.info('Ready when you are. Start the queue to process these videos in order.' if ready else 'Connect your charger to start this queue with the lid closed.')
        if st.button('Start queue', key='queue-start', type='primary', disabled=not ready):
            store.set_enabled(True)
            if closed_lid:ensure_runner(root, closed_lid=True)
            else:ensure_runner(root)
            st.rerun()
    else:
        st.info('No videos waiting. Add saved videos above, or add a video from project setup.')
    if current:
        with st.container(border=True):
            st.subheader('Now processing · '+current['project']['title'])
            st.progress(min(.99, max(0., current['progress'])), text=f"{int(current['progress']*100)}% · {current['label']}")
            elapsed = time.time()-current['started'] if current['started'] else 0
            st.caption('Elapsed '+clock(elapsed))
            if current['estimate']:
                st.caption('Analysis estimate: about '+clock(current['estimate'])+(' · export time is additional.' if current['export_clips'] else '. Actual time varies.'))
    if waiting:st.subheader('Up next')
    for index, item in enumerate(waiting):
        with st.container(border=True):
            st.write(f"{index+1}. {item['project']['title']}")
            settings = item['settings']
            mode = 'Automatic' if settings.get('watch_auto_type') else settings['mode']
            st.caption(f"{mode} · {settings.get('quality','Balanced')} · {settings['minimum']}–{settings['maximum']} seconds · "+('Find and export clips' if item['export_clips'] else 'Find clips'))
            up, down, remove = st.columns(3)
            if up.button('Move up', key='queue-up-'+item['id'], disabled=index==0):
                store.move(item['id'], -1); st.rerun()
            if down.button('Move down', key='queue-down-'+item['id'], disabled=index==len(waiting)-1):
                store.move(item['id'], 1); st.rerun()
            if remove.button('Remove from queue', key='queue-remove-'+item['id']):
                store.remove(item['id']); st.rerun()
    history = [item for item in items if item['state'] in ('done','failed','skipped')]
    if history:
        st.subheader('Finished and needs attention')
        for item in reversed(history):
            with st.container(border=True):
                st.write(item['project']['title'])
                if item['state']=='skipped':
                    st.info('Skipped · '+item['error'])
                elif item['state']=='failed':
                    st.error('Needs attention · '+item['error'])
                    if st.button('Retry this video', key='queue-retry-'+item['id']):
                        try:
                            store.retry(item['id']); ensure_runner(root); st.rerun()
                        except ValueError as error:
                            st.error(str(error))
                else:
                    count = len(read(item['result'], [])) if item['result'] else 0
                    exported = sum(Path(clip['video']).is_file() for clip in item['exports'])
                    st.success(f'Complete · {count} '+('clip' if count==1 else 'clips')+' selected'+
                               (f' · {exported} '+('clip' if exported==1 else 'clips')+' exported' if item['export_clips'] else ''))
                if item['result'] and Path(item['result']).is_file():
                    if st.button('Open clips', key='queue-open-'+item['id']):
                        st.session_state.project=item['project']; st.session_state.settings=item['settings']
                        st.session_state.result_path=item['result']; go('results')
