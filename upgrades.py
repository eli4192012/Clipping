"""Local v2 components, isolated inference and provenance-aware cache names."""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from engine import ROOT
TURBO=ROOT/'models/whisper-turbo'
EDITOR4=ROOT/'models/qwen3-4b'
VISION4=ROOT/'models/sports-vision-4b'
SPEAKERS=ROOT/'models/speakers'

def signature(settings):
    return hashlib.sha256(json.dumps({k:settings.get(k,v) for k,v in [('quality','Balanced'),('scenes',False),('speakers',False),('alignment',False)]},sort_keys=True).encode()).hexdigest()[:10]

def transcript_file(folder,settings):
    if settings.get('quality','Balanced')=='Balanced' and not settings.get('speakers') and not settings.get('alignment'):
        return Path(folder)/'transcript.json'
    canonical=Path(folder)/('transcript-'+signature(dict(settings,scenes=False))+'.json')
    legacy=Path(folder)/('transcript-'+signature(dict(settings,scenes=True))+'.json')
    return legacy if not canonical.exists() and legacy.exists() else canonical

def worker(task,payload,timeout=3600,progress=None):
    with tempfile.TemporaryDirectory(prefix='clipping-') as temp:
        request=Path(temp)/'request.json';result=Path(temp)/'result.json'
        request.write_text(json.dumps(dict(task=task,payload=payload,result=str(result))))
        env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYANNOTE_METRICS_ENABLED='0')
        executable=str(ROOT/'.venv-speech/bin/python') if task=='speech_details' else sys.executable
        from local_worker_process import run_local
        return run_local([executable,str(ROOT/'quality_worker.py'),str(request)],request,result,env,timeout,progress)


def sentences_from_words(words):
    import re
    sentences=[];group=[]
    for i,w in enumerate(words):
        if group and w.get('speaker') and group[-1].get('speaker') and w['speaker']!=group[-1]['speaker']:
            sentences.append(pack(group));group=[]
        group.append(w)
        gap=words[i+1]['start']-w['end'] if i+1<len(words) else 99
        if re.search(r'[.!?]["”’]?$',w['text']) or gap>.8 or len(group)>=65:
            sentences.append(pack(group));group=[]
    if group:sentences.append(pack(group))
    return sentences

def pack(words):
    return dict(start=words[0]['start'],end=words[-1]['end'],text=' '.join(w['text'] for w in words),speaker=words[0].get('speaker'))

def assign_speakers(words,turns):
    for w in words:
        scored=[(max(0,min(w['end'],t['end'])-max(w['start'],t['start'])),t['speaker']) for t in turns]
        if scored and max(scored)[0]>0:w['speaker']=max(scored)[1]
    return words

def scene_times(source,cache):
    from scenedetect import detect,AdaptiveDetector
    cache=Path(cache)
    if cache.exists():return json.loads(cache.read_text())
    scenes=detect(str(source),AdaptiveDetector(),start_in_scene=True)
    cuts=[float(start.get_seconds()) for start,end in scenes if start.get_seconds()>0]
    cache.write_text(json.dumps(cuts));return cuts

def apply_scene_context(candidates,cuts,total):
    # Extend only; never let a camera cut remove action or establish completeness.
    for c in candidates:
        before=[t for t in cuts if c['start']-3<=t<=c['start']]
        if before:
            c['start']=max(0,max(before))
            c.setdefault('boundary_notes',[]).append('Start extended to a nearby detected shot boundary; this does not prove the play is complete.')
    return candidates
