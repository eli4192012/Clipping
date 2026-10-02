"""Local event proposal and visual-boundary review. No media leaves this Mac."""
import json
import re
import subprocess
import sys
import hashlib
from pathlib import Path
from engine import ROOT
VISION = ROOT / 'models' / 'sports-vision'
REVIEW_VERSION = 7
EVENT = re.compile(r'\b(touchdown|intercept(?:ed|ion)?|fumble|home run|scores? a goal|slam dunk)\b', re.I)


def football_hint(title, sentences=()):
    text = title + ' ' + ' '.join(s['text'] for s in sentences)
    return bool(re.search(r'\b(NFL|football|touchdown|quarterback|kickoff|Seahawks|Commanders)\b', text, re.I))


def event_proposals(sentences,total,limit=6):
    from sports_discovery import discover,choose_events
    return choose_events(discover(sentences,total),limit)


def storyboard(source, anchor, total, target):
    import av
    from PIL import Image,ImageDraw
    # Two-second sampling covers 24 seconds before commentary and 22 after.
    start=max(0,anchor-24)
    times=[round(start+i*2,3) for i in range(24) if start+i*2<total]
    sheet=Image.new('RGB',(4*280, ((len(times)+3)//4)*180),'#101010')
    draw=ImageDraw.Draw(sheet)
    with av.open(str(source)) as media:
        for i,t in enumerate(times):
            media.seek(int(t*av.time_base))
            for frame in media.decode(video=0):
                if frame.time is not None and frame.time>=t:
                    pic=frame.to_image();pic.thumbnail((280,156))
                    x,y=i%4*280,i//4*180
                    sheet.paste(pic,(x,y));draw.text((x+6,y+158),f'FRAME {i} | {t:.1f}s',fill='white')
                    break
    sheet.save(target)
    return times


def validate_review(verdict,times,anchor):
    fields=['setup_frame','action_frame','outcome_frame','end_frame']
    indices=[verdict.get(k) for k in fields]
    if any(type(i) is not int or not 0<=i<len(times) for i in indices):
        raise ValueError('Visual review did not return valid frame indices.')
    setup,action,outcome,end=indices
    if not setup<action<=outcome<end or not times[setup]<=anchor+2 or not times[outcome]>=anchor-15:
        raise ValueError('Visual review could not establish an ordered event near the commentary.')
    if times[setup] < anchor-12 or times[action] > anchor+8:
        raise ValueError('The suggested setup or action may belong to another play.')
    if verdict.get('original_action_visible') is not True:
        raise ValueError('The model could not identify the original action, rather than only a replay.')
    return times[setup],times[end]


def visual_candidates(source,sentences,total,folder,limit=6,progress=lambda p,s:None, minimum=10, maximum=35, model_path=None, words=(), samples=(), diagnostics=None):
    model_path=Path(model_path) if model_path else VISION
    if not (model_path/'.ready').exists():
        raise RuntimeError('Vision model missing. Run Download Models.command.')
    from sports_discovery import discover,choose_events
    all_events=discover(sentences,total,words,samples)
    events=choose_events(all_events,limit)
    diagnostics=diagnostics if diagnostics is not None else {}
    diagnostics.update(found=len(all_events),reviewed=0,review_succeeded=0,events=[dict(e,status='queued' if e in events else 'Not reviewed: window limit') for e in all_events])
    results=[]
    for index,event in enumerate(events):
        progress(index/max(1,len(events)),f"Visually reviewing {event['event']} candidate {index+1}/{len(events)}…")
        identity=hashlib.sha256(json.dumps([REVIEW_VERSION,str(model_path),str(source),Path(source).stat().st_mtime_ns,event]).encode()).hexdigest()[:20]
        review_dir=folder/'vision-reviews';review_dir.mkdir(exist_ok=True)
        sheet=review_dir/f'{identity}.jpg';cache=review_dir/f'{identity}.json'
        times=storyboard(source,event['anchor'],total,sheet) if not cache.exists() else json.loads(cache.read_text())['times']
        if cache.exists():
            record=json.loads(cache.read_text())
        else:
            context=[s for s in sentences if s['end']>=times[0] and s['start']<=times[-1]]
            request=review_dir/f'{identity}.request.json'
            request.write_text(json.dumps({'sheet':str(sheet),'event':event,'context':context,'frame_count':len(times),'model_path':str(model_path)}))
            # Separate process releases the model and GPU memory after each review.
            import os
            environment = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
            try:
                run=subprocess.run([sys.executable,str(ROOT/'vision_worker.py'),str(request)],capture_output=True,text=True,timeout=600,env=environment)
                if run.returncode:
                    raise RuntimeError('Local vision worker failed.')
                record={'times':times,'verdict':json.loads(run.stdout)}
                cache.write_text(json.dumps(record,indent=2))
            except (subprocess.TimeoutExpired, RuntimeError, ValueError):
                record={'times':times,'verdict':{'reason':'Visual processing failed or timed out. This draft is based on the commentary location only.'}}
        verdict=record['verdict']
        diagnostics['reviewed']+=1
        diagnostics['review_succeeded']+=int(bool(verdict.get('labels')))
        entry=next(e for e in diagnostics['events'] if e['anchor']==event['anchor'])
        try:
            start,end=boundaries_from_labels(verdict,times,event['anchor'])
            for sentence in sentences:
                if sentence['start'] < end < sentence['end'] <= end+3:
                    end=min(total,sentence['end']+.2)
                    break
            identified=True
            concern='A setup/action/closeup sequence was found, but the model cannot prove a complete play or distinguish every replay. Review before publishing.'
        except ValueError as error:
            # Keep a wide, explicitly uncertain draft instead of pretending to know.
            start,end=uncertain_bounds(verdict,times,event['anchor'],total)
            for sentence in sentences:
                if sentence['start'] < end < sentence['end'] <= end+6:
                    end=min(total,sentence['end']+.2)
                    break
            identified=False;concern=str(error)+' This is a surrounding-context draft.'
        if identified:start=max(0,start-.75)
        if end-start < minimum or end-start > maximum+16:
            entry['status']='Excluded: duration outside target plus context allowance'
            continue
        entry['status']='Draft ready' if verdict.get('labels') else 'Draft ready: visual review failed'
        entry.update(start=start,end=end)
        ids=[i for i,s in enumerate(sentences) if s['end']>start and s['start']<end]
        results.append(dict(first=ids[0] if ids else -1,last=ids[-1] if ids else -1,start=start,end=end,
            text=' '.join(sentences[i]['text'] for i in ids),rank=event['priority']+(3 if identified else 0),passed=False,
            title=event['event'].capitalize()+' · '+('visual draft' if identified else 'uncertain boundaries'),
            reason=str(verdict.get('reason','Visual review returned no explanation.'))[:600],concern=concern,
            visual_reviewed=bool(verdict.get('labels')),visual_sequence=identified,event_anchor=event['anchor'],storyboard=str(sheet),
            boundary_notes=['Reviewed timestamped frames before and after the event commentary.','Frames are sampled every two seconds; nearby commentary can extend the ending.']))
    return results


def boundaries_from_labels(verdict, times, anchor):
    """Find nearest setup -> wide action -> closeup sequence around commentary.

    A closeup is only a possible aftermath cue. It is not proof of a score or of
    live-vs-replay status, so callers always show the result as a review draft.
    """
    labels=verdict.get('labels',[])
    if len(labels)!=len(times):
        raise ValueError('Not all sampled frames could be classified.')
    choices=[]
    for i,label in enumerate(labels):
        if label!='SETUP' or not anchor-24<=times[i]<=anchor:
            continue
        j=i+1
        while j<len(labels) and labels[j]=='SETUP': j+=1
        if j>=len(labels) or labels[j]!='ACTION' or times[j]>anchor+2:
            continue
        k=j
        while k<len(labels) and labels[k]=='ACTION': k+=1
        if k>=len(labels) or labels[k]!='CLOSEUP' or times[k]<anchor-4:
            continue
        end=k+1
        while end<len(labels)-1 and end<k+3 and labels[end]=='CLOSEUP': end+=1
        choices.append((abs(times[j]-anchor),i,j,k,end))
    if not choices:
        raise ValueError('No clear setup-to-action-to-aftermath sequence was found near this event.')
    _,setup,action,outcome,end=min(choices)
    while setup>0 and labels[setup-1]=='SETUP' and times[setup-1]>=anchor-24:setup-=1
    return times[setup],times[end]


def uncertain_bounds(verdict,times,anchor,total):
    """Use visible setup hints for a draft, never promote it to a confirmed event."""
    labels=verdict.get('labels',[])
    if len(labels)!=len(times):
        return max(0,anchor-16),min(total,anchor+12)
    setups=[i for i,label in enumerate(labels) if label=='SETUP' and anchor-10<=times[i]<=anchor]
    if not setups:
        nearby=[i for i,label in enumerate(labels) if label=='ACTION' and abs(times[i]-anchor)<=4]
        if nearby:
            first=last=min(nearby,key=lambda i:abs(times[i]-anchor))
            while first>0 and labels[first-1]=='ACTION' and times[first-1]>=anchor-16:first-=1
            while last+1<len(labels) and labels[last+1]=='ACTION' and times[last+1]<=anchor+12:last+=1
            return max(0,times[first]-2),min(total,times[min(len(times)-1,last+2)])
        return max(0,anchor-16),min(total,anchor+12)
    start_index=max(setups)
    while start_index>0 and labels[start_index-1]=='SETUP' and times[start_index-1]>=anchor-10:
        start_index-=1
    aftermath=next((i for i,label in enumerate(labels) if label=='CLOSEUP' and times[i]>=anchor+2),None)
    end=min(total, times[min(len(times)-1,aftermath+1)]) if aftermath is not None else min(total,anchor+12)
    return times[start_index],end
