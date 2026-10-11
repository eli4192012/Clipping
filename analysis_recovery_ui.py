"""Recovery controls keep approved edits accessible while full work resumes."""
import streamlit as st
from pathlib import Path
from analysis_recovery import recover_checked_edits, resume_saved_analysis
from clip_queue import QueueStore


def show(root, project, settings, go):
    st.info('Your source video, saved transcript and completed edit decisions are kept. Resume with the same settings to reuse them. An unfinished edit may need another check.')
    try:
        recovery=recover_checked_edits(project,settings)
    except (OSError,ValueError,TypeError,KeyError) as error:
        from app_logging import log_exception
        log_exception('Recovery snapshot failed')
        st.warning(f'Could not open a recovery snapshot: {error}. Saved work has not been removed.')
        recovery=None
    if recovery:
        st.success(f"Recovered {recovery['recovered_edits']} checked edits; {recovery['kept']} distinct clips are available to review. Full analysis is unfinished.")
        if st.button('Open recovered clips',key='open-recovered-clips'):
            st.session_state.result_path=recovery['result'];go('results')
    active=[item for item in QueueStore(root).items() if item['state'] in ('queued','running')
            and Path(item['project']['folder']).resolve()==Path(project['folder']).resolve() and item['settings']==settings]
    if active:
        item=active[0]
        st.info('This run is already in the video queue with your original settings: '+item['label'])
    elif st.button('Resume saved work & export clips',type='primary',key='resume-saved-analysis'):
        try:resume_saved_analysis(root,project,settings)
        except (OSError,ValueError) as error:st.error(str(error))
        else:go('queue')
    if st.button('View video queue',key='recovery-queue'):go('queue')


def partial_notice(path, go):
    from project_store import read
    report=read(path.with_suffix('.diagnostics.json'),{})
    partial=isinstance(report,dict) and report.get('partial_analysis') is True
    if partial:
        st.warning('These are recovered, checked speech edits. Full analysis and any remaining visual/sound review are still unfinished. The final selection may change.')
        if st.button('View recovery progress in video queue',key='partial-analysis-queue'):go('queue')
    return partial
