"""Choose one checked edit, inspect its decisions, request other edits only on demand."""
from app_logging import log_exception
import hashlib
import json
from project_store import read, write
from edit_timeline import edited_duration


def choose_edit(folder, analysis, candidate, transcript, settings):
    import streamlit as st
    from ui_jobs import run_job
    from upgrades import worker
    identity = hashlib.sha256((str(analysis)+str(candidate['start'])+str(candidate['end'])).encode()).hexdigest()[:20]
    saved_path = analysis.with_suffix('.variants.json')
    saved = read(saved_path, {})
    edits = saved.get(identity, {})
    if candidate.get('edit_plan'): edits = dict(edits, Balanced=candidate)
    source = candidate.get('source_candidate', candidate)
    primary = edits.get('Balanced')
    if primary is None:
        if candidate.get('shorts_editor_error'):st.warning('The Shorts edit was not verified. Showing the original moment for manual review.')
        if settings['mode'] != 'Sports' and st.button('Create a Shorts edit locally', key='shorts-'+identity):
            try:
                result = run_job('shorts-'+identity, lambda update:worker('shorts_edit', dict(candidate=source,
                    sentences=transcript['sentences'], words=transcript['words'], maximum=settings['maximum'],minimum=settings['minimum'],mode=settings['mode'],
                    quality=settings.get('quality','Balanced'), editor_model=settings.get('editor_model'), cache_dir=str(folder/'topic-reviews-v37/shorts')),
                    progress=update), 60)
                saved[identity] = dict(edits, Balanced=result)
                write(saved_path, saved)
                st.rerun()
            except Exception as error:
                log_exception('shorts_ui')
                st.warning('A safe Shorts edit was not produced: '+str(error))
        return candidate, 'Original moment'
    choices = [name for name in ('Balanced','Fast','Full Context') if name in edits] + ['Original moment']
    key = 'edit-variant-'+identity
    if 'pending-'+key in st.session_state: st.session_state[key] = st.session_state.pop('pending-'+key)
    st.session_state.setdefault(key, edits.get('_selected','Balanced') if edits.get('_selected','Balanced') in choices else 'Balanced')
    selected = st.selectbox('Edit version', choices, key=key)
    if edits.get('_selected')!=selected:
        saved[identity]=dict(edits,_selected=selected)
        write(saved_path,saved)
    chosen = source if selected == 'Original moment' else edits[selected]
    st.caption('Alternate edits share this moment. Only the selected version is rendered.')
    for option in primary['edit_plan'].get('supported_variants', []):
        name = option['name']
        if name=='Fast' and primary['edit_plan']['recommended_duration']<15:continue
        if name in edits: continue
        if st.button('Create '+name+' edit locally', key='generate-'+name+identity, help=option['reason']):
            try:
                baseline = {k:primary['edit_plan'][k] for k in ('ranges','recommended_duration','final_transcript')}
                result = run_job('variant-'+name+identity, lambda update,name=name,baseline=baseline:worker('shorts_edit', dict(candidate=source,
                    sentences=transcript['sentences'], words=transcript['words'], maximum=settings['maximum'],minimum=settings['minimum'],mode=settings['mode'],
                    quality=settings.get('quality','Balanced'), editor_model=settings.get('editor_model'), cache_dir=str(folder/'topic-reviews-v37/shorts'),
                    variant=name, baseline=baseline), progress=update), 60)
                saved[identity] = dict(edits, **{name:result},_selected=name)
                write(saved_path, saved)
                st.session_state['pending-'+key] = name
                st.rerun()
            except Exception as error:
                log_exception('shorts_ui')
                st.warning('This source did not produce a verified '+name+' edit: '+str(error))
    return chosen, selected


def decisions(candidate):
    import streamlit as st
    plan = candidate.get('edit_plan')
    if not plan: return
    original = plan['source_moment']
    st.caption(f"{original['end']-original['start']:.1f}s source moment → {edited_duration(candidate):.1f}s edited · {len(plan['ranges'])} kept ranges")
    with st.expander('Shorts editing decisions'):
        st.caption('Local model checks are estimates. Listen to the joins and compare the source before posting.')
        st.write(plan['standalone_context_check']['reason'])
        evidence=plan.get('validation',{}).get('context_evidence',{})
        if evidence:
            for name in ('subject','explanation','conclusion'):
                if evidence.get(name):st.write(name.capitalize()+': “'+evidence[name]+'”')
        if plan.get('context_restored_ids'):st.caption('Kept additional speech to finish the selected sentences and preserve their context.')
        st.caption(plan.get('decision_basis','Local editor proposal'))
        if plan.get('editor_model'):st.caption('AI editor: '+plan['editor_model'].split(':',1)[0])
        st.dataframe([dict(role=r['role'], start=round(r['start'],3), end=round(r['end'],3), reason=r['reason']) for r in plan['ranges']], hide_index=True)
        if plan['removed_ranges']:
            st.write('Removed speech')
            st.dataframe(plan['removed_ranges'], hide_index=True)
        st.write('Final spoken transcript')
        st.write(plan['final_transcript'])
        st.download_button('Download edit decisions', json.dumps(plan,indent=2), 'shorts-edit.json', 'application/json')
