"""Creator-facing Look, Post and Advanced controls for a finished edit."""
import json
from pathlib import Path
from project_store import read, write


def look_form(style,package,words,mode,identity,ranged=False):
    import streamlit as st
    from presentation import LAYOUTS
    st.caption('Choose how this clip looks. Apply style to preview your changes.')
    speakers=sorted({w['speaker'] for w in words if w.get('speaker')})
    if not style.get('packaging_version'):
        st.info('Your saved look is preserved. Apply style to enable these new packaging options.')
    with st.form('look-'+identity):
        layout=st.selectbox('Video layout',LAYOUTS,index=LAYOUTS.index(style['layout']))
        pacing=st.selectbox('Visual pacing',['Off','Subtle','Dynamic'],index=['Off','Subtle','Dynamic'].index(style.get('pacing','Subtle')),disabled=mode=='Sports')
        conversation=st.selectbox('Conversation framing',['Off','Automatic','Active Speaker','Split Screen'],index=['Off','Automatic','Active Speaker','Split Screen'].index(style.get('conversation','Automatic')),disabled=mode=='Sports')
        st.caption('Conversation framing and pacing apply to Portrait · automatic. Manual layouts and crop sliders remain available. Sports keeps its full picture in automatic mode.')
        burn=st.checkbox('Burn highlighted captions into the video',value=style.get('burn',True))
        emphasis=st.checkbox('Emphasize important caption phrases',value=style.get('semantic_emphasis',True))
        treatment=st.selectbox('Emphasis treatment',['Bold','Gentle pop'],index=['Bold','Gentle pop'].index(style.get('emphasis_style','Bold')))
        title=st.text_input('Opening hook · leave blank to hide',value=style.get('title',package['hook']),max_chars=100)
        trim_edges=st.checkbox('Trim verified quiet edges · up to 0.3 seconds per edge',value=style.get('trim_edges',False) and not ranged,disabled=ranged)
        st.caption('Quiet-edge trimming stays optional. It never removes internal pauses or changes the suggested edit.')
        position=st.slider('Speaker crop position / top speaker',0.,1.,float(style.get('position',.5)),step=.05)
        second=st.slider('Bottom speaker position',0.,1.,float(style.get('second',.75)),step=.05)
        mapping={}
        if len(speakers)==2:
            st.caption('Optional active-speaker setup: verify these anonymous transcript labels against the source. A label is not a verified person’s identity.')
            choices=['Unassigned','Left','Right']
            for speaker in speakers:
                old=style.get('speaker_positions',{}).get(speaker,'Unassigned')
                mapping[speaker]=st.selectbox(speaker+' · visible source position',choices,index=choices.index(old) if old in choices else 0)
            confirmed=st.checkbox('I checked these speaker positions against the source',value=style.get('speaker_mapping_confirmed',False) and style.get('speaker_mapping_fingerprint')==package['fingerprint'])
        else:
            confirmed=False
            st.caption('Active-speaker switching needs two anonymous speaker labels and verified visible positions. Without them, automatic framing keeps both visible faces or the full picture.')
        submitted=st.form_submit_button('Apply style')
    updated=dict(style,layout=layout,burn=burn,title=title,position=position,second=second,
        pacing='Off' if mode=='Sports' else pacing,conversation='Off' if mode=='Sports' else conversation,
        semantic_emphasis=emphasis,emphasis_style=treatment,speaker_positions=mapping,trim_edges=trim_edges,
        speaker_mapping_confirmed=confirmed,speaker_mapping_fingerprint=package['fingerprint'] if confirmed else '',packaging_version=1)
    if submitted and confirmed and set(mapping.values())!={'Left','Right'}:
        st.error('Assign one speaker to each position before confirming. The previous style is kept.')
        return style,False
    if st.button('Use suggested hook',key='hook-'+identity,disabled=not package['hook']):
        return dict(style,title=package['hook'],packaging_version=1),True
    if package['hook']:st.caption('Suggested hook: '+package['hook'])
    return (updated,True) if submitted else (style,False)


def post_form(folder,package):
    import streamlit as st
    saved_path=Path(folder)/'platform-posts-v517.json'
    saved=read(saved_path,{})
    key=package['fingerprint'];posts=saved.get(key,package['posting'])
    st.caption('Copy the package for your platform using its code-block copy button. Text is grounded in this final transcript; hashtags do not guarantee reach.')
    for platform in ('YouTube Shorts','TikTok','Instagram Reels'):
        post=posts.get(platform,package['posting'][platform])
        with st.expander(platform+' posting package',expanded=platform=='YouTube Shorts'):
            parts=([post.get('title',''),post.get('description','')] if platform=='YouTube Shorts' else [post.get('caption','')])+[' '.join(post.get('hashtags',[]))]
            st.code('\n\n'.join(p for p in parts if p),language=None,wrap_lines=True)
            with st.form('post-'+key+platform):
                if platform=='YouTube Shorts':
                    title=st.text_input('YouTube title',post.get('title',''),max_chars=100)
                    description=st.text_area('YouTube description',post.get('description',''),max_chars=2000)
                    updated=dict(title=title,description=description)
                else:
                    caption=st.text_area(platform+' caption',post.get('caption',''),max_chars=2000)
                    updated=dict(caption=caption)
                tags=st.text_input(platform+' hashtags',' '.join(post.get('hashtags',[])))
                updated['hashtags']=[t for t in tags.split() if t.startswith('#')][:8]
                if st.form_submit_button('Save '+platform+' text'):
                    saved[key]=dict(posts,**{platform:updated});write(saved_path,saved);st.rerun()
    youtube=posts['YouTube Shorts']
    return dict(title=youtube['title'],description=youtube['description']+ ('\n\n'+' '.join(youtube.get('hashtags',[])) if youtube.get('hashtags') else ''),platforms=posts)


def advanced(package,candidate,words,ranges):
    import streamlit as st
    from shorts_ui import decisions
    decisions(candidate)
    with st.expander('Editorial quality explanation'):
        st.caption('Editorial assessments compare this source’s cuts. No view probabilities, trend data or recommendation-algorithm claims are used. Unknown dimensions stay unscored.')
        st.dataframe(package['assessment'],hide_index=True,use_container_width=True)
        if package.get('corrections_changed_text'):st.warning('Caption corrections changed the final text. Review the corrected captions, hook and posting copy; the saved speech checks do not approve those text changes.')
    with st.expander('B-roll suggestions'):
        st.caption('Output timestamps after internal cuts. Suggestions only: nothing is downloaded, inserted or published. Confirm rights and factual context before choosing supplemental visuals.')
        if package['broll']:st.dataframe(package['broll'],hide_index=True,use_container_width=True)
        else:st.write('No specific supplemental visual was established from this final transcript.')
    with st.expander('Caption emphasis & source ranges'):
        st.dataframe(ranges,hide_index=True)
        st.write(package['emphasis']['phrases'])
        if len(ranges)>1:st.warning('Internal joins passed the saved text checks only. Listen to each join for clipped consonants, unnatural rhythm or a change in meaning.')
        st.caption('No synthesized words, interpolation of speech or sound effects are added to hide cuts.')
        st.download_button('Save packaging decisions',json.dumps(package,indent=2),'clip-package.json','application/json')
