"""Human review scores, tied to the exact cut being viewed."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
import streamlit as st
CATEGORIES=['Opening','Ending','Context','Pacing']

def review_form(folder,identity,details):
    key=hashlib.sha256(json.dumps([identity,details],sort_keys=True).encode()).hexdigest()[:20]
    directory=Path(folder)/'reviews';directory.mkdir(exist_ok=True)
    path=directory/(key+'.json');saved=json.loads(path.read_text()) if path.exists() else {}
    with st.expander('Rate this cut'):
        st.caption('Your ratings, not AI predictions. 1 = poor · 5 = excellent. Ratings are saved locally and do not automatically train or rank clips.')
        with st.form('rate-'+key):
            scores={name:st.slider(name,1,5,saved.get('scores',{}).get(name,3),key=key+name) for name in CATEGORIES}
            notes=st.text_area('What worked or needs fixing?',value=saved.get('notes',''),key=key+'notes')
            if st.form_submit_button('Save review'):
                saved=dict(identity=identity,details=details,scores=scores,notes=notes,updated=datetime.now(timezone.utc).isoformat())
                path.write_text(json.dumps(saved,indent=2));st.success('Review saved for this exact cut.')
        if saved:st.caption('Last saved: '+saved['updated'])

def review_history(folder):
    paths=sorted((Path(folder)/'reviews').glob('*.json'))
    if paths:
        with st.expander('Saved review scores'):
            records=[json.loads(p.read_text()) for p in paths]
            st.dataframe([dict(Quality=r['details'].get('quality',''),Start=r['details']['start'],End=r['details']['end'],**r['scores'],Notes=r['notes']) for r in records],hide_index=True)
            st.download_button('Download reviews',json.dumps(records,indent=2),'clip-reviews.json','application/json')
