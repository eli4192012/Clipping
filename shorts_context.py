"""Conservative speech context boundaries, using existing timed words only."""
import re

SELECTION_TAG = '-shorts5'


def transition(text):
    return bool(re.match(r"^(?:one (?:other|more) follow[ -]*up|(?:we'll|we will) (?:go with|do a few)|[A-Z][a-z]+,? last question|that's all we've got)\b", text.strip(), re.I)
                or re.fullmatch(r'(?:thank you|thanks(?: for your time)?)(?:,? [A-Za-z]+)?[.!]?', text.strip(), re.I))


def reporter_setup(text):
    return bool(re.match(r"^(?:it (?:does )?seem(?:s)? like|I know you(?:'ve| have) got|we saw you|one (?:other|more) follow[ -]*up)\b", text.strip(), re.I))


def question_ids(sentences, include_confirmations=True):
    """Do not turn an unfinished Whisper clause or an answered rhetorical aside into a new exchange."""
    from interview_integrity import question
    found = []
    for i, sentence in enumerate(sentences):
        text = sentence['text'].strip()
        following=sentences[i+1]['text'].strip() if i+1<len(sentences) else ''
        confirmation=bool(re.search(r'\bso with\b.+?\b(?:for you|as opposed)\b',text,re.I)
            and re.match(r"^(?:that's correct|that is correct|correct|exactly)\b",following,re.I))
        if confirmation:
            if include_confirmations:found.append(i)
            continue  # Keep mixed answer/confirmation utterances in the source neighborhood.
        explicit = question(text)
        if not explicit:
            explicit = bool(re.search(r'\b(?:how (?:do|would) you|how does (?:that|the|a|your)|can you give us|is that a matter)\b', text, re.I)
                or re.match(r'^(?:well|yeah|right|I mean)[, ]+(?:what|why|how|when|can you|could you|do you|did you)\b',text,re.I))
        if not explicit:
            continue
        if '?' not in text and i and not complete_ending(sentences[i-1]['text']) and re.match(r'^(?:where|when|how|what)\b',text):
            continue  # A lowercase continuation of an unfinished sentence, not a new question.
        if re.fullmatch(r"(?:I(?:'m| am) sorry|you know what I mean)[?. ]*", text, re.I):
            continue
        if '?' not in text and re.fullmatch(r'(?:where|when|how|what) (?:we|I|they|he|she) (?:were|was|are|am|have|had)[, ]*', text, re.I):
            continue
        # Explicitly quoted self-reflection inside an answer is not a reporter turn.
        if re.search(r'\bhey[, ]+(?:how can I|how can we)\b',text,re.I):
            continue
        found.append(i)
    return found


def interview_sources(sentences, maximum):
    """One source exchange at a time; the final edit still needs a separate check."""
    from interview_integrity import setup_start
    from topics import make_topic
    qs = question_ids(sentences,include_confirmations=False)
    if not qs:
        return []
    starts = []
    for n,q in enumerate(qs):
        floor=qs[n-1]+1 if n else 0
        start=setup_start(sentences,q,floor)
        # A capitalized "And Tommy" is an answer continuation, not a name introducing a question.
        while start<q and re.match(r'^(?:and|but|so)\b',sentences[start]['text'],re.I):start+=1
        for i in range(start-1,max(floor-1,q-5),-1):
            text=sentences[i]['text'].strip()
            cue=reporter_setup(text) or bool(re.search(r'\b(?:told us yesterday|we saw you|I spoke to|I wanted to follow up|going back to what)\b',text,re.I))
            if not cue or sentences[i+1]['start']-sentences[i]['end']>4:break
            start=i
        while start<q and transition(sentences[start]['text']):start+=1
        starts.append(start)
    groups = []
    first, qend = starts[0], qs[0]
    for n, q in enumerate(qs[1:], 1):
        between = sentences[qend+1:starts[n]]
        substantive = any(len(s['text'].split()) >= 5 and not reporter_setup(s['text'])
                          and not transition(s['text']) for s in between)
        if not substantive:
            qend = q
            continue
        groups.append((first, qend, starts[n]-1))
        first, qend = starts[n], q
    groups.append((first, qend, len(sentences)-1))
    result = []
    for a, q, b in groups:
        for i in range(q+1, b+1):
            if transition(sentences[i]['text']) or sentences[i]['start']-sentences[i-1]['end'] > 6:
                b = i-1
                break
        while b>q and not complete_ending(sentences[b]['text']):b-=1
        if b <= q:
            continue
        candidate = make_topic(sentences, a, b, max(180, maximum))
        if candidate:
            candidate.update(interview_source=True, reporter_question_indices=[i for i in qs if a <= i <= b],
                             boundary_notes=['Source question and answer; moderator transitions excluded.'])
            result.append(candidate)
    return result


def complete_ending(text):
    return bool(re.search(r'[.!?]["\x27”]*$', text.strip()))


def restore_sentences(raw, units, maximum):
    """Balanced edits retain whole utterances, including continuations split at a pause."""
    from shorts_editor import normalize_decision
    decision = normalize_decision(raw, len(units))
    if not isinstance(decision, dict) or not isinstance(decision.get('ranges'), list):
        return raw, []
    keep = set()
    previous=-1
    for span in decision['ranges']:
        a, b = span.get('first'), span.get('last')
        if type(a) is not int or type(b) is not int or not previous < a <= b < len(units):
            return raw, []  # The compiler reports invalid or reordered IDs.
        keep.update(range(a, b+1))
        previous=b
    original = set(keep)
    # A comma-cut planner must not remove the middle of an explanation.
    # Balanced internal cuts are limited to acknowledgements, literal repetition,
    # and explicit discussion references, rather than arbitrary model omissions.
    retained_texts={units[i]['sentence_text'].casefold().strip() for i in keep}
    for u in units[min(keep):max(keep)+1]:
        text=u['sentence_text'].strip()
        neutral=bool(re.fullmatch(r'(?:yeah|right|okay|sure|100%)[.!]?',text,re.I)
            or re.match(r'^(?:we discussed|as we mentioned|as I mentioned)\b.*\b(?:last week|last episode|earlier)\b',text,re.I)
            or u.get('question') and reporter_setup(text))
        repeated=text.casefold() in retained_texts and not any(units[i]['sentence_start']==u['sentence_start'] for i in original)
        if not neutral and not repeated:keep.add(u['id'])
    # Each selected sentence must retain its explanation, not just a comma clause.
    for i in list(keep):
        keep.update(u['id'] for u in units if u['sentence_start'] == units[i]['sentence_start'])
    # Whisper sometimes splits an unfinished sentence at a long pause.
    for i in list(sorted(keep)):
        start = units[i]['sentence_start']
        first = min(u['id'] for u in units if u['sentence_start'] == start)
        while first > 0 and not complete_ending(units[first-1]['sentence_text']):
            previous = units[first-1]['sentence_start']
            keep.update(u['id'] for u in units if u['sentence_start'] == previous)
            first = min(u['id'] for u in units if u['sentence_start'] == previous)
        last = max(u['id'] for u in units if u['sentence_start'] == start)
        while last+1 < len(units) and not complete_ending(units[last]['sentence_text']):
            following = units[last+1]['sentence_start']
            keep.update(u['id'] for u in units if u['sentence_start'] == following)
            last = max(u['id'] for u in units if u['sentence_start'] == following)
    restored = sorted(keep-original)
    if not restored:
        return raw, []
    # Never shorten the restored thought again to satisfy the duration ceiling.
    if sum(units[i]['end']-units[i]['start'] for i in keep) > maximum:
        raise ValueError('The complete explanation exceeds the maximum duration; choose another complete point or raise the maximum.')
    removed = [dict(ids=[u['id']], reason='Outside the selected complete thought.') for u in units if u['id'] not in keep]
    return dict(meaning_preserved=decision.get('meaning_preserved'), ending_complete=decision.get('ending_complete'),
        checks_pending=decision.get('checks_pending'), standalone_context_check=decision.get('standalone_context_check'),
        title=decision.get('title', ''), description=decision.get('description', ''),
        keep_ids=sorted(keep), hook_ids=[min(keep)], payoff_ids=[max(keep)], removed=removed), restored


def structural_check(plan, units, mode):
    """Model approval cannot override broken speech or a second detected question."""
    kept = {i for r in plan['ranges'] for i in range(r['first_unit'], r['last_unit']+1)}
    selected = []
    for u in units:
        if u['id'] in kept and not any(s['start'] == u['sentence_start'] for s in selected):
            selected.append(dict(start=u['sentence_start'], end=u['sentence_end'], text=u['sentence_text'],question=u.get('question',False)))
    first, last = units[min(kept)], units[max(kept)]
    if transition(last['text']) or reporter_setup(last['sentence_text']):
        raise ValueError('The ending is an interviewer setup or transition, not an answer.')
    if not complete_ending(last['text']):
        raise ValueError('The ending stops before the sentence is complete.')
    if re.fullmatch(r'(?:two (?:totally )?different (?:positions|roles|things)|they(?: are|\x27re) (?:totally )?different)[.!]?',last['sentence_text'].strip(),re.I):
        qend=max((i for i,s in enumerate(selected) if s['question']),default=-1)
        explanation=any(len(s['text'].split())>=5 and not reporter_setup(s['text']) for s in selected[qend+1:-1])
        if not explanation:raise ValueError('The comparison ends before explaining what is different.')
    if mode == 'Interview':
        source_questions=[u['id'] for u in units if u.get('question')]
        if source_questions and max(kept)<min(source_questions):
            raise ValueError('Only the question setup was selected; its answer is missing.')
        qs = [i for i,s in enumerate(selected) if s['question']]
        count = sum(max(1, selected[i]['text'].count('?')) for i in qs)
        if count > 1:
            raise ValueError('An interview edit may contain at most one reporter question.')
        if selected and qs and qs[-1] == len(selected)-1:
            raise ValueError('The selected question has no answer.')
    opening = first['text'].strip()
    if first.get('question') and not re.match(r"(?i:^(?:how|why|what|when|where|who|which|can|could|do|did|does|have|has|is|are|was|were|would|will|should|if|so|and|but|hey|well|you|we|I|with|given)\b)|^[A-Z][a-z]+,",opening):
        raise ValueError('The clip opens inside an unfinished interviewer question.')
    # Names elsewhere in the source do not make an isolated "he" opening standalone.
    if re.match(r"^(?:(?:well|yeah|you know)[, ]+)*(?:he|she|his|her|they|their|this guy|that guy|two totally different|when we get an injury)\b", opening, re.I):
        raise ValueError('The opening has lost the subject or comparison; keep its question or choose an opening naming the subject.')
