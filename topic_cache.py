"""Resume topic work without loading model weights when all results are saved."""
import hashlib,json,time
from pathlib import Path
from project_store import read,write
from topics import interview_topics,topic_candidates,exact_cut_review


def editorial_interview_sources(sentences,maximum):
    from interview_integrity import blocks
    from topics import make_topic
    candidates=[make_topic(sentences,a,b,max(180,maximum)) for a,q,b in blocks(sentences)]
    return [c for c in candidates if c]


def reviewed_topics(payload,load_bundle,progress=None):
    progress=progress or (lambda p,label:None)
    bundle=None
    def model():
        nonlocal bundle
        if bundle is None:bundle=load_bundle()
        return bundle
    folder=Path(payload['cache_dir']) if payload.get('cache_dir') else None
    from local_editor import cache_folder,selected_editor,IDENTITIES
    editor_identity=IDENTITIES[selected_editor(payload,large=bool(payload.get('shorts_editor')))] if payload.get('editor_model') else None
    if folder and payload.get('editor_model'):folder=cache_folder(folder,payload['editor_model'])
    if folder:folder.mkdir(parents=True,exist_ok=True)
    if payload['mode']=='Interview':
        if payload.get('shorts_editor'):
            # These are source neighborhoods, not final question-and-answer clips.
            # The editor may rescue a standalone answer from a multipart exchange.
            candidates=editorial_interview_sources(payload['sentences'],payload['maximum'])
        else:candidates=interview_topics(payload['sentences'],payload['maximum'])
    else:
        inputs=[payload['sentences'],payload['minimum'],payload['maximum'],payload['mode'],payload['quality'],payload.get('categories',[])]
        if payload.get('shorts_editor'):inputs.append('shorts-proposals-1')
        key=hashlib.sha256(json.dumps(inputs+['proposals-v58'],sort_keys=True).encode()).hexdigest()
        path=folder/('proposals-'+key+'.json') if folder else None
        candidates=read(path,None) if path else None
        if not isinstance(candidates,list):
            m,t,g,s=model()
            candidates=topic_candidates(payload['sentences'],payload['minimum'],max(180,payload['maximum']) if payload.get('shorts_editor') else payload['maximum'],payload['mode'],m,t,g,s,progress=lambda p,label:progress(.35*p,label),cache_dir=folder,**({'categories':payload['categories']} if payload.get('categories') else {}))
            # Empty/failed proposals remain retryable rather than poisoning the cache.
            if candidates and path:write(path,candidates)
    reviewed=[]
    durations=[]
    for index,candidate in enumerate(candidates):
        if payload.get('shorts_editor'):
            from shorts_editor import edit_candidate
            remaining=''
            if durations:
                seconds=sum(durations[-5:])/len(durations[-5:])*(len(candidates)-index)
                remaining=f' · about {max(1,round(seconds/60))} min left in this stage (estimate)'
            progress(.35+.65*index/max(1,len(candidates)),f'Editing moment {index+1} of {len(candidates)}'+remaining)
            began=time.monotonic()
            try:
                result=edit_candidate(candidate,payload['sentences'],payload.get('words',[]),payload['maximum'],payload['quality'],
                    str(folder/'shorts') if folder else None,model,
                    progress=lambda p,label,index=index:progress(.35+.65*(index+p)/max(1,len(candidates)),f'Moment {index+1} of {len(candidates)} · {label}'),
                    editor_identity=editor_identity)
            except (ValueError,TypeError,AttributeError,KeyError) as error:
                # An unverified splice never silently becomes the recommended export.
                rejected=candidate.get('context_uncertain',False) or candidate['end']-candidate['start']>payload['maximum']
                if payload['mode']=='Interview':
                    from interview_integrity import verify
                    rejected=rejected or not verify(candidate,payload['sentences'])
                result=dict(candidate,passed=False,boundary_rejected=bool(rejected),shorts_editor_error=str(error),
                    concern='Shorts edit was not verified. This is the unedited original moment; review it manually.',title=candidate.get('title','Moment'))
            reviewed.append(result)
            elapsed=time.monotonic()-began
            if elapsed>1:durations.append(elapsed)
            progress(.35+.65*(index+1)/max(1,len(candidates)),f'Checked edit {index+1} of {len(candidates)}')
            continue
        key=hashlib.sha256(json.dumps([candidate,payload['quality'],payload.get('categories',[]),'exact-review-v514'],sort_keys=True).encode()).hexdigest()
        path=folder/(key+'.json') if folder else None
        result=read(path,None) if path else None
        if not isinstance(result,dict) or not {'text','start','end','passed'}<=result.keys():
            if payload['mode']=='Interview' and candidate.get('context_uncertain'):
                result=dict(candidate,passed=False,boundary_rejected=True,concern='Opening requires an earlier exchange; rejected without loading AI.')
                if path:write(path,result)
                reviewed.append(result)
                progress(.35+.65*(index+1)/max(1,len(candidates)),f'Checked {index+1} of {len(candidates)} moments · missing context rejected')
                continue
            remaining=''
            if durations:
                seconds=sum(durations[-5:])/len(durations[-5:])*(len(candidates)-index)
                remaining=f' · about {max(1,round(seconds/60))} min left in this stage (estimate)'
            progress(.35+.65*index/max(1,len(candidates)),f'Reviewing moment {index+1} of {len(candidates)}'+remaining)
            m,t,g,s=model()
            began=time.monotonic()
            result=exact_cut_review(candidate,m,t,g,s,**({'categories':payload['categories']} if payload.get('categories') else {}))
            durations.append(time.monotonic()-began)
            if path:write(path,result)
        progress(.35+.65*(index+1)/max(1,len(candidates)),f'Checked {index+1} of {len(candidates)} moments')
        if payload['mode']=='Interview':
            from interview_integrity import verify,topic_title
            result['title']=topic_title(result['text'])
            if result.get('context_uncertain') or not verify(result,payload['sentences']):
                result.update(passed=False,boundary_rejected=True,concern='The cut does not contain complete question-and-answer boundaries.')
        reviewed.append(result)
    return reviewed
