"""Controlled interview comparison: same transcript, same exchange, two reviewers."""
import copy
import hashlib
import json
from pathlib import Path
from engine import export_clip
from interview import interview_candidates,protect_endings
from jobs import get_transcript
from upgrades import worker,transcript_file
from modes import VERSION

def target_candidate(sentences,target,maximum):
    matches=[c for c in interview_candidates(sentences,5,maximum,limit=None) if c['start']<=target<=c['end']]
    if not matches:raise ValueError('No complete interview exchange contains that timestamp within the chosen duration limit. Choose a time inside a question or answer, or increase the limit.')
    return min(matches,key=lambda c:c['end']-c['start'])

def compare(project,settings,target,progress):
    transcript=get_transcript(project,settings,lambda p,label:progress(p*.4,label))
    seed=target_candidate(transcript['sentences'],target,settings['maximum'])
    source=Path(project['source']);tp=transcript_file(project['folder'],settings)
    identity=hashlib.sha256(json.dumps([VERSION,float(target),str(source),source.stat().st_mtime_ns,tp.read_text(),seed,settings['portrait']],sort_keys=True).encode()).hexdigest()[:20]
    folder=Path(project['folder'])/'comparisons';folder.mkdir(exist_ok=True)
    output=folder/(identity+'.json')
    if output.exists():
        saved=json.loads(output.read_text())
        if all(Path(c['video']).exists() and Path(c['captions']).exists() for c in saved['results']):
            progress(1,'Saved comparison ready');return str(output)
    results=[]
    for index,quality in enumerate(['Balanced','Higher quality']):
        progress(.24+index*.35,'Reviewing the same exchange · '+quality)
        reviewed=worker('review',dict(sentences=transcript['sentences'],candidates=[copy.deepcopy(seed)],mode='Interview',quality=quality))
        if len(reviewed)!=1 or reviewed[0]['question']!=seed['question']:raise ValueError('Reviewer returned a different exchange.')
        c=protect_endings(reviewed,transcript['words'],project['duration'])[0]
        progress(.44+index*.35,'Rendering comparison · '+quality)
        video,captions=export_clip(source,c['start'],c['end'],transcript['words'],settings['portrait'])
        results.append(dict(quality=quality,candidate=c,video=str(video),captions=str(captions)))
    report=dict(version='2.2',source=str(source),target=target,question=transcript['sentences'][seed['question']]['text'],transcript=str(tp),transcript_quality=settings.get('quality','Balanced'),results=results)
    output.write_text(json.dumps(report,indent=2));progress(1,'Comparison ready')
    return str(output)
