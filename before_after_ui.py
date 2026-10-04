"""Play real before/after exports and save human preferences separately."""
import json
from pathlib import Path
import streamlit as st

from before_after import reports, build, directory, save_rating, CHOICES
from project_store import read
BEFORE_AFTER_FORM_API=2


def show(root, go):
    st.title('Before & after')
    st.write('Watch the same moment before and after the opening and ending reviews. Compare the idea, accuracy and finish as well as length.')
    if 'before_after_pending' in st.session_state:
        from ui_jobs import run_job
        spec=st.session_state.before_after_pending
        try:
            from before_after import identity
            report=run_job('before-after-'+identity(spec),lambda update:build(spec,update),180)
            st.session_state.before_after_selected=report['id']
            st.session_state['before-after-picker']=report['id']
        except Exception as error:
            st.error('Could not create the comparison: '+str(error).splitlines()[-1][:350])
        finally:st.session_state.pop('before_after_pending',None)
    items=reports(root)
    if not items:
        st.info('No comparisons yet. Open a saved clip and choose Compare before and after in Edit.')
        return
    if not st.checkbox('Show earlier comparison runs',value=False):
        latest={}
        for item in items:
            key=json.dumps([item['source']['path'],item['before']['ranges'],item['mode'],item.get('comparison_kind','Controlled trial')],sort_keys=True)
            latest.setdefault(key,item)
        items=list(latest.values())
    by_id={r['id']:r for r in items}
    selected=st.session_state.get('before_after_selected')
    selected=st.selectbox('Comparison',list(by_id),index=list(by_id).index(selected) if selected in by_id else 0,
                          format_func=lambda key:by_id[key]['name'],key='before-after-picker')
    st.session_state.before_after_selected=selected
    report=by_id[selected]
    st.caption(report['source_title']+' · '+report['mode']+' · '+report['editor'])
    st.caption(report['baseline_note'])
    if not report['available']:
        st.warning('This comparison’s source, transcript or media changed or is missing. The saved notes remain readable; create a fresh comparison from the clip.')
    for label,column in zip(('Before','After'),st.columns(2)):
        side=report[label.lower()]
        with column:
            st.subheader(label)
            st.caption(f"{side['duration']:.1f}s · {side['width']} × {side['height']}")
            if report['available']:st.video(side['video']['path'])
            st.write('Opening text: '+(side['opening_text'] or 'None'))
            st.write('Title: '+(side['posting'].get('title') or 'No checked posting title'))
            st.write('Description: '+(side['posting'].get('description') or 'No checked description'))
            st.caption('Last thought: “'+side['last_sentence']+'”')
            with st.expander(label+' transcript and source ranges'):
                st.write(side['final_transcript']);st.dataframe(side['ranges'],hide_index=True)
                if report['available']:
                    video=Path(side['video']['path']);captions=Path(side['captions']['path'])
                    st.download_button('Save '+label.lower()+' video',video.read_bytes(),video.name,'video/mp4',key=selected+label+'video')
                    st.download_button('Save '+label.lower()+' subtitles',captions.read_bytes(),captions.name,'text/plain',key=selected+label+'captions')
    st.subheader('What changed')
    before,after=report['before'],report['after']
    st.write(f"Duration: {before['duration']:.1f}s → {after['duration']:.1f}s. Opening text {'changed' if before['opening_text']!=after['opening_text'] else 'kept'}. Source ending {'trimmed' if before['ranges']!=after['ranges'] else 'kept'}.")
    for note in report['observations']:
        if 'Source accuracy problem:' in note or 'needs correction.' in note:st.warning(note)
        else:st.write(note)
    for stage in report['stages']:
        if stage['status']=='failed':st.warning(stage['name']+' failed. '+stage['error'])
    with st.expander('Accuracy and processing details'):
        st.caption('Source checks are local model estimates. Matched subtitles and unchanged source order do not prove a paraphrase is accurate.')
        for label in ('before','after'):
            side=report[label]
            st.write(label.capitalize()+': '+str(side['detected_questions'])+' detected questions · subtitles match the selected speech.')
            for warning in side['boundary_warnings']:st.warning(label.capitalize()+': '+warning)
        if report.get('ending_review'):st.json(report['ending_review']['source_check'])
        if report.get('opening_review'):st.json(report['opening_review']['source_check'])
        if after['posting'].get('source_check'):st.json(after['posting']['source_check'])
        st.dataframe([dict(Stage=s['name'],Seconds=s['seconds'],Result=s['status'],Cache='Reused' if s['cached'] else 'Fresh') for s in report['stages']],hide_index=True)
        st.caption('Seconds are measured for these stages on this Mac. Cache reads are not fresh inference times. Transcription and discovery were reused; this is not a whole-video speed test.')
    saved=read(directory(root)/'ratings'/(selected+'.json'),{})
    with st.form('comparison-rating-'+selected):
        preference=st.radio('Which version works better?',CHOICES,index=CHOICES.index(saved.get('choice','Not rated')),key='preference-'+selected)
        notes=st.text_area('Your notes',saved.get('notes',''),key='notes-'+selected)
        if st.form_submit_button('Save comparison review',disabled=not report['available']):
            try:save_rating(root,selected,preference,notes);st.success('Your comparison review is saved on this Mac.')
            except ValueError as error:st.error(str(error))
    st.download_button('Download comparison report',json.dumps(report,indent=2),'before-after.json','application/json',key='report-'+selected)
    st.caption('Viewing and rating do not apply edits, publish clips, or train the AI.')
