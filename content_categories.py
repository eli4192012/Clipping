"""User-selected editorial lenses, separate from the processing engine."""
import hashlib,json,re
AUTO='Let AI detect'
GUIDANCE={
'Podcast':'Keep a complete story or argument, including setup, useful detail and payoff.',
'Lifestyle':'Find a practical routine, personal experience or everyday tip with an explained benefit.',
'Vlog':'Preserve a mini story: where the creator is, what happens, and their reaction or outcome.',
'Travel':'Identify the destination and preserve the discovery, experience or actionable travel tip.',
'Food & Cooking':'Keep the dish, necessary ingredients or steps, and the result; avoid cutting mid-instruction.',
'Beauty & Fashion':'Keep the product or outfit context, technique or comparison, and final assessment.',
'Fitness':'Keep exercise setup, technique, safety qualifications and completed demonstration explanation.',
'Sports':'Identify the sport and event; retain setup, outcome and reaction. Commentary alone cannot prove action is visible.',
'Basketball':'Look for possessions, shots, assists, blocks and turning points; preserve buildup and outcome, not only celebration.',
'Soccer':'Look for attacks, goals, saves and tactical turning points; retain the buildup and outcome.',
'American football':'Prioritize complete plays: pre-snap setup, action, outcome and useful reaction; do not start after a touchdown.',
'Marketing & Webinar':'Find a specific problem, strategy, supporting example and actionable takeaway; skip housekeeping and sales filler.',
'Talking head & Speech':'Keep one clear claim with its explanation and conclusion; avoid dependent opening references.',
'Motivational speech':'Preserve the challenge, personal insight and concrete resolution; avoid empty hype or dangling promises.',
'Commentary':'Identify the subject, opinion, supporting evidence and conclusion; preserve uncertainty and context.',
'Interview':'Exactly one question and its complete answer. Never combine follow-ups or multiple questions. Skip weak or context-dependent exchanges; do not pad duration.',
'Entertainment':'Find a self-contained amusing or surprising exchange; preserve the setup and payoff.',
'Movies':'Keep a coherent scene or exchange with character context and resolution; avoid cutting dialogue mid-thought.',
'Drama shows':'Preserve conflict, character context, the meaningful reveal and its immediate reaction.',
'Reality & Talk shows':'Keep the question or situation, the revealing response and reaction as a complete exchange.',
'News':'Retain who, what, where and when plus attribution and uncertainty; do not present speculation as fact.',
'Informative & Educational':'Keep the question or concept, explanation, example and learning takeaway.',
'Product reviews':'Identify the product, testing or comparison evidence and qualified verdict; include material drawbacks.',
'History':'Preserve the time period, people, cause, event and consequence; avoid an isolated unexplained fact.',
'Science & Tech':'Preserve the technical question, explanation or demonstration, evidence and limitations.',
'Music':'Prefer a complete musical discussion or introduction and conclusion; transcript evidence cannot establish musical phrase boundaries.',
'Gaming':'Look for a challenge, strategy, turning point and outcome; spoken reactions alone do not prove gameplay completion.',
'Other':'Find a complete standalone moment with an identified subject and clear conclusion.'}
OPTIONS=[AUTO,*GUIDANCE]

def validate(values):
    values=list(dict.fromkeys(values))
    if not values or len(values)>2 or any(v not in OPTIONS for v in values):raise ValueError('Choose one or two video types.')
    if AUTO in values and len(values)>1:raise ValueError('Use Let AI detect by itself, or choose up to two specific types.')
    return values

def guidance(values):
    return '\n'.join(f'{v}: {GUIDANCE[v]}' for v in sorted(values or []) if v in GUIDANCE)+'\nCombine selected lenses when applicable; a clip need not fit both. Never invent unseen visual evidence.' if values else ''

def route(values):
    if 'Interview' in values or 'Reality & Talk shows' in values:return 'Interview'
    if values==['American football'] or set(values)=={'American football','Sports'}:return 'Sports'
    return 'Podcast'

def cache_tag(settings):
    values=settings.get('categories',[])
    return '-cat'+hashlib.sha256(json.dumps(sorted(values)).encode()).hexdigest()[:10] if values else ''

def inferred(title,sentences,mode):
    text=title+' '+' '.join(s['text'] for s in sentences[:150])
    cues={'Basketball':r'\bbasketball|\bnba\b|slam dunk','Soccer':r'\bsoccer|premier league|goalkeeper','American football':r'\bnfl\b|touchdown|quarterback|colts|texans','Food & Cooking':r'recipe|cooking|ingredients','Travel':r'travel|itinerary|tourist','Fitness':r'workout|exercise|fitness','Beauty & Fashion':r'makeup|skincare|fashion','Gaming':r'gameplay|minecraft|fortnite','Science & Tech':r'science|technology|software','History':r'history|historical','News':r'breaking news|news bulletin','Music':r'concert|musical|songwriting','Product reviews':r'product review|unboxing','Marketing & Webinar':r'webinar|marketing','Vlog':r'\bvlog\b','Lifestyle':r'lifestyle|daily routine','Movies':r'movie|film scene','Drama shows':r'drama series','Motivational speech':r'motivational|motivation','Informative & Educational':r'tutorial|educational|lesson','Commentary':r'commentary|analysis','Entertainment':r'comedy|funny|entertainment','Reality & Talk shows':r'talk show|reality show','Talking head & Speech':r'keynote|speech'}
    hits=sorted(((len(re.findall(pattern,text,re.I)),name) for name,pattern in cues.items()),reverse=True)
    subject=hits[0][1] if hits and hits[0][0]>0 else None
    if mode=='Interview':return ['Interview']+([subject] if subject and subject!='Interview' else [])
    if subject:return [subject]+(['Podcast'] if mode=='Podcast' and subject not in ('Music','Movies','Drama shows','Gaming') else [])
    return ['Sports' if mode=='Sports' else 'Podcast']


def update_selection(key):
    import streamlit as st
    prior=st.session_state.get(key+'-accepted',[AUTO])
    current=list(st.session_state[key])
    added=[v for v in current if v not in prior]
    if AUTO in added:current=[AUTO]
    elif added:current=[v for v in current if v!=AUTO]
    if len(current)>2:
        current=prior
        st.toast('You can select up to two video types.')
    st.session_state[key]=current
    st.session_state[key+'-accepted']=current
