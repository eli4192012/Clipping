"""Offline mode routing from speech, title and sampled face evidence."""
import hashlib,json,re,subprocess,tempfile
from pathlib import Path


def classify(title,sentences,face_fraction=0):
    title=title.lower();text=' '.join(s['text'] for s in sentences);lower=text.lower()
    from interview import is_question,ANSWER_LEAD
    questions=sum(is_question(s['text']) and not ANSWER_LEAD.search(s['text']) for s in sentences)
    answers=sum(bool(ANSWER_LEAD.search(s['text'])) for s in sentences)
    interview=bool(re.search(r'interview|press conference|media availability|q\s*&\s*a',title))
    podcast=bool(re.search(r'podcast|roundtable|panel discussion',title))
    sports=bool(re.search(r'football|basketball|soccer|touchdown|highlights|nfl|nba|colts|texans',title+' '+lower))
    action=len(re.findall(r'touchdown|intercept(?:ed|ion)|sacked|first down|end zone|yard line|he throws|he scores|slam dunk|goal!',lower))
    if podcast:return dict(mode='Podcast',confidence='Moderate',reason='The title identifies a podcast or panel discussion; conversational story selection fits this format.')
    if interview or (questions>=2 and answers>=1 and (face_fraction>=.4 or questions>=4)):
        return dict(mode='Interview',confidence='High' if questions>=2 and face_fraction>=.4 else 'Moderate',reason='Question-and-answer speech or an explicit interview title indicates an interview, even when the subject is sports.')
    if sports and face_fraction<.4 and (action>=2 or re.search(r'highlights|full game|gameplay|best plays',title)):
        return dict(mode='Sports',confidence='Moderate',reason='Sports action cues and few visible close-up faces suggest on-field footage rather than an interview.')
    if questions>=2 and answers>=1:return dict(mode='Interview',confidence='Low',reason='Speech contains questions and answers, but the visual evidence is unclear. Check this choice for mixed footage.')
    return dict(mode='Podcast',confidence='Moderate' if len(text.split())>=80 and face_fraction>=.4 else 'Low',reason='No clear interview exchange or sports-action pattern was found. Podcast mode is the general speech/story fallback; override it for other footage.')


def detect(project,progress=lambda p,t:None):
    source=Path(project['source']);folder=Path(project['folder'])
    key=hashlib.sha256(json.dumps([str(source),source.stat().st_size,source.stat().st_mtime_ns,project['title'],'categories-v1']).encode()).hexdigest()[:16]
    cache=folder/('video-type-'+key+'.json')
    if cache.exists():return json.loads(cache.read_text())
    progress(.05,'Checking the video type')
    sentences=[];basis='sampled speech'
    for p in sorted(folder.glob('transcript*.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True):
        try:
            data=json.loads(p.read_text())
            if isinstance(data,dict) and 'sentences' in data:
                sentences=data['sentences'];basis='saved transcript';break
        except (ValueError,OSError):continue
    notes=[]
    if not sentences:
        import av,imageio_ffmpeg
        from engine import transcribe,speech_model
        with av.open(str(source)) as v:has_audio=bool(v.streams.audio)
        if has_audio:
            length=project['duration'] if project['duration']<=60 else 20
            starts=[0] if project['duration']<=60 else [0,(project['duration']-length)/2,project['duration']-length]
            recognizer=None
            with tempfile.TemporaryDirectory(prefix='clipping-type-') as tmp:
                for i,start in enumerate(starts):
                    progress(.1+.5*i/len(starts),'Listening to a short sample to identify the format')
                    sample=Path(tmp)/'sample.wav'
                    run=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-y','-ss',str(start),'-i',str(source),'-t',str(length),'-vn','-ac','1','-ar','16000',str(sample)],capture_output=True,text=True)
                    if run.returncode:notes.append('A speech sample could not be read.');continue
                    try:
                        if recognizer is None:recognizer=speech_model()
                        sentences.extend(transcribe(sample,model=recognizer)['sentences'])
                    except Exception:notes.append('Speech detection unavailable; used remaining evidence.');break
            del recognizer
        else:notes.append('No audio track found.')
    progress(.75,'Checking whether people stay visible')
    try:
        from framing import inspect_framing
        visual=inspect_framing(source,0,project['duration'])
        fraction=visual.get('single_face_samples',0)/max(1,visual.get('sample_count',0))
    except Exception:
        fraction=0;notes.append('Visual detection unavailable.')
    result=classify(project['title'],sentences,fraction)
    from content_categories import inferred
    result['categories']=inferred(project['title'],sentences,result['mode'])
    if notes:result['confidence']='Low'
    result.update(basis=basis,notes=notes,face_fraction=round(fraction,2))
    cache.write_text(json.dumps(result,indent=2));progress(1,'Video type identified')
    return result
