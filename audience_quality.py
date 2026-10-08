"""Transparent editing heuristics, not a model of YouTube's recommendation system."""
import re

RUBRIC_VERSION = 'audience-v1'
CRITERIA = ('opening', 'clarity', 'value', 'payoff')
CURATION_API=1


def validated_review(raw, text):
    """Accept only complete ratings with evidence actually present in this cut."""
    if not isinstance(raw, dict):
        return None
    result = {}
    normalized = ' '.join(text.casefold().split())
    for name in CRITERIA:
        item = raw.get(name)
        if not isinstance(item, dict) or type(item.get('rating')) is not int or item['rating'] not in (0, 1, 2):
            return None
        quote = item.get('evidence')
        if not isinstance(quote, str) or not quote.strip() or ' '.join(quote.casefold().split()) not in normalized:
            return None
        result[name] = dict(rating=item['rating'], evidence=quote[:250])
    return result


def annotate(candidates, mode):
    for item in candidates:
        text = item.get('text', '').strip()
        review = validated_review(item.get('audience_review'), text) if mode != 'Sports' else None
        if mode == 'Sports':
            # Commentary alone does not demonstrate that the action is in the clip.
            sequence = item.get('visual_sequence') is True
            item['audience_quality'] = dict(version=RUBRIC_VERSION, basis='Sampled visual cues', score=2 if sequence else 0,
                reason='Sampled frames suggest setup, action and aftermath; check that the actual play is complete.' if sequence else 'The complete action is not visually established; review the play before posting.')
        elif review:
            # These are our editorial priorities, deliberately not YouTube weights.
            score = review['opening']['rating'] + 2*review['clarity']['rating'] + 2*review['value']['rating'] + 3*review['payoff']['rating']
            strengths = [name for name in CRITERIA if review[name]['rating'] == 2]
            weaknesses = [name for name in CRITERIA if review[name]['rating'] == 0]
            reason = ('Strong: '+', '.join(strengths)+'. ') if strengths else ''
            reason += ('Needs review: '+', '.join(weaknesses)+'.') if weaknesses else 'No major weakness identified in the transcript review.'
            item['audience_quality'] = dict(version=RUBRIC_VERSION, basis='Local transcript review', score=score, reason=reason, criteria=review)
        else:
            dependent = bool(re.match(r'^(?:he|she|it|they|that|this|because)\b', text, re.I))
            closed = bool(re.search(r'[.!]["”\x27]*$', text))
            item['audience_quality'] = dict(version=RUBRIC_VERSION, basis='Basic text checks', score=int(not dependent)+int(closed),
                reason='Only opening wording and sentence punctuation were checked. Story value and payoff need your review.')
    return candidates


def selection_key(item):
    quality = item.get('audience_quality', {})
    from multimodal_curation import valid_priority
    score=item['multimodal_curation']['ranking_score'] if valid_priority(item) else quality.get('score',0)
    return (item.get('passed', False), quality.get('basis') == 'Local transcript review', score, item.get('rank', 0))


def weak_value(item):
    criteria = item.get('audience_quality', {}).get('criteria', {})
    return bool(criteria) and criteria.get('value',{}).get('rating') == 0 and criteria.get('payoff',{}).get('rating') == 0


def show_report(item):
    import streamlit as st
    quality = item.get('audience_quality')
    if not quality:
        return
    with st.expander('Why this moment was selected'):
        st.write(quality['reason'])
        st.caption(quality['basis']+' · Editing estimate, not a prediction of views. No live trends or channel analytics were used.')
        labels = {0:'Weak', 1:'Mixed', 2:'Strong'}
        for name, detail in quality.get('criteria', {}).items():
            st.write(f"**{name.title()} · {labels[detail['rating']]}**")
            st.text(detail['evidence'])
