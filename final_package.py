"""Cached, extractive packaging of the final timeline. No inference or network calls."""
import hashlib
import json
import math
import re
from pathlib import Path
from edit_timeline import remap_words, timeline_duration
from project_store import read, write

VERSION = 'final-package-5'
SIGNALS = {
    'contradiction': r'\b(?:best|worst)\b.*\b(?:no|not|never)\b|\b(?:no|not|never)\b.*\b(?:best|worst)\b',
    'surprise': r'\b(?:secret|surprise|unexpected|unbelievable)\b',
    'stakes': r'\b(?:cost|lose|lost|risk|win|won|must|need)\b',
    'opinion': r'\b(?:best|worst|always|never)\b',
    'emotion': r'\b(?:ugly|love|hate|afraid|angry|proud|crazy|incredible)\b',
    'consequence': r'\b(?:because|result|finally|instead|therefore)\b',
}


def tokens(text):
    return re.findall(r"[\w]+(?:['’][\w]+)?", text.casefold())


def contains(text, quote):
    return bool(tokens(quote)) and (' '+ ' '.join(tokens(quote))+' ') in (' '+' '.join(tokens(text))+' ')


def sentences(words):
    groups, group = [], []
    for i, word in enumerate(words):
        previous=words[group[-1]] if group else None
        cut=bool(previous and word.get('segment_id')!=previous.get('segment_id') and
                 word.get('source_start',word['start'])-previous.get('source_end',previous['end'])>.2)
        if group and (cut or word['start']-previous['end'] > .8):
            groups.append(group); group = []
        group.append(i)
        if re.search(r'[.!?]["”\x27]*$', word['text']):
            groups.append(group); group = []
    if group: groups.append(group)
    return [dict(indices=g, start=words[g[0]]['start'], end=words[g[-1]]['end'],
                 text=' '.join(words[i]['text'] for i in g)) for g in groups]


def hook_strength(text):
    found = [name for name, pattern in SIGNALS.items() if re.search(pattern, text, re.I)]
    return 5*('contradiction' in found)+3*('surprise' in found)+len(found)-4*text.rstrip().endswith('?')


def hook_from_final(words):
    """Literal source phrases protect negation and qualifications better than invented slogans."""
    options = []
    for sentence in sentences(words):
        text = sentence['text'].strip()
        if len(text) <= 100:
            options.append(text)
        # Only shorten at a clause boundary; never truncate in the middle of a claim.
        parts=re.split(r'\s+because\s+',text,maxsplit=1,flags=re.I)
        if len(parts)==2 and not re.search(r'\b(?:but|unless|although|however|except)\b',parts[1],re.I):
            if 4<=len(parts[0].split()) and len(parts[0])<=100:options.append(parts[0])
        # Contrasting/conditional/qualified statements must retain their qualifications.
        protected=bool(re.search(r'\b(?:but|if|unless|although|however|except|might|may|could|not|never)\b',text,re.I))
        if not protected:
            for clause in re.split(r'[,;]\s+|\s+because\s+',text,flags=re.I):
                if 4<=len(clause.split())<=14 and len(clause)<=100 and not re.match(r'^(?:and|because|that|which)\b',clause,re.I):
                    options.append(clause)
    if not options:
        return ''  # An unfinished long utterance needs a manually written hook.
    text = max(options, key=lambda t:(hook_strength(t), -len(t)))
    quote=re.sub(r'^(?:so|i mean)[, ]+', '', text, flags=re.I).strip(' ,;:')
    return quote[:1].upper()+quote[1:]


def entities_from_final(text, confirmed=()):
    entities = []
    candidates = list(confirmed)
    candidates += re.findall(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,2}\b', text)
    candidates += [name for name in ('Colts','Texans','Commanders','NFL','NBA','London','YouTube','TikTok') if contains(text,name)]
    for name in candidates:
        name = re.sub(r'^(?:The|So|And|But)\s+', '', str(name)).strip()
        if name and contains(text,name) and name.casefold() not in {n.casefold() for n in entities}:
            entities.append(name)
    return entities[:8]


def semantic_emphasis(words, hook, plan=None):
    """Emphasize a few grounded phrases, never every occurrence of a keyword."""
    text = ' '.join(w['text'] for w in words)
    patterns = [r'\b(?:not|no|never) (?:\w+ ){0,3}(?:at all|cut|win)\b',
                r'\bbest cut\b', r'\bsecret weapon\b', r'\bugly win\b',
                r'\bfound a way\b', r'\bgolden right foot\b', r'\bbubble wrap\b']
    clean = [re.sub(r'[^\w\x27’]', '', w['text']).lower() for w in words]
    matches = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            phrase = tokens(match.group()); n = len(phrase)
            for i in range(len(words)-n+1):
                if clean[i:i+n] == phrase:
                    # Include nearby negation rather than emphasizing an inverted positive claim.
                    begin = i
                    for j in range(max(0,i-3),i):
                        if clean[j] in ('not','no','never'): begin = j; break
                    matches.append(list(range(begin,i+n))); break
    if not matches and hook:
        candidates = [i for i,w in enumerate(words) if contains(hook,w['text']) and
                      len(clean[i]) >= 5 and clean[i] not in ('because','there','which','about','their','would','could','should')]
        if candidates: matches = [[i] for i in candidates[:2]]
    # Prioritize hook/payoff ranges; all indices refer to the FINAL output timeline.
    priority = []
    for r in (plan or {}).get('ranges',[]):
        if r.get('role') in ('hook','payoff','hook_payoff'):
            priority.append((r['start'],r['end']))
    matches.sort(key=lambda g:(not any(a <= words[g[0]].get('source_start',-1)<b for a,b in priority),g[0]))
    budget = max(2, min(12, math.ceil(len(words)/3))); selected = set(); phrases = []
    for group in matches:
        if len(phrases)>=3: break
        fresh = set(group)-selected
        if not fresh or len(selected)+len(fresh)>budget: continue
        selected.update(group)
        phrases.append(dict(start=words[group[0]]['start'],end=words[group[-1]]['end'],
                            text=' '.join(words[i]['text'] for i in group),indices=group))
    return dict(indices=sorted(selected),phrases=phrases,basis='Final hook/payoff phrases and literal language cues')


def posting_packages(text, hook, entities):
    tags = []
    for name in entities:
        tag = '#'+''.join(re.findall(r'\w+',name))
        if tag not in tags: tags.append(tag)
    for phrase in ('secret weapon','best cut','ugly win','bubble wrap'):
        if contains(text,phrase): tags.append('#'+''.join(p.title() for p in phrase.split()))
    groups = re.split(r'(?<=[.!?])\s+',text)
    opening = groups[0] if groups else text
    ending = groups[-1] if len(groups)>1 else ''
    title = hook or (opening if len(opening)<=100 else 'Selected moment')
    quote = '“'+text[:1400]+'”'  # Quoted final transcript, not claims about unseen footage.
    return {
        'YouTube Shorts':dict(title=title[:100],description=quote,hashtags=tags[:3]),
        'TikTok':dict(caption=(hook or opening)[:500],hashtags=tags[:4]),
        'Instagram Reels':dict(caption=('“'+opening+'”'+ ('\n\n'+ending if ending and ending!=opening else '\n\nFrom the conversation.'))[:1800],hashtags=tags[:5]),
    }


def broll_suggestions(words, entities):
    result = []
    for sentence in sentences(words):
        text = sentence['text']
        subject = source_type = None
        if re.search(r'\b(?:score|scoreboard|\d+ to \d+)\b',text,re.I):
            subject = 'Score graphic matching the spoken score'
            source_type = 'An original graphic using verified scores; confirm the event first.'
        elif contains(text,'London'):
            subject = 'London location graphic'
            source_type = 'Your own map/design or properly licensed location footage.'
        elif re.search(r'\b(?:run|running|touchdown|kick|foot|player)\b',text,re.I):
            names = [n for n in entities if contains(text,n)]
            subject = (names[0]+' · illustration of the spoken point') if names else 'Illustration of the spoken play or technique'
            source_type = 'Your own or licensed sports footage, or an original diagram; generic stock does not establish this player or play.'
        if subject and sentence['end']-sentence['start']>=.5:
            result.append(dict(start=round(sentence['start'],3),end=round(sentence['end'],3),subject=subject,
                why='Could clarify this spoken reference: “'+text[:180]+'”',source_type=source_type))
        if len(result)>=3: break
    return result


def editorial_assessment(candidate, words, ranges, mode):
    text = ' '.join(w['text'] for w in words); units = sentences(words)
    review = candidate.get('audience_quality',{}).get('criteria',candidate.get('audience_review',{}))
    checks = (candidate.get('edit_plan') or {}).get('validation',{})
    approved = candidate.get('passed') is True and tokens(text)==tokens(candidate.get('text',''))
    fields = []
    def add(name,status,reason,quote=''):
        fields.append(dict(criterion=name,assessment=status,reason=reason,evidence=quote if contains(text,quote) else ''))
    for name,key in [('Hook Strength','opening'),('Standalone Clarity','clarity'),('Payoff Strength','payoff')]:
        detail = review.get(key,{})
        if mode!='Sports' and type(detail.get('rating')) is int and detail['rating'] in (0,1,2) and contains(text,detail.get('evidence','')):
            add(name,('Weak','Mixed','Strong')[detail['rating']], 'Existing grounded local transcript review.',detail['evidence'])
        else: add(name,'Needs review','No grounded local rating for this final cut.')
    gaps = [b['start']-a['end'] for a,b in zip(words,words[1:]) if a.get('segment_id')==b.get('segment_id')]
    cuts=sum(b['start']-a['end']>.001 for a,b in zip(ranges,ranges[1:]))
    add('Pacing','Inspect joins' if cuts else 'Inspect delivery',
        f"{timeline_duration(ranges):.1f}s · {cuts} internal cuts · {sum(g>1 for g in gaps)} pauses over one second. Shorter is not automatically better.",text[:160])
    entities = entities_from_final(text)
    add('Audience Clarity','Named references' if entities else 'Needs review',
        'Names are in the final speech; intended audience still needs your judgment.' if entities else 'No specific audience can be established from wording alone.',entities[0] if entities else '')
    expressive = next((u['text'] for u in units if re.search(SIGNALS['emotion']+'|'+SIGNALS['surprise'],u['text'],re.I)),'')
    add('Emotional / Personality Strength','Expressive wording' if expressive else 'Needs listening',
        'Literal emotional or surprising language is present; tone was not assessed.' if expressive else 'Text does not establish personality or vocal delivery.',expressive)
    add('Ending Quality','Locally checked' if approved and mode!='Sports' and checks.get('complete_ending') is True else 'Needs review',
        'The saved final-transcript check passed. Listen to the actual ending.' if approved and checks.get('complete_ending') else 'No complete ending check for this final cut.',units[-1]['text'] if units else '')
    add('Overall Editorial Quality','Text approved · media review needed' if approved and mode!='Sports' else 'Draft · needs review',
        'Use these assessments to compare cuts from this source. They do not predict reach, retention or virality.')
    return fields


def edit_fingerprint(source, ranges, words, candidate, mode, confirmed):
    stat = Path(source).stat()
    body = [VERSION,str(Path(source).resolve()),stat.st_size,stat.st_mtime_ns,ranges,words,
            candidate.get('edit_plan'),candidate.get('audience_quality'),candidate.get('passed'),mode,list(confirmed)]
    return hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]


def get_package(folder, source, candidate, source_words, ranges, mode, confirmed=()):
    words = remap_words(source_words,ranges)
    key = edit_fingerprint(source,ranges,words,candidate,mode,confirmed)
    path = Path(folder)/'packaging-v517'/(key+'.json')
    saved = read(path,None)
    if isinstance(saved,dict) and saved.get('version')==VERSION: return saved
    text = ' '.join(w['text'] for w in words)
    hook = hook_from_final(words); entities = entities_from_final(text,confirmed)
    package = dict(version=VERSION,fingerprint=key,final_transcript=text,hook=hook,entities=entities,
        corrections_changed_text=tokens(text)!=tokens(candidate.get('text','')),
        emphasis=semantic_emphasis(words,hook,candidate.get('edit_plan')),sentences=sentences(words),
        posting=posting_packages(text,hook,entities),broll=broll_suggestions(words,entities),
        assessment=editorial_assessment(candidate,words,ranges,mode))
    write(path,package)
    return package
