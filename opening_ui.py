"""On-demand opening suggestions; applying them changes only first-screen text."""
import streamlit as st
from opening_hooks import context, cached_hook, get_hook
from local_editor import installed, LABELS

OPENING_FORM_API = 1


def opening_form(root, folder, package, words, settings, style, identity):
    with st.expander('Improve the opening with AI'):
        st.caption('Make the subject clear from the first frame and preview the clip’s point. Review a suggestion, then apply it to the opening text.')
        if settings.get('mode') == 'Sports' or not package['final_transcript'].strip():
            st.info('AI opening text currently uses speech clips. You can write opening text below for this clip.')
            return style, False
        try:
            info = context(root, package, words, settings)
        except ValueError as error:
            st.error(str(error))
            return style, False
        if style.get('opening_hook_fingerprint') and style['opening_hook_fingerprint'] != package['fingerprint']:
            st.warning('This saved AI opening was written for an earlier cut. Review it or generate a new suggestion.')
        st.caption(LABELS[info['model']] + ' · ' + str(len(info['lessons'])) + ' opening examples · runs on this Mac')
        if not installed(info['model']):
            st.info('The selected local editor is missing. Choose an installed editor in project settings, or write the opening text below.')
        st.write('Current opening text: ' + (style.get('title') or 'Hidden'))
        result = cached_hook(folder, package, info)
        a, b = st.columns(2)
        generate = a.button('Generate AI opening', key='generate-opening-' + identity, disabled=not installed(info['model']))
        fresh = b.button('Generate a fresh opening', key='fresh-opening-' + identity, disabled=not installed(info['model']))
        if generate or fresh:
            from ui_jobs import run_job
            try:
                result = run_job('opening-' + info['key'], lambda update: get_hook(folder, package, info, update, force=fresh), 60)
            except Exception as error:
                detail = (str(error).splitlines() or ['Try again or enter opening text manually.'])[-1][:240]
                st.error('Could not generate an opening: ' + detail)
        if result:
            st.markdown('**Suggested opening text**')
            st.write(result['opening_text'])
            st.caption(result.get('reason', ''))
            with st.expander('Why this fits the clip'):
                st.write('Subject: “' + result['subject_quote'] + '”')
                st.write('Payoff: “' + result['payoff_quote'] + '”')
                st.caption(result['source_check'].get('reason', 'Checked against the final speech.'))
                st.caption('The local model checks its own suggestion in a separate pass. Listen and review the wording.')
            if st.button('Apply this opening text', key='apply-opening-' + identity,
                         disabled=style.get('title') == result['opening_text'] and style.get('opening_hook_fingerprint') == package['fingerprint']):
                return dict(style, title=result['opening_text'], opening_hook_key=result['key'],
                            opening_hook_fingerprint=package['fingerprint']), True
        return style, False
