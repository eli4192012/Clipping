import hashlib
import json
from pathlib import Path
import streamlit as st
from comparison import compare
from review_ui import review_form,review_history
from ui_jobs import run_job
from upgrades import EDITOR4
from engine import EDITOR

def show(project,settings,go):
    st.title('Same moment. Two editors.')
    st.write('Both reviewers receive the same transcript and the same interview exchange. This compares editing decisions; automatic topic selection is tested separately in Find my clips.')
    if st.button('← Back to settings'):go('settings')
    st.caption('Shared transcript: '+settings.get('quality','Balanced')+'. Change processing quality in settings to choose a different shared transcript.')
    with st.form('compare-target'):
        target=st.number_input('Target time in the original video (seconds)',min_value=0.,max_value=float(project['duration']),value=min(40.,float(project['duration'])),step=.5)
        st.caption('Choose a time inside the question or answer you want to compare. Both reviewers must keep that question. If there is no matching exchange, no substitute topic will be shown.')
        requested=st.form_submit_button('Compare this moment',disabled=not ((EDITOR/'.ready').exists() and (EDITOR4/'.ready').exists()))
    if requested:st.session_state.comparison_pending=target
    if 'comparison_pending' in st.session_state:
        pending=st.session_state.comparison_pending
        try:
            key=hashlib.sha256(json.dumps([project,settings,pending],sort_keys=True).encode()).hexdigest()[:16]
            result=run_job('compare-'+key,lambda update:compare(project,settings,pending,update),240)
            st.session_state.comparison_result=result
        except Exception as error:st.error(str(error))
        finally:st.session_state.pop('comparison_pending',None)
    path=st.session_state.get('comparison_result')
    if path and Path(path).exists():
        report=json.loads(Path(path).read_text())
        if report['source']==project['source']:
            st.subheader(report['question'])
            st.caption(f"Target {report['target']:.1f}s · Shared {report['transcript_quality']} transcript · Saved comparison")
            for column,result in zip(st.columns(2),report['results']):
                with column:
                    c=result['candidate'];st.subheader(result['quality'])
                    st.caption(f"{c['start']:.2f}s → {c['end']:.2f}s · {c['end']-c['start']:.2f}s long")
                    st.video(result['video'])
                    st.download_button('Save this video',Path(result['video']).read_bytes(),Path(result['video']).name,'video/mp4',key=path+result['quality'])
                    st.write(c['reason'])
                    if c.get('concern'):st.warning(c['concern'])
                    with st.expander('Boundary notes'):
                        st.write(c['text'])
                        for note in c.get('boundary_notes',[]):st.caption(note)
                    review_form(project['folder'],path,dict(quality=result['quality'],start=c['start'],end=c['end'],video=result['video']))
            st.download_button('Download comparison report',Path(path).read_bytes(),'comparison.json','application/json')
    saved=sorted((Path(project['folder'])/'comparisons').glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True)
    if saved:
        with st.expander('Previous comparisons'):
            selected=st.selectbox('Saved comparison',saved,format_func=lambda p:f"{json.loads(p.read_text())['target']:.1f}s · {p.stem[:8]}")
            if st.button('Open comparison'):
                st.session_state.comparison_result=str(selected);st.rerun()
    review_history(project['folder'])
    st.stop()
