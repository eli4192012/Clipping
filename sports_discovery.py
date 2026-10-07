"""Broad, ranked sports proposals. Cues indicate where to look, not confirmed events."""
import re
CUES=[('touchdown',r'\btouchdown\b',10),('turnover',r'\b(?:intercept(?:ed|ion)?|fumble|picked off)\b',9),('sack / pressure',r'\b(?:sack(?:ed)?|sandwiched|brought down|under pressure)\b',7),('big gain',r'\b(?:[2-9]\d[ -]yards?|[2-9]\d[ -]yard|wide open|breaks free|breaks loose|deep ball|downfield)\b',7),('completion',r'\b(?:pass(?:es)? (?:is )?complete|caught|what a catch|makes the catch)\b',5),('first down',r'\bfirst down\b',4),('defensive stop',r'\b(?:loss of|stopped short|nowhere to go|knocked away|pass broken up|incomplete)\b',5),('return / run',r'\b(?:return(?:s|ed)?|high.steps|breaks a tackle|takes off|scrambles?)\b',4)]

def cue_anchor(sentence,pattern,words):
    timed=[w for w in words if w['end']>sentence['start'] and w['start']<sentence['end']]
    if timed:
        text=' '.join(w['text'] for w in timed)
        match=re.search(pattern,text,re.I)
        if match:
            offset=0
            for w in timed:
                if offset+len(w['text'])>match.start():return (w['start']+w['end'])/2
                offset+=len(w['text'])+1
    match=re.search(pattern,sentence['text'],re.I)
    fraction=match.start()/max(1,len(sentence['text'])) if match else .5
    return sentence['start']+(sentence['end']-sentence['start'])*fraction

def discover(sentences,total,words=(),samples=()):
    events=[]
    for i,s in enumerate(sentences):
        for name,pattern,priority in CUES:
            if re.search(pattern,s['text'],re.I):
                events.append(dict(anchor=cue_anchor(s,pattern,words),event=name,text=s['text'],sentence=i,priority=priority,origin='commentary'))
    # A few visual candidates supplement commentary without calling motion a touchdown.
    for start in range(0,int(total),20):
        window=[s for s in samples if start<=s['time']<start+20 and not s['cut']]
        if not window:continue
        strongest=max(window,key=lambda s:s['motion'])
        if strongest['motion']>=.04:
            events.append(dict(anchor=strongest['time'],event='visual activity',text='',sentence=-1,priority=1,origin='motion'))
    grouped=[]
    for e in sorted(events,key=lambda e:(-e['priority'],e['anchor'])):
        if 0<=e['anchor']<total and not any(abs(e['anchor']-old['anchor'])<12 for old in grouped):grouped.append(e)
    return sorted(grouped,key=lambda e:e['anchor'])

def choose_events(events,limit):
    chosen=[];remaining=list(events)
    while remaining and len(chosen)<limit:
        best=max(remaining,key=lambda e:e['priority']+min(3,min((abs(e['anchor']-c['anchor'])/30 for c in chosen),default=0)))
        chosen.append(best);remaining.remove(best)
    return sorted(chosen,key=lambda e:e['anchor'])

def classify_frame(text):
    text=text.lower()
    # A negated setup phrase must never be treated as evidence of a setup.
    cleaned=re.sub(r'\b(?:not|not yet|rather than|instead of)\s+(?:a\s+)?(?:lined up|close[- ]?up|pre-snap|before the snap)[^,.]*','',text)
    if re.search(r'close[- ]?up|close view|portrait',cleaned) and not ('wide view' in cleaned and 'rather than' in text):return 'CLOSEUP'
    if re.search(r'lined up|pre-snap|ready to snap|before the snap',cleaned) and not re.search(r'play in progress|players in motion',cleaned):return 'SETUP'
    if re.search(r'wide|play in progress|running|throwing|tackling|players in motion',cleaned):return 'ACTION'
    return 'OTHER'
