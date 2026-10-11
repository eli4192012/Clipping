"""Saved copy for sharing clips, with a 100-character title limit."""
from app_logging import log_exception


def normalize(title,description):
    title=' '.join(str(title).split()).strip() or 'Video highlight'
    if len(title)>100:
        shortened=title[:99]
        title=(shortened.rsplit(' ',1)[0] if ' ' in shortened else shortened).rstrip(' .')+'…'
    return dict(title=title,description=str(description).strip()[:2000])


def clean_saved(copy):
    result=normalize(copy.get('title','Video highlight'),copy.get('description',''))
    if copy.get('fallback'):result['fallback']=True
    return result


def fallback(candidate,text):
    excerpt=' '.join(text.split())[:500]
    return normalize(candidate.get('title','Video highlight'),('From this clip: “'+excerpt+'”') if excerpt else 'A selected moment from this video.')


def show(folder,candidate,words,start,end,quality):
    import hashlib,json
    import streamlit as st
    from project_store import read,write
    text=' '.join(w['text'] for w in words if w['end']>start and w['start']<end)
    key=hashlib.sha256(json.dumps([start,end,text],ensure_ascii=False).encode()).hexdigest()[:24]
    path=folder/'publishing-copy.json';saved=read(path,{})
    if key not in saved:
        copy=candidate.get('publishing') if start==candidate['start'] and end==candidate['end'] and text.strip()==candidate['text'].strip() else None
        if copy:
            saved[key]=clean_saved(copy)
        else:
            from upgrades import worker
            from ui_jobs import run_job
            try:
                result=run_job('publishing-'+key,lambda update:worker('publishing',dict(text=text,quality=quality)),45)
                saved[key]=normalize(result.get('title',candidate['title']),result.get('description',''))
            except Exception:
                log_exception('publishing')
                saved[key]=fallback(candidate,text)
                saved[key]['fallback']=True
        write(path,saved)
    copy=clean_saved(saved[key])
    if copy!=saved[key]:saved[key]=copy;write(path,saved)
    with st.expander('Title & description',expanded=True):
        if copy.get('fallback'):st.info('Local writing was unavailable. Showing a title and transcript excerpt; use Generate fresh copy to retry.')
        st.caption('Title: '+str(len(copy['title']))+'/100 characters, including spaces. Copy using the code-block button.')
        st.code(copy['title'],language=None)
        st.text_area('Description',value=copy['description'],height=110,disabled=True,key='description-'+key)
        if st.button('Generate fresh copy locally',key='generate-copy-'+key):
            from upgrades import worker
            from ui_jobs import run_job
            try:
                result=run_job('publishing-'+key,lambda update:worker('publishing',dict(text=text,quality=quality)),45)
                saved[key]=normalize(result.get('title',candidate['title']),result.get('description',''))
                write(path,saved);st.rerun()
            except Exception as e:
                log_exception('publishing')
                st.error(f'Could not generate copy: {e}')
        with st.form('edit-copy-'+key):
            title=st.text_input('Posting title',value=copy['title'])
            description=st.text_area('Edit description',value=copy['description'])
            if st.form_submit_button('Save posting copy'):
                title=' '.join(title.split())
                if len(title)>100:st.error(f'Title totals {len(title)} characters. Reduce it to 100 or fewer.')
                else:saved[key]=normalize(title,description);write(path,saved);st.rerun()
        st.download_button('Download posting text',copy['title']+'\n\n'+copy['description'],'posting-text.txt',key='download-copy-'+key)
    return copy
