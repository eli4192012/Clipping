"""A small persistent playlist builder for finished local clips."""
from pathlib import Path
import streamlit as st
from ui_jobs import clock, run_job
from combined_video import (FORMATS, drafts, new_draft, save_draft, saved_clips,
                            move_clip, export_combination, assembly_fingerprint)


def add_to_draft(root, clip):
    choices = drafts(root)
    identity = st.session_state.get('assembly_id')
    draft = next((d for d in choices if d['id'] == identity), None) or (choices[0] if choices else new_draft())
    # Opening a clip twice should not accidentally add it twice.
    if not any(item['id'] == clip['id'] for item in draft['clips']):
        draft['clips'].append(clip)
        save_draft(root, draft)
    st.session_state.assembly_id = draft['id']


def show(root):
    root = Path(root)
    st.title('Combine clips.')
    st.write('Put saved clips in order and turn them into one longer video.')
    choices = drafts(root)
    if not choices:
        draft = new_draft()
        save_draft(root, draft)
        choices = [draft]
    identity = st.session_state.get('assembly_id', choices[0]['id'])
    if identity not in {d['id'] for d in choices}:
        identity = choices[0]['id']
    select, create = st.columns([5, 1])
    selected = select.selectbox('Saved combinations', [d['id'] for d in choices],
                                index=next(i for i, d in enumerate(choices) if d['id'] == identity),
                                format_func=lambda key: next(d['title'] for d in choices if d['id'] == key),
                                key='saved-assembly-'+identity)
    if create.button('New combination'):
        draft = new_draft()
        save_draft(root, draft)
        st.session_state.assembly_id = draft['id']
        st.rerun()
    if selected != identity:
        st.session_state.assembly_id = selected
        st.rerun()
    draft = next(d for d in choices if d['id'] == selected)
    st.session_state.assembly_id = selected
    with st.form('assembly-options-'+selected):
        title = st.text_input('Video name', value=draft['title'], max_chars=120)
        canvas = st.selectbox('Video shape', list(FORMATS), index=list(FORMATS).index(draft['format']))
        background = st.checkbox('Use a blurred background where clips do not fill the frame', value=draft['background'] == 'blur')
        st.caption('The full saved clip stays visible. Its captions and opening text stay in the video.')
        if st.form_submit_button('Save video settings'):
            draft.update(title=title.strip() or 'Combined video', format=canvas, background='blur' if background else 'dark')
            save_draft(root, draft)
            st.rerun()
    available, errors = saved_clips(root)
    if errors:
        st.warning(f'{len(errors)} saved exports could not be read. The remaining clips are available.')
    projects = ['All projects']+sorted({c['project'] for c in available})
    project = st.selectbox('Clips from', projects)
    query = st.text_input('Find a saved clip', placeholder='Search by title or project…').strip().lower()
    matches = [c for c in available if (project == 'All projects' or c['project'] == project)
               and (not query or query in (c['title']+' '+c['project']).lower())]
    lookup = {c['id']: c for c in matches}
    with st.form('add-clips-'+selected, clear_on_submit=True):
        added = st.multiselect('Choose clips to add', list(lookup), format_func=lambda key:
                               lookup[key]['title']+' · '+clock(lookup[key]['duration'])+' · '+lookup[key]['project'])
        if st.form_submit_button('Add selected clips', disabled=not matches):
            existing = {c['id'] for c in draft['clips']}
            draft['clips'].extend(lookup[key] for key in added if key not in existing)
            save_draft(root, draft)
            st.rerun()
    if not available:
        st.info('Open Review clip on the clips you want first. Their finished versions will appear here.')
    st.subheader('Your video order')
    missing = []
    total = 0.
    for i, clip in enumerate(draft['clips']):
        content, up, down, remove = st.columns([7, 1, 1, 1])
        content.write(f"{i+1}. {clip['title']}")
        length = float(clip.get('duration', 0))
        total += length
        content.caption(clip.get('project', 'Saved clip')+' · '+clock(length))
        if not Path(clip['video']).is_file():
            content.error('This saved clip is missing. Remove it or restore the file before exporting.')
            missing.append(clip)
        if up.button('↑', key=f'up-{selected}-{i}', help='Move clip up', disabled=i == 0):
            save_draft(root, move_clip(draft, i, -1))
            st.rerun()
        if down.button('↓', key=f'down-{selected}-{i}', help='Move clip down', disabled=i == len(draft['clips'])-1):
            save_draft(root, move_clip(draft, i, 1))
            st.rerun()
        if remove.button('Remove', key=f'remove-{selected}-{i}'):
            draft['clips'].pop(i)
            save_draft(root, draft)
            st.rerun()
    st.caption(f"{len(draft['clips'])} clips · about {clock(total)} total. Your order is saved on this Mac.")
    if draft['clips']:
        with st.expander('Preview one clip'):
            preview = st.selectbox('Clip to preview', range(len(draft['clips'])),
                                   format_func=lambda i: f"{i+1}. {draft['clips'][i]['title']}")
            clip = draft['clips'][preview]
            if Path(clip['video']).is_file():
                st.video(clip['video'])
    st.caption('Clips join with direct cuts. Review the transitions and story before sharing. New edits to an individual clip need to be added as a new saved version.')
    if len(draft['clips']) < 2:
        st.info('Add at least two clips to export a combined video.')
    if st.button('Export combined video', type='primary', disabled=len(draft['clips']) < 2 or bool(missing)):
        try:
            result = run_job('assembly-'+selected, lambda update: export_combination(root, draft, update), max(20, total*2))
            draft['last_export'] = result
            save_draft(root, draft)
            st.rerun()
        except Exception as error:
            st.error(str(error))
    result = draft.get('last_export')
    if result and Path(result['video']).is_file():
        st.subheader('Saved combined video')
        try:
            current = assembly_fingerprint(draft) == result.get('fingerprint')
        except (OSError, ValueError):
            current = False
        if not current:
            st.info('The combination has changed since this export. Export again to update the saved video.')
        if st.checkbox('Preview combined video', key='preview-combined-'+selected):
            st.video(result['video'])
        st.caption(clock(result['duration'])+f" · {result['width']} × {result['height']}")
        from download_names import clip_filename
        video_name = clip_filename(draft['title'])
        finder, download = st.columns(2)
        if finder.button('Show video in Finder'):
            import subprocess
            subprocess.run(['open', '-R', result['video']], check=False)
        ready_key = 'assembly-download-'+result['video']
        if download.button('Prepare video download'):
            st.session_state[ready_key] = True
        st.caption('The video is already saved in exports. Preview and browser download load it only when requested.')
        if st.session_state.get(ready_key):
            with Path(result['video']).open('rb') as file:
                st.download_button('↓ Save combined video', file, video_name, 'video/mp4', type='primary')
        captions = Path(result['captions'])
        if captions.is_file() and captions.read_text().strip():
            st.download_button('↓ Save combined subtitles', captions.read_bytes(), clip_filename(draft['title'], 'srt'), 'text/plain')
        st.download_button('↓ Save clip timestamps', Path(result['chapters']).read_bytes(), Path(video_name).stem+'-chapters.txt', 'text/plain')
