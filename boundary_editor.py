"""Lightweight cut inspection and precise controls; no model inference."""
import math
from pathlib import Path


def check_boundaries(words,sentences,start,end,total):
    if not all(math.isfinite(v) for v in (start,end,total)) or not 0<=start<end<=total:
        return {'warnings':['Choose a start before the end, within the source video.'],'suggestion':None}
    warnings=[];left,right=start,end
    for label,at in [('Opening',start),('Ending',end)]:
        intersect=[w for w in words if w['start']+.005<at<w['end']-.005]
        if intersect:
            warnings.append(label+' cuts through the timed word: '+', '.join(str(w['text']) for w in intersect))
            if label=='Opening':left=max(0,min(w['start'] for w in intersect)-.08)
            else:right=min(total,max(w['end'] for w in intersect)+.08)
        elif any(s['start']+.08<at<s['end']-.08 for s in sentences):
            warnings.append(label+' falls inside a transcript sentence. Check whether the thought makes sense.')
    selected=[w for w in words if w['end']>start and w['start']<end]
    if selected and str(selected[-1]['text']).rstrip().endswith('?'):
        warnings.append('The clip ends with a question. Check that the intended answer is included.')
    # Only a small outward repair is suggested. Never silently change manual cuts.
    suggestion=(round(left,6),round(right,6)) if (left,right)!=(start,end) and start-left<=2 and right-end<=2 else None
    if not selected:warnings.append('No timed speech in this selection; use visual review to verify the boundaries.')
    return dict(warnings=warnings,suggestion=suggestion)


def boundary_frames(source,at,total):
    """Actual presentation timestamps near an edge, including VFR footage."""
    import av
    from io import BytesIO
    times=[];selected=None
    with av.open(str(source)) as media:
        stream=media.streams.video[0];stream.thread_count=1
        origin=float(stream.start_time*stream.time_base) if stream.start_time is not None else 0.
        media.seek(int(max(0,origin+at-.6)*av.time_base))
        for frame in media.decode(video=0):
            if frame.time is None:continue
            t=float(frame.time)-origin
            if t<max(0,at-.6):continue
            if t>min(total,at+.6):break
            times.append(t)
            if selected is None or abs(t-at)<abs(selected[0]-at):selected=(t,frame)
    if selected is None:return dict(times=[],image=None,time=None)
    im=selected[1].to_image();im.thumbnail((480,270))
    out=BytesIO();im.save(out,format='JPEG',quality=80)
    return dict(times=times,image=out.getvalue(),time=selected[0])


def adjacent_time(times,at,direction):
    values=[t for t in times if t<at-1e-6] if direction<0 else [t for t in times if t>at+1e-6]
    return (max(values) if direction<0 else min(values)) if values else at


def editor(source,total,start,end,transcript,identity):
    import streamlit as st
    warnings=check_boundaries(transcript['words'],transcript['sentences'],start,end,total)
    with st.expander('Precise timeline & boundary checks',expanded=True):
        st.caption('Times refer to the original video. The end is exclusive: a frame at the end time is not included. Changes apply only when you save them.')
        for warning in warnings['warnings']:st.warning(warning)
        if not warnings['warnings']:st.success('No timed word or sentence is cut at these boundaries. Visual completeness still needs review.')
        suggestion=warnings['suggestion']
        if suggestion and st.button(f'Include cut-off words · {suggestion[0]:.3f}s–{suggestion[1]:.3f}s',key='repair-'+identity):return suggestion
        # Slider edits happen in a form so dragging cannot trigger repeated renders.
        with st.form('timeline-'+identity+f'-{start}-{end}'):
            selection=st.slider('Selection in original video (seconds)',min_value=0.,max_value=float(total),value=(float(start),float(end)),step=.01,format='%.2f')
            if st.form_submit_button('Apply timeline selection'):return selection
        with st.form('precise-'+identity+f'-{start}-{end}'):
            a,b=st.columns(2)
            left=a.number_input('Exact start (seconds)',min_value=0.,max_value=float(total),value=float(start),step=.001,format='%.3f')
            right=b.number_input('Exact end (seconds)',min_value=0.,max_value=float(total),value=float(end),step=.001,format='%.3f')
            if st.form_submit_button('Apply exact times'):return left,right
        @st.cache_data(show_spinner=False,max_entries=64)
        def frames(file,mtime,point,length):return boundary_frames(file,point,length)
        if st.checkbox('Show boundary frames and frame-step controls',key='frames-'+identity):
            pending_key='frame-draft-'+identity+f'-{start}-{end}'
            pending_start,pending_end=st.session_state.get(pending_key,(start,end))
            for label,at,column in zip(['Start','End'],[pending_start,pending_end],st.columns(2)):
                with column:
                    try:near=frames(str(source),Path(source).stat().st_mtime_ns,at,total)
                    except Exception:st.info('Frame preview unavailable. Exact time controls still work.');continue
                    if near['image']:st.image(near['image'],caption=f"{label} preview · nearest frame at {near['time']:.6f}s")
                    before,after=st.columns(2)
                    for direction,button_column in [(-1,before),(1,after)]:
                        new=adjacent_time(near['times'],at,direction)
                        valid=(0<=new<pending_end) if label=='Start' else (pending_start<new<=total)
                        if button_column.button('← Frame' if direction<0 else 'Frame →',key=f'{identity}-{label}-{direction}',disabled=new==at or not valid):
                            st.session_state[pending_key]=(new,pending_end) if label=='Start' else (pending_start,new)
                            st.rerun()
            if (pending_start,pending_end)!=(start,end):
                st.caption(f'Preview selection: {pending_start:.6f}s–{pending_end:.6f}s. The saved clip has not changed.')
                if st.button('Apply frame adjustments',key='apply-frames-'+identity):return pending_start,pending_end
                if st.button('Discard frame adjustments',key='discard-frames-'+identity):
                    st.session_state.pop(pending_key,None);st.rerun()
            st.caption('Frame steps are preview-only until applied. Frame steps use decoded timestamps rather than assuming a fixed frame rate. Preview shows the nearest source frame, not the cropped export.')
        if st.checkbox('Play opening and ending with surrounding context',key='edge-context-'+identity):
            for label,at,col in zip(['Opening context','Ending context'],[start,end],st.columns(2)):
                with col:
                    st.write(label);st.video(str(source),start_time=float(max(0,at-3)),end_time=float(min(total,at+3)))
        nearby=[s for s in transcript['sentences'] if s['end']>max(0,start-5) and s['start']<min(total,end+5)]
        with st.expander('Transcript around this cut'):
            st.dataframe([{'Start':round(s['start'],3),'End':round(s['end'],3),'Text':s['text']} for s in nearby],hide_index=True)
    return None
