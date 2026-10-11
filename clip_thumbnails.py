"""Cached thumbnails from the actual rendered clip; no model or network calls."""
from app_logging import log_exception
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
    key=hashlib.sha256(f'{video.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:thumb3'.encode()).hexdigest()[:24]
    cache=folder/'thumbnails'/key
    manifest=cache/'options.json'
    saved=read(manifest,None)
    if saved and len(saved.get('options',[]))==3 and all((cache/o['file']).is_file() for o in saved['options']):
        return cache,saved
    import cv2
    from visual_pacing import detect_faces,MODEL
    detector=cv2.FaceDetectorYN.create(str(MODEL),'',(640,640),.85,.3,5000) if MODEL.is_file() else None
    # Newer OpenCV builds can omit the legacy Haar API; it is optional.
    eye_detector=None
    if hasattr(cv2,'CascadeClassifier') and hasattr(cv2,'data'):
        eye_detector=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_eye.xml')
    options=[]
    with av.open(str(video)) as container:
        stream=container.streams.video[0]
        stream.codec_context.thread_count=1
        length=float(stream.duration*stream.time_base) if stream.duration else float(container.duration or 0)/av.time_base
        if length<=0:raise ValueError('The video has no readable duration.')
        origin=stream.start_time or 0
        for i,fraction in enumerate((.07,.18,.30,.42,.55,.68,.81,.93)):
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
            pixels=cv2.cvtColor(np.asarray(picture),cv2.COLOR_RGB2BGR)
            faces=detect_faces(pixels,detector) if detector else []
            face_detail=0.;eye_cues=0
            for x,y,w,h in faces:
                x,y,w,h=map(int,(x,y,w,h));region=pixels[max(0,y):y+h,max(0,x):x+w]
                if not region.size:continue
                face_gray=cv2.cvtColor(region,cv2.COLOR_BGR2GRAY)
                face_detail=max(face_detail,float(cv2.Laplacian(face_gray,cv2.CV_32F).var()))
                if eye_detector is not None and not eye_detector.empty():eye_cues=max(eye_cues,len(eye_detector.detectMultiScale(face_gray[:max(1,h*2//3)],1.1,4)))
            score=detail*exposure+min(20,face_detail/60)+min(2,len(faces))*3+min(2,eye_cues)*2
            cache.mkdir(parents=True,exist_ok=True)
            filename=f'option-{i+1}.jpg'
            import uuid
            temp=cache/(filename+'.'+uuid.uuid4().hex+'.tmp')
            picture.save(temp,format='JPEG',quality=90,optimize=True)
            temp.replace(cache/filename)
            options.append(dict(file=filename,seconds=round(timestamp,3),score=round(score,3),faces=len(faces),eye_cues=eye_cues))
    chosen=[]
    for option in sorted(options,key=lambda o:o['score'],reverse=True):
        if all(abs(option['seconds']-old['seconds'])>=length*.15 for old in chosen):chosen.append(option)
        if len(chosen)==3:break
    if len(chosen)<3:chosen+=[o for o in options if o not in chosen][:3-len(chosen)]
    clean_count=0
    for option in chosen:
        picture=clean_frame(video,option['seconds'])
        if picture is not None:
            picture.thumbnail((1280,1280),Image.Resampling.LANCZOS)
            picture.save(cache/option['file'],format='JPEG',quality=92);clean_count+=1
    saved=dict(options=chosen,recommended=0,sampled_frames=len(options),clean_frames=clean_count,eye_detector_available=eye_detector is not None,
        basis='Sharpness, exposure, visible-face and eye cues; expression and blinking are not reliably verified.')
    write(manifest,saved)
    return cache,saved


def clean_frame(video,seconds):
    """Reuse the source and camera plan for a cover without burned captions/hook duplication."""
    from project_store import read
    timeline=read(Path(video).with_suffix('.timeline.json'),{})
    plan=read(Path(video).with_suffix('.framing.json'),{})
    source=timeline.get('source')
    if not source or not Path(source).is_file() or not plan.get('decision'):return None
    offset=0.;source_time=None
    for r in timeline.get('ranges',[]):
        if offset<=seconds<offset+r['end']-r['start']:
            source_time=r['start']+seconds-offset;break
        offset+=r['end']-r['start']
    if source_time is None:return None
    if plan['decision']['kind']=='active':
        shot=next((s for s in plan['shots'] if s['start']<=seconds<s['end']),None)
        if not shot:return None
        plan=dict(plan,decision=shot['crop'],shots=[],pacing=[])
    from visual_pacing import camera_filter
    import subprocess,imageio_ffmpeg,io
    from PIL import Image
    graph=f'[0:v]setpts=PTS-STARTPTS+{seconds:.6f}/TB,'+camera_filter(plan)+'[cover]'
    command=[imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-threads','2','-ss',str(source_time),'-i',str(source),
        '-filter_complex_threads','2','-filter_complex',graph,'-map','[cover]','-an','-frames:v','1',
        '-fps_mode','passthrough','-threads','2','-c:v','png','-f','image2pipe','pipe:1']
    try:
        result=subprocess.run(command,capture_output=True,timeout=15)
        return Image.open(io.BytesIO(result.stdout)).convert('RGB') if result.returncode==0 else None
    except (OSError,ValueError,subprocess.TimeoutExpired):return None


def overlay_cover(cache,option,text):
    from PIL import Image,ImageDraw,ImageFont
    import textwrap
    text=' '.join(str(text).split())[:80]
    if not text:return cache/option['file']
    key=hashlib.sha256((option['file']+text+':overlay2').encode()).hexdigest()[:16]
    target=cache/('cover-'+key+'.jpg')
    if target.is_file():return target
    image=Image.open(cache/option['file']).convert('RGBA');width,height=image.size
    size=max(20,round(width*.055));font_path=Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf')
    lines=textwrap.wrap(text,width=25 if height>width else 40)
    for _ in range(12):
        font=ImageFont.truetype(str(font_path),size) if font_path.is_file() else ImageFont.load_default(size=size)
        draw=ImageDraw.Draw(image)
        if max(draw.textbbox((0,0),line,font=font)[2] for line in lines)<=width*.86:break
        size=max(16,size-2)
    overlay=Image.new('RGBA',image.size);draw=ImageDraw.Draw(overlay)
    top=round(height*.065);line_height=round(size*1.3)
    draw.rounded_rectangle((round(width*.04),top-14,round(width*.96),top+len(lines)*line_height+14),radius=12,fill=(12,16,24,255))
    for i,line in enumerate(lines):
        box=draw.textbbox((0,0),line,font=font);x=(width-(box[2]-box[0]))/2
        draw.text((x,top+i*line_height),line,font=font,fill='white',stroke_width=1,stroke_fill='black')
    import uuid
    temporary=target.with_name(target.name+'.'+uuid.uuid4().hex+'.tmp')
    Image.alpha_composite(image,overlay).convert('RGB').save(temporary,format='JPEG',quality=92)
    temporary.replace(target);return target


def show(video,folder,title):
    import streamlit as st
    from project_store import read,write
    from download_names import clip_filename
    with st.expander('Cover / thumbnail'):
        st.caption('Choose among frames from this finished clip. Visible faces, sharpness and brightness help rank frames; blinking, expression and recognizable identities still need your judgment.')
        stat=Path(video).stat();request_key=hashlib.sha256(f'{video}:{stat.st_mtime_ns}'.encode()).hexdigest()[:16]
        if st.button('Prepare cover options',key='prepare-cover-'+request_key):st.session_state['covers-ready-'+request_key]=True
        if not st.session_state.get('covers-ready-'+request_key):
            st.caption('Prepared only when requested; this does not rerun transcription or editing.')
            return
        try:
            with st.spinner('Preparing local thumbnails…'):
                cache,result=generate(video,folder)
        except Exception as error:
            log_exception('clip_thumbnails')
            st.warning(f'Could not prepare thumbnails: {error}')
            return
        saved=read(cache/'selected.json',{})
        with st.form('cover-text-'+cache.name):
            overlay_text=st.text_input('Cover text · leave blank for frame only',value=saved.get('text',title[:80]),max_chars=80)
            if st.form_submit_button('Apply cover text'):
                write(cache/'selected.json',dict(saved,text=overlay_text));st.rerun()
        overlay_text=saved.get('text',title[:80])
        for i,col in enumerate(st.columns(3)):
            item=result['options'][i]
            col.image(str(overlay_cover(cache,item,overlay_text)),caption=f"Option {i+1} · {item['seconds']:.1f}s"+(' · Recommended' if i==result['recommended'] else ''),width="stretch")
        initial=saved.get('option',result['recommended'])
        if initial not in range(3):initial=result['recommended']
        selection=st.radio('Choose thumbnail',range(3),index=initial,format_func=lambda i:f'Option {i+1}',horizontal=True,key='thumbnail-'+cache.name)
        if saved.get('option')!=selection:write(cache/'selected.json',dict(saved,option=selection,text=overlay_text))
        filename=Path(clip_filename(title)).stem+'-thumbnail.jpg'
        st.download_button('↓ Save thumbnail',overlay_cover(cache,result['options'][selection],overlay_text).read_bytes(),filename,'image/jpeg',key='download-thumbnail-'+cache.name,type='primary')
        st.caption('Downloaded separately. YouTube Shorts may control how covers are selected or surfaced; this does not set a platform thumbnail or upload anything.')
