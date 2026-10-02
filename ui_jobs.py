"""Reconnectable background jobs with live elapsed time and estimated remaining time."""
import queue
import time
from concurrent.futures import ThreadPoolExecutor
import streamlit as st


def clock(seconds):
    seconds=max(0,round(seconds))
    return f'{seconds//60}m {seconds%60:02d}s' if seconds>=60 else f'{seconds}s'


def remaining_text(elapsed,estimate):
    if elapsed>=estimate:return 'Taking longer than estimated · still working'
    return f'About {clock(estimate-elapsed)} remaining · estimate'


def run_job(key,work,estimate):
    state_key='job-'+key
    if state_key not in st.session_state:
        events=queue.Queue();executor=ThreadPoolExecutor(max_workers=1)
        def guarded():
            from resource_limits import HEAVY_JOB_LOCK
            import fcntl
            from engine import ROOT
            events.put((0.,'Waiting for the other local job to finish'))
            with HEAVY_JOB_LOCK:
                with (ROOT/'work/heavy-job.lock').open('a') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX)
                    return work(lambda p,label:events.put((p,label)))
        future=executor.submit(guarded)
        st.session_state[state_key]={'future':future,'events':events,'executor':executor,'start':time.monotonic(),'p':0.,'label':'Starting','estimate':estimate}
    job=st.session_state[state_key]
    with st.container(key='job-progress'):
        st.markdown('<div class="eyebrow">PROCESSING YOUR VIDEO</div>',unsafe_allow_html=True)
        bar=st.progress(0);label=st.empty();timing=st.empty()
    while True:
        while True:
            try:
                p,message=job['events'].get_nowait()
                job['p']=max(job['p'],min(.99,p));job['label']=message
            except queue.Empty:break
        elapsed=time.monotonic()-job['start']
        bar.progress(job['p'],text=f"{int(job['p']*100)}% · {job['label']}")
        label.caption('Keep this app open. Your video stays on this Mac.')
        timing.caption(f"Elapsed {clock(elapsed)} · {remaining_text(elapsed,job['estimate'])}")
        if job['future'].done():break
        time.sleep(.5)
    try:
        result=job['future'].result()
        bar.progress(1.,text='100% · Complete')
        return result
    finally:
        job['executor'].shutdown(wait=False)
        del st.session_state[state_key]
