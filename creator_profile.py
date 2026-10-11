"""Descriptive local review summaries. Never trains or changes automatic choices."""
import collections
import json
import statistics
from pathlib import Path
from project_store import read
from edit_timeline import timeline_duration


def summarize(records):
    usable=[];seen=set()
    for record in sorted(records,key=lambda r:r.get('updated','') if isinstance(r,dict) else '',reverse=True):
        if not isinstance(record,dict):continue
        scores=record.get('scores',{});details=record.get('details',{})
        if not isinstance(scores,dict) or not isinstance(details,dict):continue
        values=[scores.get(k) for k in ('Opening','Ending','Context','Pacing')]
        if any(type(v) is not int or not 1<=v<=5 for v in values):continue
        try:
            duration=timeline_duration(details['ranges']) if details.get('ranges') else float(details['end'])-float(details['start'])
        except (KeyError,TypeError,ValueError):continue
        if duration<=0:continue
        identity=json.dumps([record.get('identity',''),{k:details.get(k) for k in ('quality','start','end','ranges','variant')}],sort_keys=True)
        if identity in seen:continue
        seen.add(identity)
        usable.append((details,values,duration))
    good=[r for r in usable if statistics.mean(r[1])>=4]
    entities=collections.Counter(e for d,_,_ in good for e in d.get('entities',[]) if isinstance(e,str))
    answer=[d['answer_only'] for d,_,_ in good if type(d.get('answer_only')) is bool]
    removal=[d['removed_fraction'] for d,_,_ in good if type(d.get('removed_fraction')) in (int,float) and 0<=d['removed_fraction']<=1]
    return dict(review_count=len(usable),highly_rated_count=len(good),enough_for_patterns=len(good)>=5,
        median_rated_duration=round(statistics.median(r[2] for r in usable),2) if usable else None,
        median_highly_rated_duration=round(statistics.median(r[2] for r in good),2) if good else None,
        answer_only_samples=len(answer),answer_only_count=sum(answer),
        median_removed_fraction=round(statistics.median(removal),3) if removal else None,
        visual_pacing=dict(collections.Counter(d['visual_pacing'] for d,_,_ in good if d.get('visual_pacing'))),
        common_entities=entities.most_common(5),
        basis='Latest human review per cut, stored on this Mac. No learning, ranking changes or preference weights are applied.')


def load(root):
    records=[read(p,{}) for p in Path(root).glob('*/reviews/*.json')]
    return summarize(records)


def show(root):
    import streamlit as st
    profile=load(root)
    with st.expander('My review patterns · local Creator Profile'):
        st.caption(profile['basis'])
        st.write(f"{profile['review_count']} rated cuts · {profile['highly_rated_count']} averaged at least 4/5.")
        if not profile['enough_for_patterns']:
            st.info('Fewer than five highly rated cuts: too little evidence to describe a stable preference. Ratings still have no effect on automatic editing.')
        if profile['median_rated_duration'] is not None:st.write(f"Median rated duration: {profile['median_rated_duration']:.1f}s.")
        if profile['enough_for_patterns']:
            st.write(f"Median highly rated duration: {profile['median_highly_rated_duration']:.1f}s.")
            if profile['answer_only_samples']:st.write(f"Answer-only openings: {profile['answer_only_count']} of {profile['answer_only_samples']} recorded highly rated cuts.")
            if profile['median_removed_fraction'] is not None:st.write(f"Median source-moment footage omitted: {profile['median_removed_fraction']:.0%}. This includes setup and ending, not just filler.")
            if profile['visual_pacing']:st.write('Pacing on highly rated cuts: '+str(profile['visual_pacing']))
            if profile['common_entities']:st.write('Repeated named references: '+', '.join(f'{e} ({n})' for e,n in profile['common_entities']))
        st.caption('Older reviews remain available. Missing framing, answer-only or entity details are not guessed.')
        import json
        st.download_button('Save local profile summary',json.dumps(profile,indent=2),'creator-profile.json','application/json')
