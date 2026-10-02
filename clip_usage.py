"""Persist a used marker per saved clip, independent of titles and style edits."""
import hashlib
from pathlib import Path
from project_store import read,write


def clip_key(run,clip):
    return hashlib.sha256(f"{Path(run).name}:{clip['start']}:{clip['end']}".encode()).hexdigest()[:24]


def is_used(folder,run,clip):
    return read(Path(folder)/'used-clips.json',{}).get(clip_key(run,clip),False) is True


def set_used(folder,run,clip,value):
    path=Path(folder)/'used-clips.json';data=read(path,{})
    if value:data[clip_key(run,clip)]=True
    else:data.pop(clip_key(run,clip),None)
    write(path,data)


def checkbox(folder,run,clip,location):
    import streamlit as st
    current=is_used(folder,run,clip)
    key='used-'+str(folder)+'-'+clip_key(run,clip)+'-'+location
    # The disk value is authoritative when switching between list and editor.
    st.session_state[key]=current
    def changed():set_used(folder,run,clip,st.session_state[key])
    st.checkbox('Used',key=key,on_change=changed,help='Mark this saved clip as already used. You can uncheck it anytime.')
