"""Move one managed project to macOS Trash without touching external originals."""
import fcntl
import json
import shutil
import uuid
from contextlib import ExitStack
from pathlib import Path


def delete_project(folder, root=None, trash=None):
    import social_store
    from project_store import read
    root=Path(root or Path(__file__).resolve().parent)
    folder=Path(folder)
    data=(root/'data').resolve()
    if folder.is_symlink() or folder.resolve().parent!=data or not folder.is_dir():
        raise ValueError('Only an existing project directly inside Clipping/data can be deleted.')
    folder=folder.resolve()
    if not isinstance(read(folder/'project.json',None),dict) and not read(folder/'import.json',{}).get('filename'):
        raise ValueError('This folder is not a saved Clipping project.')
    with ExitStack() as stack:
        # Do not move files out from under inference, rendering or a social upload.
        for path in (root/'work/heavy-job.lock',social_store.DB.parent/'social-upload.lock'):
            path.parent.mkdir(parents=True,exist_ok=True)
            lock=stack.enter_context(path.open('a'))
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ValueError('Wait for the current processing or publishing job to finish before deleting a project.')
        trash=Path(trash or Path.home()/'.Trash')
        trash.mkdir(parents=True,exist_ok=True)
        destination=trash/('Clipping-'+folder.name+'-'+uuid.uuid4().hex[:12])
        moved=False
        try:
            with social_store.connection() as db:
                db.execute('BEGIN IMMEDIATE')
                rows=db.execute('SELECT id,data FROM drafts').fetchall()
                for row in rows:
                    draft=json.loads(row['data'])
                    if Path(draft['folder']).resolve()==folder:
                        draft['project_deleted']=True
                        db.execute('UPDATE drafts SET data=? WHERE id=?',(json.dumps(draft),row['id']))
                shutil.move(str(folder),str(destination));moved=True
        except Exception:
            if moved and destination.exists() and not folder.exists():shutil.move(str(destination),str(folder))
            raise
    return destination


def confirm_delete(project):
    import streamlit as st
    identity=project['folder']
    with st.expander('Delete project'):
        st.write('Move this project’s imported video, transcripts, saved analyses and edits to your Mac’s Trash. Exported clips and files in Downloads are kept. Published posts and posting history are kept; drafts for this project can no longer be posted.')
        with st.form('delete-project-'+identity):
            confirmed=st.checkbox('Delete this project: '+project['title'])
            submit=st.form_submit_button('Move project to Trash')
        if submit:
            if not confirmed:st.error('Check the confirmation box to delete this project.')
            else:
                try:delete_project(identity)
                except ValueError as error:st.error(str(error))
                except OSError:st.error('Could not move the project to Trash. Check folder permissions and try again.')
                else:
                    if st.session_state.get('project',{}).get('folder')==identity:
                        for key in ('project','settings','result_path','clip_index'):st.session_state.pop(key,None)
                    st.session_state['deleted_project_notice']='Project moved to Trash. Exported clips were kept.'
                    st.rerun()
