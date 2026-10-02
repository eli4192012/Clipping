import json
import streamlit as st

def show_report(path):
    path=path.with_suffix('.diagnostics.json')
    if not path.exists():return
    report=json.loads(path.read_text());a,b,c=st.columns(3)
    a.metric('Moments found',report['found']);b.metric('Review attempts',report['reviewed']);c.metric('Clips kept',report['kept'])
    st.caption(f"{report['review_succeeded']} windows returned frame descriptions. Found moments are proposals, not verified plays.")
    if report.get('note'):st.caption(report['note'])
    with st.expander('Why were other moments excluded?'):
        if report.get('events'):
            st.dataframe([dict(Time=round(e['anchor'],1),Cue=e['event'],Source=e['origin'],Status=e['status']) for e in report['events']],hide_index=True)
        for e in report['exclusions']:st.write(f"{e['start']:.1f}–{e['end']:.1f}s: {e['reason']}")
        st.caption('Increase Event windows to inspect to review more proposals. Increase the clip limit to keep more eligible results. Overlap and footage limits still apply.')
        st.download_button('Download sports analysis report',path.read_bytes(),'sports-analysis.json','application/json')
