"""Review ending suggestions before explicitly applying a non-destructive trim."""
import streamlit as st
from ending_review import cached, get_ending, with_editor
from local_editor import installed, LABELS

ENDING_FORM_API = 3


def ending_form(folder, data, saved, identity, unavailable_reason=''):
    with st.expander('Improve the ending with AI'):
        st.caption('Finish on the useful point before a new topic. Generate a suggestion, review the removed speech, then apply it. Earlier speech and internal cuts stay in place.')
        if data is None:
            st.info('AI ending review needs complete timed speech. Use the boundary controls for this clip.')
            if unavailable_reason: st.caption(unavailable_reason)
            return None, False
        editors=['qwen3-4b','qwen3.5-4b']
        if data['model'] not in editors:editors.append(data['model'])
        selected=st.selectbox('Ending review editor',editors,index=editors.index(data['model']),format_func=lambda key:LABELS[key],
                              key='ending-editor-'+identity+'-'+data['model'])
        data=with_editor(data,selected)
        st.caption(LABELS[data['model']] + ' · ' + str(len(data['lessons'])) + ' ending examples · runs on this Mac')
        if not installed(data['model']): st.info('Choose an installed ending editor above to review this clip locally.')
        result = cached(folder, data)
        a, b = st.columns(2)
        generate = a.button('Review ending with AI', key='ending-' + identity, disabled=not installed(data['model']))
        fresh = b.button('Review ending again', key='fresh-ending-' + identity, disabled=not installed(data['model']))
        if generate or fresh:
            from ui_jobs import run_job
            try: result = run_job('ending-' + data['key'], lambda update: get_ending(folder, data, update, force=fresh), 60)
            except Exception as error:
                detail = (str(error).splitlines() or ['Review the boundary manually.'])[-1][:300]
                st.error('Could not review the ending: ' + detail)
        if result:
            st.write('Suggested ending: “' + result['last_sentence'] + '”')
            st.caption(result['reason'])
            st.caption(f"{result['previous_duration']:.1f}s → {result['duration']:.1f}s · source ending {result['end']:.3f}s")
            if result['changed']:
                with st.expander('Speech removed from the end'):
                    st.write(result['removed_transcript'])
            else: st.success('Keep the current ending. No trim is needed.')
            with st.expander('Why this ending works'):
                st.write('Main point: “' + result['main_point_quote'] + '”')
                st.write('Payoff: “' + result['payoff_quote'] + '”')
                st.caption(result['source_check'].get('reason', 'Checked against the selected speech.'))
                st.caption('The local model checks its own choice. Listen to the ending before sharing.')
            same = saved and saved.get('ranges') == result['ranges']
            if st.button('Apply this ending', key='apply-ending-' + identity, disabled=not result['changed'] or bool(same)):
                return result, True
        if saved:
            if saved.get('opening_text') != data['opening_text']:
                st.warning('This ending was reviewed with earlier opening text. Review the new wording or request another ending review. Your applied cut is kept.')
            st.caption('AI ending applied · ' + f"{saved['duration']:.1f}s. Previous exports are still saved.")
            if st.button('Restore prior ending', key='restore-ending-' + identity): return None, True
        return saved, False
