"""Shared schedule details for both publishing history screens."""
import streamlit as st
from social_schedule import display_time,cancel_local


def schedule_panel(draft,key_prefix):
    if not draft.get('publish_at'):return False
    confirmed=dict(draft,publish_at=draft.get('remote_publish_at') or draft['publish_at'])
    st.caption('Post time: '+display_time(confirmed))
    if draft.get('schedule_provider')=='local':
        st.caption('Instagram scheduling needs this Mac awake and online. More than an hour late requires a new schedule.')
        if draft['status'] in ('Scheduled','Schedule failed'):
            if st.button('Cancel schedule & return to editing',key=key_prefix+'-cancel-'+draft['id']):
                try:cancel_local(draft['id'],draft['updated']);st.rerun()
                except Exception as error:st.error(str(error))
            return True
    elif draft.get('remote_id'):
        st.caption('YouTube handles the release after upload. Your Mac can be off. Manage or cancel an uploaded schedule in YouTube Studio.')
        st.link_button('Manage in YouTube Studio','https://studio.youtube.com/video/'+draft['remote_id']+'/edit')
    return False
