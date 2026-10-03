"""Browse and annotate clip references without running model work."""
from pathlib import Path
import json
import streamlit as st
from example_library import LABELS, FORMATS, STATUSES, add_clip, directory, load, save_notes


def _lines(value):
    return [line.strip() for line in value.splitlines() if line.strip()]


def show(root):
    st.title('Example library.')
    st.write('Keep clips and titles worth learning from, with notes on what works and what to avoid.')
    st.caption('Step 1: collect and review examples. These records do not yet change AI editing or titles.')
    try:
        bank = load(root)
    except ValueError as error:
        st.error(str(error))
        return
    notice = st.session_state.pop('example-library-notice', None)
    if notice:
        st.success(notice)
    with st.expander('Add an example'):
        with st.form('add-example', clear_on_submit=True):
            upload = st.file_uploader('Example video', type=['mp4', 'mov', 'm4v', 'webm', 'mkv'])
            name = st.text_input('Example name')
            title = st.text_input('Actual posted title', help='Use the published title, including its hashtags.')
            kind = st.selectbox('Video format', FORMATS)
            strengths = st.text_area('What works', help='One observation per line.')
            cautions = st.text_area('What to avoid copying', help='One observation per line.')
            transcript = st.text_area('Transcript, if you have it', help='No automatic transcription runs when adding an example.')
            if st.form_submit_button('Add example'):
                try:
                    if upload is None:
                        raise ValueError('Choose an example video first.')
                    _, added = add_clip(root, upload.getvalue(), upload.name, name, title, kind, strengths, cautions, transcript)
                    st.session_state['example-library-notice'] = 'Example saved locally.' if added else 'That clip is already in the library; its existing notes were kept.'
                    st.rerun()
                except (ValueError, OSError) as error:
                    st.error(str(error))
    examples = sorted(bank['examples'], key=lambda e: LABELS.index(e['label']))
    st.write(f'{len(examples)} examples · {sum(e["status"] == STATUSES[1] for e in examples)} marked ready for future reference')
    st.caption('Example types describe editing lessons; analytics show the post’s measured results.')
    if not examples:
        st.info('Add a clip to start your example library.')
        return
    search, filter_column = st.columns([3, 1])
    query = search.text_input('Find an example', placeholder='Search titles and notes…').strip().casefold()
    label = filter_column.selectbox('Example type', ['All examples', *LABELS])
    matches = [e for e in examples if (label == 'All examples' or e['label'] == label)
               and (not query or query in ' '.join([e['name'], e['posted_title'], e.get('notes', ''),
                                                   *e['observations']['strengths'], *e['observations']['cautions']]).casefold())]
    if not matches:
        st.info('No examples match this search.')
        return
    lookup = {e['id']: e for e in matches}
    selected = st.selectbox('Choose an example', list(lookup), format_func=lambda key:
                            (lookup[key]['posted_title'] or lookup[key]['name']), key='example-library-choice')
    example = lookup[selected]
    st.subheader(example['name'])
    st.caption(f'{example["content_format"]} · {example["duration"]:.1f}s · {example["label"]} · {example["status"]}')
    preview, details = st.columns([1, 2])
    with preview:
        source = Path(example['source'])
        if not source.is_file():
            st.warning('The original clip is missing. Your notes and transcript are still saved.')
        else:
            if st.button('Show clip preview', key='example-preview-' + selected):
                st.session_state['example-preview-id'] = selected
            if st.session_state.get('example-preview-id') == selected:
                st.video(str(source))
        frame_sheet = example.get('frame_sheet')
        if frame_sheet and (directory(root) / frame_sheet).is_file():
            with st.expander('Sampled frames'):
                st.image(str(directory(root) / frame_sheet))
    with details:
        if example['posted_title']:
            st.markdown('**Actual posted title**')
            st.write(example['posted_title'])
        if example.get('opening_text'):
            st.markdown('**Opening text visible in the clip**')
            st.write(example['opening_text'])
        analytics = example.get('analytics') or {}
        if analytics:
            st.markdown('**YouTube analytics**')
            period = example.get('analytics_period', [])
            if period:
                st.caption('Export period: ' + ' to '.join(period))
            metrics = st.columns(2)
            metrics[0].metric('Views', analytics.get('Views', '—'))
            metrics[1].metric('Engaged views', analytics.get('Engaged views', '—'))
            metrics[0].metric('Stayed to watch', analytics.get('Stayed to watch (%)', '—') + '%')
            metrics[1].metric('Average viewed', analytics.get('Average percentage viewed (%)', '—') + '%')
            st.caption('Average viewed applies to people who stayed, and can exceed 100%. Read it alongside the engaged-view count.')
            if not example.get('analytics_match_confirmed'):
                st.warning('Possible YouTube match — not confirmed yet.')
            st.caption(example.get('analytics_match', {}).get('basis', ''))
        else:
            st.caption('No analytics are attached to this example.')
        st.markdown('**What works**')
        for line in example['observations']['strengths']:
            st.write('• ' + line)
        st.markdown('**What to avoid copying**')
        for line in example['observations']['cautions']:
            st.write('• ' + line)
    with st.expander('Transcript'):
        if example.get('transcript_reviewed'):
            st.caption('Marked reviewed by you. The original transcript is preserved.')
        else:
            st.caption('Not checked word by word. Automatic transcripts can contain mistakes.')
        st.write(example.get('transcript_text') or 'No transcript supplied yet.')
    with st.expander('Review and edit example notes'):
        with st.form('example-notes-' + selected):
            name = st.text_input('Example name', example['name'])
            title = st.text_input('Actual posted title', example['posted_title'])
            opening = st.text_input('Opening text', example.get('opening_text', ''))
            kind = st.selectbox('Video format', FORMATS, index=FORMATS.index(example['content_format']))
            label = st.selectbox('Example type', LABELS, index=LABELS.index(example['label']))
            status = st.selectbox('Reference status', STATUSES, index=STATUSES.index(example['status']))
            st.caption('Ready means you have reviewed its lessons for future use. It is not an AI quality score.')
            strengths = st.text_area('What works', '\n'.join(example['observations']['strengths']))
            cautions = st.text_area('What to avoid copying', '\n'.join(example['observations']['cautions']))
            role = st.text_area('Use this example for', example['observations'].get('role', ''))
            notes = st.text_area('Your notes', example.get('notes', ''))
            matched = st.checkbox('I confirmed this clip matches the attached YouTube analytics', value=example.get('analytics_match_confirmed', False), disabled=not bool(analytics))
            checked = st.checkbox('I checked the transcript against the clip', value=example.get('transcript_reviewed', False), disabled=not bool(example.get('transcript_text')))
            if st.form_submit_button('Save example notes'):
                try:
                    save_notes(root, selected, name=name, posted_title=title, opening_text=opening,
                               content_format=kind, label=label, status=status, notes=notes,
                               observations=dict(strengths=_lines(strengths), cautions=_lines(cautions), role=role),
                               analytics_match_confirmed=matched, transcript_reviewed=checked)
                    st.session_state['example-library-notice'] = 'Example notes saved.'
                    st.rerun()
                except ValueError as error:
                    st.error(str(error))
    st.download_button('Download example library', json.dumps(bank, indent=2, ensure_ascii=False),
                       'example-library.json', 'application/json')
