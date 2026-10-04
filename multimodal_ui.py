"""Inspect source-timed curation evidence without triggering inference on view."""
import json
from pathlib import Path
import streamlit as st
from multimodal_curation import fingerprint,valid_priority,curate


def show(candidate):
    data=candidate.get('multimodal_curation')
    if not data:return
    with st.expander('Speech, visuals & sound evidence'):
        if not valid_priority(candidate):
            st.caption('This evidence belongs to an earlier cut or source file. Review the current moment again.');return
        st.write('Editing rules: '+data['genre'])
        for failure in data.get('failures',[]):st.warning(failure)
        st.caption('Supporting signals can nudge priority. They never override source integrity, complete endings or the interview question limit.')
        st.dataframe([dict(Signal=k.capitalize(),Estimate=round(v,3) if v is not None else None,Weight=data['weights'][k])
                      for k,v in data['signals'].items()],hide_index=True,width='stretch')
        st.caption('Unknown signals stay blank. Estimates are editing cues, not probabilities of views. '+data['speech_basis'])
        sound=data['sound']
        if sound.get('available'):
            st.write(f"Sound: {sound['window_count']} retained windows · {sound['speech_fraction']:.0%} with speech · {sound['reaction_fraction']:.0%} with a possible reaction.")
            if sound['events']:
                st.dataframe([dict(Source_start=e['start'],Source_end=e['end'],Sound=e['label'],Model_score=e['score']) for e in sound['events']],hide_index=True,width='stretch')
            else:st.caption('No reaction sound reached the display threshold. A quiet answer can still be valuable.')
        else:st.caption('Sound: '+sound['status'])
        visual=data['visual']
        st.caption(f"Visual scan: {visual['motion_samples']} retained motion samples · {visual['camera_changes']} camera changes. Neither proves a completed action.")
        if visual['samples']:
            for frame,column in zip(visual['samples'],st.columns(len(visual['samples']))):
                with column:
                    if not Path(frame['path']).is_file():
                        st.caption('The saved sample image is missing. Review this moment again.');continue
                    st.image(frame['path'],caption=f"Source {frame['time']:.2f}s")
                    if frame.get('status')=='Observed':st.write(frame['description']);st.caption(frame['shot'].replace('_',' '))
                    else:st.caption('This sample could not be interpreted.')
                    for note in frame.get('uncertainty',[]):st.caption(note)
        else:st.caption('Learned visual review was not available for this moment. The automatic review covers only the selected number of moments.')
        st.caption(data['visual_model'])
        for note in data['limitations']:st.caption(note)
        st.download_button('Download curation evidence',json.dumps(data,indent=2),'curation-evidence.json','application/json',key='curation-report-'+fingerprint(candidate))


def review_form(project,transcript,candidate,settings):
    """Review an existing final cut on demand without applying any edit."""
    from multimodal_curation import VERSION
    source=Path(project['source']);identity=fingerprint(candidate)+str(source.stat().st_mtime_ns)
    local=st.session_state.get('curation-'+identity)
    if local:show(local)
    else:show(candidate)
    if st.button('Review this moment with speech, visuals & sound',key='curation-button-'+identity,
                 help='Uses the saved transcript and local models. Keeps the current cut and posting text.'):
        from ui_jobs import run_job
        options=dict(settings,multimodal_curation=True,curation_windows=1)
        try:
            reviewed,report=run_job('curation-'+VERSION+identity,lambda update:curate(project,transcript,[candidate],options,update),90)
            st.session_state['curation-'+identity]=reviewed[0]
            for failure in report['failures']:st.warning(failure)
            st.rerun()
        except Exception as error:st.error('Could not review this moment: '+str(error).splitlines()[-1][:250])
