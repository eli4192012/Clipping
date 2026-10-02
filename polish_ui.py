"""Saved, reversible caption corrections for existing and new clips."""
import json
import streamlit as st
from polish import corrected_words,known_names,name_suggestions


def caption_editor(folder,transcript_path,transcript,start,end,ranges=None):
    path=transcript_path.with_suffix('.corrections.json')
    edits=json.loads(path.read_text()) if path.exists() else {}
    names_path=folder/'confirmed-names.json'
    confirmed=json.loads(names_path.read_text()) if names_path.exists() else []
    with st.expander('Check names & edit captions'):
        st.caption('Possible matches use names found in this transcript or your list. They are spelling hints, not verified identities. Listen before applying a correction. Original transcription and timing are preserved.')
        with st.form('names-'+str(folder)):
            text=st.text_area('Known names · one per line',value='\n'.join(confirmed))
            if st.form_submit_button('Save known names'):
                names_path.write_text(json.dumps([n.strip() for n in text.splitlines() if n.strip()]));st.rerun()
        names=known_names(' '.join(w['text'] for w in transcript['words']),confirmed)
        suggestions=name_suggestions(transcript['words'],names)
        selected=[i for i,w in enumerate(transcript['words']) if any(w['end']>r['start'] and w['start']<r['end'] for r in (ranges or [dict(start=start,end=end)]))]
        rows=[dict(word_id=str(i),seconds=round(transcript['words'][i]['start'],2),original=transcript['words'][i]['text'],caption=edits.get(str(i),transcript['words'][i]['text']),possible_name=suggestions.get(i,'')) for i in selected]
        if rows:
            with st.form('captions-'+str(path)+str(start)+str(end)):
                updated=st.data_editor(rows,disabled=['word_id','seconds','original','possible_name'],hide_index=True,use_container_width=True,num_rows='fixed',key='caption-rows-'+str(path)+str(start)+str(end))
                save=st.form_submit_button('Save caption corrections');reset=st.form_submit_button('Restore original captions for this clip')
            if reset:
                for i in selected:edits.pop(str(i),None)
                path.write_text(json.dumps(edits));st.rerun()
            if save:
                if any(not isinstance(r['caption'],str) or not r['caption'].strip() or len(r['caption'])>100 for r in updated):st.error('Keep each caption entry between 1 and 100 characters. This editor changes text, not spoken timing.')
                else:
                    for r in updated:
                        if r['caption']==r['original']:edits.pop(r['word_id'],None)
                        else:edits[r['word_id']]=r['caption'].strip()
                    path.write_text(json.dumps(edits));st.rerun()
    return corrected_words(transcript['words'],edits)
