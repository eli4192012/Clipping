"""Conservative exchange boundaries and topic-only headings; no face identification."""
import re
from interview import is_question,setup_cue,ANSWER_LEAD
QUESTION_COUNT_API=2

def question(text):
    text=text.strip()
    if re.search(r'you know what I mean\??\s*$',text,re.I):return False
    if ANSWER_LEAD.search(text):return False
    if '?' not in text and re.match(r'^(?:but|and) when\b',text,re.I):return False
    return is_question(text)

def answer(text):
    text=text.strip()
    # A reporter's qualification is still part of the question.
    if re.match(r'^(?:I mean[, ]+)?(?:both|obviously|with|given|because|like[, ])\b',text,re.I):return False
    return bool(re.match(r'^(?:hey[, ]+)?(?:yeah|yes|no\b|absolutely|well|sure|definitely|I (?:can|can\x27t|think|just|would|want|feel|know|wanted)|we (?:are|have|want)|I mean I)\b',text,re.I))

def setup_start(sentences,q,floor):
    start=q
    for i in range(q-1,max(floor-1,q-5),-1):
        text=sentences[i]['text'].strip()
        if re.match(r'^(?:because|but when)\b',text,re.I):break
        if re.fullmatch(r'(?:yeah|right|okay)[.!]?',text,re.I):continue
        if answer(text) or re.search(r'\b(?:I|we|our)\b',text,re.I) and not re.match(r'^(?:we know|I mean both)\b',text,re.I):break
        if sentences[i+1]['start']-sentences[i]['end']>4:break
        if re.match(r'^(?:he had|she had)\b',text,re.I):continue
        if setup_cue(text) or re.match(r"^[A-Z][a-zA-Z]+(?:,| is |['’]s )",text) or re.search(r"\byou['’]ve (?:talked|been)\b",text,re.I) or re.match(r'^(?:he had|she had|there have been|you talk about|we know|now |with |against )',text,re.I):start=i
        else:break
    return start

def blocks(sentences):
    qs=[i for i,s in enumerate(sentences) if question(s['text'])]
    if not qs:return []
    starts=[setup_start(sentences,q,0 if n==0 else qs[n-1]+1) for n,q in enumerate(qs)]
    exchanges=[];first=starts[0];qend=qs[0]
    for n,q in enumerate(qs[1:],1):
        between=sentences[qend+1:starts[n]]
        substantive=any(answer(s['text']) or (not question(s['text']) and not setup_cue(s['text']) and not re.match(r'^(?:I mean|because|like|both|you|he had|she had)\b',s['text'],re.I) and len(s['text'].split())>=3) for s in between)
        if not substantive:qend=q;continue
        exchanges.append([first,qend,starts[n]-1]);first=starts[n];qend=q
    exchanges.append([first,qend,len(sentences)-1])
    result=[]
    for a,q,b in exchanges:
        # A large transcript hole can hide an unheard reporter question. Do not bridge it.
        for i in range(q+1,b+1):
            if sentences[i]['start']-sentences[i-1]['end']>6:
                b=i-1;break
        if b>q and any(not question(s['text']) and len(s['text'].split())>=3 for s in sentences[q+1:b+1]):result.append([a,q,b])
    return result

def topic_title(text):
    """Never infer a speaker's name, job or identity from an image or model guess."""
    for pattern,title in [
        (r'playbook|miscommunication|communication','Playbook Study and Communication'),
        (r'injur|hurt|recovery','Injury and Availability Discussion'),
        (r'rival|heated|both 0|division games','Preparing for a Division Rivalry'),
        (r'tackl','Improving Tackling and Execution'),
        (r'patience|trust','Patience and Trust in the Play'),
        (r'young|potential|expectation','Development and Expectations'),
        (r'prepar|practice','Preparation and Practice'),
        (r'win|season|game','Approach to the Next Game')]:
        if re.search(pattern,text,re.I):return title
    return 'A Complete Question and Answer'

def question_count(sentences,a,q):
    """Count explicit reporter questions, not punctuation in a player's answer."""
    texts=[s['text'] for s in sentences[a:q+1] if question(s['text'])]
    count=sum(t.count('?') for t in texts)
    joined=' '.join(s['text'] for s in sentences[a:q+1])
    if re.search(r'number one.*number two|first question.*second question',joined,re.I):return max(2,count)
    return count or int(bool(texts))


def speech_question_count(sentences,words=None):
    """Keep a short paused continuation of one unfinished question together."""
    if words is not None:
        expanded=[]
        for sentence in sentences:
            parts=[[]];voice=None
            for i in sentence.get('indices',[]):
                label=words[i].get('speaker')
                if label and voice and label!=voice:parts.append([])
                parts[-1].append(i)
                if label:voice=label
            if not parts[0]:expanded.append(sentence);continue
            for part in parts:
                labels={words[i].get('speaker') for i in part if words[i].get('speaker')}
                expanded.append(dict(text=' '.join(words[i]['text'] for i in part),
                    start=words[part[0]].get('source_start',words[part[0]]['start']),
                    end=words[part[-1]].get('source_end',words[part[-1]]['end']),speaker=next(iter(labels)) if len(labels)==1 else None))
        sentences=expanded
    count=0;previous=None
    for sentence in sentences:
        text=sentence['text'].strip()
        if question(text):
            n=max(1,text.count('?'))
            # Whisper can split "What is ... how you prepare," from
            # "how you study ...?" at a short pause. A completed question,
            # answer, voice change or independent capitalized question cannot
            # use this narrowly defined continuation exception.
            continuation=bool(previous and question(previous['text'])
                and re.search(r'[,;]$',previous['text'].strip())
                and not re.search(r'[.!?]',previous['text'])
                and re.match(r'^(?:how|whether|or|and|that|which)\b',text)
                and 0<=sentence['start']-previous['end']<=1.5
                and not (sentence.get('speaker') and previous.get('speaker')
                         and sentence['speaker']!=previous['speaker']))
            count+=max(0,n-1) if continuation else n
        previous=sentence
    joined=' '.join(s['text'] for s in sentences)
    if re.search(r'number one.*number two|first question.*second question',joined,re.I):count=max(count,2)
    return count


def verify(candidate,sentences):
    """Only one complete question and answer may survive AI review."""
    a,b=candidate.get('first'),candidate.get('last')
    if type(a) is not int or type(b) is not int:return False
    covered=[(start,q,end) for start,q,end in blocks(sentences) if start>=a and end<=b]
    if len(covered)!=1:return False
    start,q,end=covered[0]
    return start==a and end==b and question_count(sentences,start,q)==1
