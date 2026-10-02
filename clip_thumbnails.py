"""Cached thumbnails from the actual rendered clip; no model or network calls."""
import hashlib
import json
from pathlib import Path


def generate(video, folder):
    import av
    import numpy as np
    from PIL import Image
    from project_store import read,write
    video,folder=Path(video),Path(folder)
    stat=video.stat()
    key=hashlib.sha256(f'{video.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:thumb1'.encode()).hexdigest()[:24]
    cache=folder/'thumbnails'/key
    manifest=cache/'options.json'
    saved=read(manifest,None)
    if saved and len(saved.get('options',[]))==3 and all((cache/o['file']).is_file() for o in saved['options']):
        return cache,saved
    options=[]
    with av.open(str(video)) as container:
        stream=container.streams.video[0]
        stream.codec_context.thread_count=1
        length=float(stream.duration*stream.time_base) if stream.duration else float(container.duration or 0)/av.time_base
        if length<=0:raise ValueError('The video has no readable duration.')
        origin=stream.start_time or 0
        for i,fraction in enumerate((.2,.5,.8)):
            seconds=length*fraction
            container.seek(origin+int(seconds/stream.time_base),stream=stream,backward=True)
            chosen=None
            for count,frame in enumerate(container.decode(stream)):
                chosen=frame
                timestamp=float((frame.pts-origin)*stream.time_base) if frame.pts is not None else seconds
                if timestamp>=seconds or count>=300:break
            if chosen is None:raise ValueError('No readable video frame at this moment.')
            picture=chosen.to_image().convert('RGB')
            # Preserve portrait or landscape framing from the finished export.
            picture.thumbnail((1280,1280),Image.Resampling.LANCZOS)
            sample=picture.copy();sample.thumbnail((160,160))
            gray=np.asarray(sample.convert('L'),dtype=np.float32)
            detail=float(np.abs(np.diff(gray,axis=0)).mean()+np.abs(np.diff(gray,axis=1)).mean())
            exposure=float(((gray>20)&(gray<240)).mean())
            score=detail*exposure
            cache.mkdir(parents=True,exist_ok=True)
            filename=f'option-{i+1}.jpg'
            import uuid
            temp=cache/(filename+'.'+uuid.uuid4().hex+'.tmp')
            picture.save(temp,format='JPEG',quality=90,optimize=True)
            temp.replace(cache/filename)
            options.append(dict(file=filename,seconds=round(timestamp,3),score=round(score,3)))
    saved=dict(options=options,recommended=max(range(3),key=lambda i:options[i]['score']))
    write(manifest,saved)
    return cache,saved


def show(video,folder,title):
    import streamlit as st
    from project_store import read,write
    from download_names import clip_filename
    with st.expander('Video thumbnails',expanded=True):
        st.caption('Three frames from this finished clip. The recommendation favors sharpness and balanced brightness; choose the moment that best represents your video.')
        try:
            with st.spinner('Preparing local thumbnails…'):
                cache,result=generate(video,folder)
        except Exception as error:
            st.warning(f'Could not prepare thumbnails: {error}')
            return
        for i,col in enumerate(st.columns(3)):
            item=result['options'][i]
            col.image(str(cache/item['file']),caption=f"Option {i+1} · {item['seconds']:.1f}s"+(' · Recommended' if i==result['recommended'] else ''),width="stretch")
        saved=read(cache/'selected.json',{})
        initial=saved.get('option',result['recommended'])
        if initial not in range(3):initial=result['recommended']
        selection=st.radio('Choose thumbnail',range(3),index=initial,format_func=lambda i:f'Option {i+1}',horizontal=True,key='thumbnail-'+cache.name)
        if saved.get('option')!=selection:write(cache/'selected.json',dict(option=selection))
        filename=Path(clip_filename(title)).stem+'-thumbnail.jpg'
        st.download_button('↓ Save thumbnail', (cache/result['options'][selection]['file']).read_bytes(),filename,'image/jpeg',key='download-thumbnail-'+cache.name,type='primary')
        st.caption('Saved locally with this project. Download separately; this does not change the video or upload a social-media cover.')
