"""Source-timed local audio evidence, cached independently of transcription."""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from project_store import read,write

VERSION='sound-yamnet-2'
WEIGHTS_SHA='13c3308955bbfaef262f175ac9c40e47b134573a93984f009220dd7cc12a1744'
ROOT=Path(__file__).resolve().parent
REACTIONS={'Laughter','Giggle','Chuckle, chortle','Belly laugh','Applause','Cheering','Whoop','Shout','Yell'}


def signature(path):
    p=Path(path).resolve();s=p.stat()
    return dict(path=str(p),size=s.st_size,mtime_ns=s.st_mtime_ns)


def installed(root=ROOT):
    root=Path(root);weights=root/'models/sound-yamnet/yamnet.h5'
    marker=read(weights.parent/'.ready',{})
    try:return ((root/'.venv-audio/bin/python').is_file() and marker.get('sha256')==WEIGHTS_SHA
                and marker.get('size')==weights.stat().st_size and marker.get('mtime_ns')==weights.stat().st_mtime_ns)
    except OSError:return False


def scan(project,progress=lambda p,label:None):
    source=signature(project['source']);folder=Path(project['folder'])/'multimodal-curation'
    key=hashlib.sha256(json.dumps([VERSION,source,WEIGHTS_SHA],sort_keys=True).encode()).hexdigest()[:24]
    target=folder/('sound-'+key+'.json');saved=read(target,None)
    if isinstance(saved,dict) and saved.get('version')==VERSION and saved.get('source')==source:
        progress(1,'Reusing source-timed sound analysis');return saved
    import av
    with av.open(source['path']) as media:has_audio=bool(media.streams.audio)
    if not has_audio:return dict(version=VERSION,source=source,status='No audio track',frames=[],levels=[])
    if not installed():raise RuntimeError('Sound model missing. Run .venv/bin/python setup_sound.py once.')
    import imageio_ffmpeg
    from local_worker_process import run_local
    with tempfile.TemporaryDirectory(prefix='clipping-sound-') as tmp:
        request=Path(tmp)/'request.json';result=Path(tmp)/'result.json'
        request.write_text(json.dumps(dict(source=source['path'],duration=project['duration'],
            ffmpeg=imageio_ffmpeg.get_ffmpeg_exe(),result=str(result))))
        env=dict(os.environ,TF_CPP_MIN_LOG_LEVEL='2',CUDA_VISIBLE_DEVICES='-1',TF_NUM_INTRAOP_THREADS='2',TF_NUM_INTEROP_THREADS='1',
                 HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        output=run_local([str(ROOT/'.venv-audio/bin/python'),str(ROOT/'sound_worker.py'),str(request)],request,result,env,3600,progress)
    if signature(project['source'])!=source:raise ValueError('The source changed during sound analysis; no cache was saved.')
    saved=dict(output,version=VERSION,source=source,model='YAMNet · local CPU',weights_sha256=WEIGHTS_SHA)
    write(target,saved);return saved


def summarize(scan,ranges):
    """Include only model windows wholly inside retained speech; never bridge a cut."""
    frames=[f for f in scan.get('frames',[]) if any(r['start']<=f['start'] and f['end']<=r['end'] for r in ranges)]
    levels=[f for f in scan.get('levels',[]) if any(r['start']<=f['start'] and f['end']<=r['end'] for r in ranges)]
    if not frames:return dict(available=False,status=scan.get('status','No complete sound windows in this cut'),events=[],score=None)
    speech=sum(any(t['label'] in ('Speech','Conversation','Narration, monologue') and t['score']>=.25 for t in f['tags']) for f in frames)/len(frames)
    reactions=[dict(start=f['start'],end=f['end'],**t) for f in frames for t in f['tags'] if t['label'] in REACTIONS and t['score']>=.25]
    music=sum(any(t['label']=='Music' and t['score']>=.25 for t in f['tags']) for f in frames)/len(frames)
    quiet=sum(f['rms_db']<-45 for f in levels)/len(levels) if levels else None
    return dict(available=True,status='Measured sound windows',speech_fraction=round(speech,3),music_fraction=round(music,3),
        reaction_fraction=round(len({e['start'] for e in reactions})/len(frames),3),quiet_fraction=quiet,
        events=sorted(reactions,key=lambda e:e['score'],reverse=True)[:8],window_count=len(frames),
        rms_db_min=min((f['rms_db'] for f in levels),default=None),rms_db_max=max((f['rms_db'] for f in levels),default=None))
