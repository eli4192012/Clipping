"""Conservative local face framing. Uncertain/mixed footage keeps the full picture."""
import statistics

AUTO='Portrait · automatic'


def choose_framing(samples,width,height):
    """Try stable portrait crops from tight to wide, then preserve context with blur."""
    import math
    if width*16==height*9:
        return dict(kind='native',reason='Already 9:16; kept the original framing without added blur or extra zoom.')
    fallback=dict(kind='blur',reason='Kept the full picture with a blurred video background: no safe single-person portrait crop was confirmed.')
    if not samples:return fallback
    if any(len(faces)>1 for faces in samples):return dict(fallback,reason='Multiple faces detected; kept everyone visible over a blurred video background.')
    faces=[s[0] for s in samples if len(s)==1]
    if len(faces)<len(samples)*.85:return fallback
    face_h=statistics.median(f[3] for f in faces)
    if face_h<height*.08:return fallback
    centers=[x+w/2 for x,y,w,h in faces]
    cx=statistics.median(centers)
    # Use all sampled positions, including movement. Clamp safety margins to the
    # actual source: a crop cannot recover headroom absent from the original.
    left=min(max(0,x-w*.20) for x,y,w,h in faces)
    right=max(min(width,x+w*1.20) for x,y,w,h in faces)
    top=min(max(0,y-h*.25) for x,y,w,h in faces)
    bottom=max(min(height,y+h*1.20) for x,y,w,h in faces)
    max_units=int(min(height,width*16/9)//32)
    preferred=min(max_units,max(1,math.ceil(max(height*.65,face_h*5)/32)))
    # Multiples of 18x32 give an exact 9:16 ratio and even codec dimensions.
    for units in sorted(set([preferred,min(max_units,math.ceil(preferred*1.2)),max_units])):
        if units<1:continue
        crop_w,crop_h=18*units,32*units
        low_x=math.ceil(max(0,right-crop_w)/2)*2
        high_x=math.floor(min(width-crop_w,left)/2)*2
        low_y=math.ceil(max(0,bottom-crop_h)/2)*2
        high_y=math.floor(min(height-crop_h,top)/2)*2
        if low_x>high_x or low_y>high_y:continue
        x=max(low_x,min(high_x,round((cx-crop_w/2)/2)*2))
        y=max(low_y,min(high_y,round((statistics.median(f[1] for f in faces)-crop_h*.12)/2)*2))
        return dict(kind='crop',x=x,y=y,width=crop_w,height=crop_h,
            reason='Used a clear full-screen portrait crop with the original background. All sampled faces fit with safety margins; no added blur.')
    wide=min(width,height*1.2)
    foreground_left=max(0,min(width-wide,cx-wide/2))
    if left>=foreground_left and right<=foreground_left+wide:
        return dict(kind='blur_person',x=int(foreground_left)//2*2,y=0,width=int(wide)//2*2,height=height//2*2,
            reason='A full-screen portrait crop would cut into the sampled face positions. Used a wider, sharp foreground with blurred video behind it.')
    return fallback


def inspect_framing(source,start,end):
    import av,cv2
    from pathlib import Path
    with av.open(str(source)) as probe:
        width,height=probe.streams.video[0].width,probe.streams.video[0].height
        if width*16==height*9:return choose_framing([],width,height)
    model=Path(__file__).parent/'models/face-framing/yunet.onnx'
    if not model.exists():return dict(kind='blur',reason='Face detector unavailable; kept the full picture with a blurred background.')
    detector=cv2.FaceDetectorYN.create(str(model),'',(640,640),.85,.3,5000)
    samples=[]
    with av.open(str(source)) as video:
        stream=video.streams.video[0];width,height=stream.width,stream.height
        if width*16==height*9:return choose_framing([],width,height)
        # Sample throughout the actual selected clip, including its first and final moments.
        count=max(3,min(24,int((end-start)/2)+2))
        for i in range(count):
            at=start+(end-start)*(.015+.97*i/(count-1))
            video.seek(int(at*av.time_base))
            for frame in video.decode(video=0):
                if frame.time is not None and frame.time>=at:
                    pixels=frame.to_ndarray(format='bgr24');scale=min(1,640/width)
                    pixels=cv2.resize(pixels,(round(width*scale),round(height*scale)))
                    detector.setInputSize((pixels.shape[1],pixels.shape[0]))
                    _,found=detector.detect(pixels)
                    samples.append([] if found is None else [tuple(float(n)/scale for n in rect[:4]) for rect in found]);break
            else:samples.append([])
    return dict(choose_framing(samples,width,height),sample_count=len(samples),single_face_samples=sum(len(s)==1 for s in samples))


def framing_filter(decision):
    if decision['kind']=='native':return 'scale=720:1280,setsar=1'
    if decision['kind']=='crop':
        return f"crop={decision['width']}:{decision['height']}:{decision['x']}:{decision['y']},scale=720:1280,setsar=1"
    if decision['kind']=='blur_person':return blur_filter(f"crop={decision['width']}:{decision['height']}:{decision['x']}:{decision['y']},")
    return blur_filter()


def blur_filter(foreground=''):
    # Both layers are the same video and remain synchronized. Downscaling before
    # blur keeps it inexpensive; background fills every pixel of the portrait.
    return ('split=2[back][front];[back]scale=180:320:force_original_aspect_ratio=increase,'
            'crop=180:320,boxblur=12:2,scale=720:1280,setsar=1[blurred];'
            f'[front]{foreground}scale=720:1280:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1[sharp];'
            '[blurred][sharp]overlay=(W-w)/2:(H-h)/2:shortest=1,setsar=1')
