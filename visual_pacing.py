"""Local, cached face sampling and restrained final-timeline camera plans."""
import hashlib
import json
import math
import statistics
from pathlib import Path
from edit_timeline import remap_words, timeline_duration
from framing import choose_framing, framing_filter, blur_filter
from project_store import read, write

VERSION = 'visual-plan-2'
MODEL = Path(__file__).parent/'models/face-framing/yunet.onnx'
HOLD_SECONDS = 3.0


def detect_faces(pixels, detector=None):
    import cv2
    if detector is None:
        if not MODEL.is_file(): return []
        detector = cv2.FaceDetectorYN.create(str(MODEL),'',(640,640),.85,.3,5000)
    height,width=pixels.shape[:2];scale=min(1,640/width)
    small=cv2.resize(pixels,(round(width*scale),round(height*scale)))
    detector.setInputSize((small.shape[1],small.shape[0]))
    _,found=detector.detect(small)
    return [] if found is None else [list(float(v)/scale for v in f[:4]) for f in found]


def inspect_scene(source,ranges,cache_dir=None):
    """At most 24 samples, from KEPT footage only; sample cache ignores cosmetic changes."""
    import av
    stat=Path(source).stat();model_stat=[MODEL.stat().st_size,MODEL.stat().st_mtime_ns] if MODEL.is_file() else None
    key=hashlib.sha256(json.dumps([VERSION,str(Path(source).resolve()),stat.st_size,stat.st_mtime_ns,
                                  ranges,model_stat],sort_keys=True).encode()).hexdigest()[:24]
    cache=(Path(cache_dir) if cache_dir is not None else Path(__file__).parent/'work/visual-samples')/(key+'.json')
    saved=read(cache,None)
    if saved: return saved
    from time import perf_counter
    begun=perf_counter();samples=[];length=timeline_duration(ranges)
    # Uniform output-time samples plus the edges of every retained range.
    points={length*(.015+.97*i/max(1,min(15,int(length/2)+2)-1)) for i in range(min(15,int(length/2)+2))}
    offset=0
    for r in ranges:
        d=r['end']-r['start'];points.update((offset+min(.05,d/4),offset+d-min(.05,d/4)));offset+=d
    points=sorted(points)
    if len(points)>24: points=[points[round(i*(len(points)-1)/23)] for i in range(24)]
    detector=None
    if MODEL.is_file():
        import cv2
        detector=cv2.FaceDetectorYN.create(str(MODEL),'',(640,640),.85,.3,5000)
    with av.open(str(source)) as video:
        stream=video.streams.video[0];stream.codec_context.thread_count=1
        width,height=stream.width,stream.height
        origin=stream.start_time or 0
        for point in points:
            offset=0.;at=None;range_end=None
            for r in ranges:
                if point < offset+r['end']-r['start']:
                    at=r['start']+point-offset;range_end=r['end'];break
                offset+=r['end']-r['start']
            if at is None:continue
            video.seek(origin+int(at/stream.time_base),stream=stream)
            for frame in video.decode(stream):
                timestamp=float((frame.pts-origin)*stream.time_base) if frame.pts is not None else at
                if timestamp+1e-6>=at:
                    faces=detect_faces(frame.to_ndarray(format='bgr24'),detector) if detector and timestamp<range_end else []
                    samples.append(dict(time=point,source_time=timestamp,faces=faces));break
            else:samples.append(dict(time=point,source_time=at,faces=[]))
    result=dict(width=width,height=height,samples=samples,seconds=perf_counter()-begun,
                detector_available=detector is not None)
    write(cache,result);return result


def speaker_turns(words,mapping,hold=HOLD_SECONDS):
    """Tiny acknowledgements cannot trigger a cut; anonymous labels require user mapping."""
    groups=[]
    for w in words:
        speaker=w.get('speaker')
        if groups and speaker==groups[-1]['speaker']:
            groups[-1]['end']=w['end'];groups[-1]['words'].append(w['text'])
        else:groups.append(dict(speaker=speaker,start=w['start'],end=w['end'],words=[w['text']]))
    turns=[]
    for g in groups:
        if g['speaker'] not in mapping:continue
        if g['end']-g['start']<1.2 or len(g['words'])<4:continue
        if turns and (g['speaker']==turns[-1]['speaker'] or g['start']-turns[-1]['start']<hold):continue
        turns.append(dict(start=g['start'],speaker=g['speaker'],position=mapping[g['speaker']]))
    return turns


def pair_crops(samples,width,height,ratio=9/8):
    if not samples or sum(len(s['faces'])==2 for s in samples)<len(samples)*.9:return None
    pairs=[sorted(s['faces'],key=lambda f:f[0]+f[2]/2) for s in samples if len(s['faces'])==2]
    result=[]
    for slot in range(2):
        faces=[p[slot] for p in pairs]
        centers=[f[0]+f[2]/2 for f in faces]
        if max(centers)-min(centers)>width*.12:return None
        left=min(max(0,x-w*.2) for x,y,w,h in faces);right=max(min(width,x+w*1.2) for x,y,w,h in faces)
        top=min(max(0,y-h*.25) for x,y,w,h in faces);bottom=max(min(height,y+h*1.25) for x,y,w,h in faces)
        crop_h=int(min(height,width/ratio)//2*2);crop_w=int(crop_h*ratio)//2*2
        low_x=math.ceil(max(0,right-crop_w)/2)*2;high_x=math.floor(min(width-crop_w,left)/2)*2
        low_y=math.ceil(max(0,bottom-crop_h)/2)*2;high_y=math.floor(min(height-crop_h,top)/2)*2
        if low_x>high_x or low_y>high_y:return None
        x=int(max(low_x,min(high_x,statistics.median(centers)-crop_w/2)))//2*2
        y=int(max(low_y,min(high_y,statistics.median(f[1] for f in faces)-crop_h*.12)))//2*2
        # Rounding cannot reduce the protected face margins.
        if x<low_x or y<low_y:return None
        result.append(dict(kind='crop',x=x,y=y,width=crop_w,height=crop_h))
    if abs(result[0]['x']-result[1]['x'])<width*.1:return None
    return result


def can_zoom(decision,samples,amount):
    if decision['kind'] not in ('crop','blur_person'):return False
    x,y,w,h=[decision[k] for k in ('x','y','width','height')]
    margin_x=w*(1-1/(1+amount))/2; margin_y=h*(1-1/(1+amount))/2
    faces=[s['faces'][0] for s in samples if len(s['faces'])==1]
    return bool(faces) and len(faces)>=len(samples)*.9 and all(
        fx-fw*.05>=x+margin_x and fx+fw*1.05<=x+w-margin_x and
        fy-fh*.05>=y+margin_y and fy+fh*1.05<=y+h-margin_y for fx,fy,fw,fh in faces)


def plan_camera(scene,words,ranges,package,options,mode):
    length=timeline_duration(ranges);samples=scene['samples'];width,height=scene['width'],scene['height']
    fallback=dict(kind='native',reason='Original portrait composition retained.') if width*16==height*9 else dict(kind='blur',reason='Full picture retained because framing is uncertain.')
    plan=dict(version=VERSION,duration=length,decision=fallback,shots=[],pacing=[],warnings=[],
              reason=fallback['reason'],sample_count=len(samples),sampling_seconds=scene.get('seconds',0))
    if mode=='Sports':
        plan['reason']='Sports keeps the full picture; speaker switching and automatic punch-ins are disabled.'
        return plan
    decision=choose_framing([s['faces'] for s in samples],width,height)
    plan.update(decision=decision,reason=decision['reason'])
    if decision['kind'] in ('crop','blur_person'):
        plan['warnings'].append('Face sampling cannot verify slides, objects or source text outside the crop. Review the preview; choose full picture when that context matters.')
    conversation=options.get('conversation','Off')
    pairs=pair_crops(samples,width,height)
    if conversation!='Off' and pairs:
        verified=options.get('speaker_mapping_confirmed') and options.get('speaker_mapping_fingerprint')==package.get('fingerprint')
        mapping=options.get('speaker_positions',{}) if verified else {}
        active=pair_crops(samples,width,height,ratio=9/16)
        turns=[t for t in speaker_turns(words,mapping) if t['start']<=length-HOLD_SECONDS] if active else []
        substantive={w.get('speaker') for w in words if w.get('speaker')}
        valid_mapping=all(s in mapping and mapping[s] in ('Left','Right') for s in substantive) and set(mapping.values())=={'Left','Right'} and all(w.get('speaker') in mapping for w in words)
        if conversation in ('Active Speaker','Automatic') and valid_mapping and turns and len(turns)<=12 and len({t['speaker'] for t in turns})>=2:
            for i,t in enumerate(turns):
                slot=0 if t['position']=='Left' else 1
                plan['shots'].append(dict(start=0 if i==0 else t['start'],
                    end=turns[i+1]['start'] if i+1<len(turns) else length,crop=active[slot],speaker=t['speaker']))
            plan['reason']='Switched using your confirmed speaker positions, with a three-second minimum hold and short acknowledgements ignored.'
            plan['decision']=dict(kind='active')
        else:
            plan['decision']=dict(kind='split',crops=pairs)
            plan['reason']='Two stable visible faces kept in split screen; active-speaker identity was not inferred.'
            if conversation=='Active Speaker':plan['warnings'].append('Active-speaker framing could not be verified. Showing both visible speakers instead.')
        plan['warnings'].append('Speaker crops may omit slides, objects or text outside the faces. Review the preview; choose full picture to retain all visual content.')
        return plan
    if conversation=='Active Speaker' and not pairs:
        plan.update(decision=fallback,reason='Active-speaker framing is uncertain; full picture retained.')
        plan['warnings'].append('No stable two-person scene was confirmed. Speaker labels alone do not identify a visible face.')
        return plan
    pacing=options.get('pacing','Off');amount=.035 if pacing=='Subtle' else .07
    if pacing!='Off' and can_zoom(decision,samples,amount):
        beats=[]
        for unit in package.get('sentences',[])[1:]:
            if HOLD_SECONDS<=unit['start']<=length-2:
                beats.append((unit['start'],unit['text']))
        for phrase in package.get('emphasis',{}).get('phrases',[]):
            if HOLD_SECONDS<=phrase['start']<=length-2:beats.append((phrase['start'],phrase['text']))
        selected=[]
        for start,text in sorted(beats):
            if selected and start-selected[-1]['start']<HOLD_SECONDS:continue
            selected.append(dict(start=start,end=length,amount=amount,reason='Semantic beat: “'+text[:100]+'”'))
            if len(selected)>=(1 if pacing=='Subtle' else 2):break
        for i,beat in enumerate(selected):
            beat['end']=selected[i+1]['start'] if i+1<len(selected) else length
        plan['pacing']=selected
        if selected:plan['reason']+=' Restrained punch-in at a final-transcript beat, returning wider at the ending.'
    if pacing!='Off' and not plan['pacing']:
        plan['reason']+=' No useful, safely framed pacing change was established.'
    return plan


def pacing_filter(width,height,events):
    if not events:return ''
    terms=[f"{e['amount']:.6f}*min(clip((t-{e['start']:.6f})/1.2,0,1),clip(({e['end']:.6f}-t)/1.0,0,1))" for e in events]
    zoom='1+'+'+'.join(terms)
    return f"scale=w='trunc({width}*({zoom})/2)*2':h='trunc({height}*({zoom})/2)*2':eval=frame,crop={width}:{height}:(iw-{width})/2:(ih-{height})/2,setsar=1"


def camera_filter(plan):
    decision=plan['decision'];kind=decision['kind']
    if kind=='active':
        shots=plan['shots'];n=len(shots)
        parts=['split='+str(n)+''.join(f'[shot{i}]' for i in range(n))]
        for i,shot in enumerate(shots):
            parts.append(f"[shot{i}]trim=start={shot['start']:.6f}:end={shot['end']:.6f},setpts=PTS-STARTPTS,"+framing_filter(shot['crop'])+f'[view{i}]')
        return ';'.join(parts)+';'+''.join(f'[view{i}]' for i in range(n))+f'concat=n={n}:v=1:a=0,setsar=1'
    if kind=='split':
        parts=['split=2[top][bottom]']
        for label,crop in zip(('top','bottom'),decision['crops']):
            parts.append(f"[{label}]crop={crop['width']}:{crop['height']}:{crop['x']}:{crop['y']},scale=720:640,setsar=1[{label}view]")
        return ';'.join(parts)+';[topview][bottomview]vstack,setsar=1'
    if kind=='blur_person' and plan['pacing']:
        foreground=f"crop={decision['width']}:{decision['height']}:{decision['x']}:{decision['y']},"+pacing_filter(decision['width'],decision['height'],plan['pacing'])+','
        return blur_filter(foreground)
    result=framing_filter(decision)
    if plan['pacing']:result+=','+pacing_filter(720,1280,plan['pacing'])
    return result
