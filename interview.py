"""Conservative transcript-based question/answer grouping.

These are editing cues, not speaker diarization. Ambiguous context is surfaced
for review; a duration preference never causes padding into another exchange.
"""
import re

QUESTION = re.compile(r'^(?:so[, ]+|and[, ]+|but[, ]+)?(?:how|why|what|when|where|who|which|can you|could you|do you|did you|are you|is there|have you|tell (?:me|us)|talk (?:to us )?about)\b',re.I)
FIRST_PERSON = re.compile(r"\b(?:I|I'm|I've|I'll|we|we're|we've|our|us)\b",re.I)
ANSWER_LEAD = re.compile(r'^(?:yeah|yes|no|absolutely|exactly|well|definitely|sure|right|I mean)\b',re.I)
NAME = re.compile(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+\b')
PRONOUN = re.compile(r'\b(?:he|she|his|her|they|their|that|this|it)\b',re.I)


def is_question(text):
    return '?' in text or bool(QUESTION.search(text.strip()))


def setup_cue(text):
    """Second-person framing or named subjects can introduce a coming question."""
    if re.match(r"^(?:let['’]?s (?:talk|turn|move)|it['’]?s only fitting|moving on|turning to|speaking of)\b",text,re.I):
        return True
    text=re.sub(r"\bI (?:believe|think)\b", "", text, flags=re.I)
    if FIRST_PERSON.search(text) or ANSWER_LEAD.search(text) or is_question(text):
        return False
    return bool(re.search(r'\b(?:your|you mentioned|you had|you said)\b',text,re.I) or NAME.search(text)
                or re.match(r'^(?:against|as for|speaking of|moving on|turning to|nothing new for|now the first)\b',text,re.I))


def intro_start(sentences, question, floor):
    start=question
    for i in range(question-1,max(floor-1,question-4),-1):
        sentence=sentences[i]
        if sentences[question]['start']-sentence['start']>22:
            break
        if sentences[i+1]['start']-sentence['end']>3:
            break
        question_speaker=sentences[question].get('speaker')
        if question_speaker and sentence.get('speaker') and sentence['speaker']!=question_speaker:
            break
        if not setup_cue(sentence['text']):
            break
        start=i
    return start


def exchanges(sentences):
    questions=[i for i,s in enumerate(sentences) if is_question(s['text'])]
    introductions=[intro_start(sentences,q,questions[n-1]+1 if n else 0) for n,q in enumerate(questions)]
    results=[]
    for n,q in enumerate(questions):
        start=introductions[n]
        end=(introductions[n+1]-1) if n+1<len(questions) else len(sentences)-1
        # Measured return to the questioner's voice can delimit declarative next-topic setup.
        asker=sentences[q].get('speaker')
        if asker:
            answer_voice=False
            for j in range(q+1,end+1):
                voice=sentences[j].get('speaker')
                if voice and voice!=asker:answer_voice=True
                elif voice==asker and answer_voice and (setup_cue(sentences[j]['text']) or is_question(sentences[j]['text'])):
                    end=j-1;break
        # The next exchange's question setup is outside this answer.
        if end<=q:
            continue
        answer=sentences[q+1:end+1]
        if not any(len(s['text'].split())>=3 and not is_question(s['text']) for s in answer):
            continue
        results.append({'first':start,'question':q,'last':end})
    return results


def interview_candidates(sentences,minimum,maximum,limit=12):
    results=[]
    for exchange in exchanges(sentences):
        first,q,last=exchange['first'],exchange['question'],exchange['last']
        start,end=sentences[first]['start'],sentences[last]['end']
        length=end-start
        # Never cut an overlong answer halfway through just to hit the target.
        if length<5 or length>maximum:
            continue
        text=' '.join(s['text'] for s in sentences[first:last+1])
        question=sentences[q]['text']
        unresolved=first==q and bool(PRONOUN.search(question)) and not NAME.search(question)
        notes=['One question and its answer; the next detected interviewer setup is excluded.']
        if first<q: notes.append('Included the preceding subject introduction.')
        if length<minimum: notes.append('Shorter than your target to keep one complete exchange.')
        if unresolved:notes.append('The opening may refer to an unnamed subject. Check the context.')
        score=6-abs(length-minimum*1.25)/max(maximum,1)
        if first<q:score+=2
        if unresolved:score-=3
        results.append(dict(first=first,last=last,question=q,start=start,end=end,text=text,rank=score,
            context_uncertain=unresolved,boundary_notes=notes,
            title='Interview exchange',passed=False,reason='Grouped a question with its answer using transcript cues.',
            concern='Transcript-based boundaries need review; speaker changes are inferred, not measured.'))
    return sorted(results,key=lambda c:c['rank'],reverse=True)[:limit]


def interview_content(title,sentences=()):
    if re.search(r'\b(interview|podcast|press conference|media availability|preview|Q&A)\b',title,re.I):
        return True
    return sum(is_question(s['text']) for s in sentences)>=3


def apply_review_ending(candidate,sentences,verdict):
    """Accept only an in-range sentence boundary after the question and answer."""
    last=verdict.get('end_sentence')
    if type(last) is not int or not candidate['question']<last<=candidate['last']:
        raise ValueError('Local review returned an invalid answer boundary.')
    if sum(len(s['text'].split()) for s in sentences[candidate['question']+1:last+1]) < 5:
        raise ValueError('The proposed answer contains too little substantive speech.')
    if is_question(sentences[last]['text']):
        raise ValueError('Local review ended at a question, not an answer.')
    if last<candidate['last']:
        following=sentences[last+1]
        changed_voice=bool(sentences[last].get('speaker') and following.get('speaker') and sentences[last]['speaker']!=following['speaker'])
        transition=bool(re.match(r'^(?:let us discuss|let us move|next topic)\b',following['text'],re.I))
        if not (is_question(following['text']) or setup_cue(following['text']) or changed_voice or transition):
            raise ValueError('No supported topic boundary; preserve the complete answer.')
        candidate['last']=last
        candidate['end']=sentences[last]['end']
        candidate['text']=' '.join(s['text'] for s in sentences[candidate['first']:last+1])
        candidate.setdefault('boundary_notes',[]).append('Local transcript review shortened the ending to keep one topic.')
    return candidate


def apply_review_opening(candidate,sentences,first):
    """Opening edits may remove preceding fragments but never any of the question."""
    if type(first) is not int or not candidate['first']<=first<=candidate['question']:
        raise ValueError('Opening must keep the complete question.')
    question=sentences[candidate['question']]['text']
    # Keep a named subject if the question refers back to that subject.
    removed=' '.join(s['text'] for s in sentences[candidate['first']:first])
    kept=' '.join(s['text'] for s in sentences[first:candidate['question']+1])
    if NAME.search(removed) and PRONOUN.search(question) and not NAME.search(kept):
        raise ValueError('Opening would remove the referenced subject.')
    if first>candidate['first']:
        candidate['first']=first;candidate['start']=sentences[first]['start']
        candidate['text']=' '.join(s['text'] for s in sentences[first:candidate['last']+1])
        candidate.setdefault('boundary_notes',[]).append('Removed preceding dialogue while keeping the full question and its subject.')
    return candidate


def protect_endings(candidates,words,total,padding=.5):
    """Only add verified transcript silence; never shorten the answer or enter the next word."""
    for c in candidates:
        end=c['end']
        # Don't add padding when the selected endpoint lies inside a spoken word.
        if any(w['start']<end<w['end'] for w in words):continue
        next_word=min((w['start'] for w in words if w['start']>=end),default=total)
        padded=min(total,end+padding,max(end,next_word-.08))
        if padded>end+.05:
            c['end']=round(padded,3)
            c.setdefault('boundary_notes',[]).append('Added up to half a second after the answer without including the next transcribed word.')
    return candidates
