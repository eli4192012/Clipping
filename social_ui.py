"""Accounts, per-export drafts, explicit publishing and persistent history."""
import json
from pathlib import Path
from urllib.parse import urlparse
import streamlit as st
import social_store as store
import social_auth as auth
import social_publish as publisher


def accounts_screen():
    st.title('Accounts')
    st.write('Connect a destination once. Review and publish each clip yourself.')
    st.caption('Clipping stays local. Signing in and publishing use the selected platform. Credentials are saved in macOS Keychain.')
    for account in store.accounts():
        with st.container(border=True):
            st.subheader(account['name']);st.caption(account['platform'].title()+' · Connected')
            if st.button('Disconnect',key='disconnect-'+account['id']):
                try:auth.disconnect(account);st.rerun()
                except Exception:st.error('Could not remove Keychain credentials. Try again after unlocking your Keychain.')
    st.caption('Disconnect removes the local login. To revoke access at the platform too, use Google Account permissions or Facebook Business Integrations.')
    yt,ig=st.tabs(['YouTube','Instagram'])
    with yt:
        st.subheader('Connect YouTube')
        with st.expander('First-time Google setup',expanded=True):
            st.markdown('1. Create a Google Cloud project and enable **YouTube Data API v3**.\n2. Configure OAuth consent and add your Google account as a test user.\n3. Create an **OAuth client → Desktop app** and download its JSON.\n4. Upload it below, then connect your channel.')
            st.link_button('Open Google Cloud credentials','https://console.cloud.google.com/apis/credentials')
            st.info('New unaudited API projects may only upload private videos, even when you choose another visibility. Google test-mode logins may also need reconnecting.')
            uploaded=st.file_uploader('Google Desktop OAuth JSON',type=['json'],key='google-client')
            if st.button('Save Google setup',disabled=uploaded is None):
                try:auth.secret('config:youtube',auth.google_config(json.loads(uploaded.getvalue())));st.success('Saved securely in Keychain.')
                except ValueError as e:st.error(str(e))
                except Exception:st.error('Could not save setup to macOS Keychain.')
        if st.button('Connect YouTube'):
            try:st.session_state['social_google']=auth.begin_google()
            except Exception:st.error('Save valid Google setup and unlock Keychain before connecting.')
        pending=st.session_state.get('social_google')
        if pending:
            st.link_button('Sign in with Google',pending['url'])
            st.caption('After signing in, return here. This login expires after 10 minutes.')
            if st.button('Finish connecting YouTube'):
                try:auth.finish_google(pending);st.session_state.pop('social_google',None);st.rerun()
                except auth.SocialError as e:st.error(str(e))
                except Exception:st.error('Connection failed. Start a new login and check Google setup.')
    with ig:
        st.subheader('Connect Instagram')
        st.info('Direct local uploads require a Creator or Business Instagram account linked to a Facebook Page, plus a Meta app with Facebook Login for Business.')
        with st.expander('First-time Meta setup',expanded=True):
            st.markdown('1. Create a Meta Business app with **Instagram API with Facebook Login** and **Facebook Login for Business**.\n2. Create a login configuration using a **User access token**. Include `instagram_basic`, `instagram_content_publish`, `pages_show_list`, and `pages_read_engagement`.\n3. Add your account as an app tester/admin and grant the linked Page. Public users need Meta approval.\n4. Register an HTTPS OAuth redirect URL you control. This local version uses a manual return: after login, copy the redirected address back here.')
            st.caption('Use a simple callback page without analytics or third-party scripts. It should not exchange the code. Keep the redirected address private.')
            st.link_button('Open Meta apps','https://developers.facebook.com/apps/')
            with st.form('meta-setup'):
                app_id=st.text_input('Meta App ID')
                app_secret=st.text_input('Meta App secret',type='password')
                config_id=st.text_input('Facebook Login for Business configuration ID')
                redirect=st.text_input('Registered HTTPS redirect URL',placeholder='https://your-site.example/callback')
                if st.form_submit_button('Save Meta setup'):
                    u=urlparse(redirect)
                    if not app_id.isdigit() or not config_id.isdigit() or not app_secret or u.scheme!='https' or not u.netloc or u.query or u.fragment:
                        st.error('Enter both numeric IDs, an app secret and a valid HTTPS callback URL without query parameters.')
                    else:
                        try:auth.secret('config:instagram',dict(client_id=app_id,client_secret=app_secret,config_id=config_id,redirect_uri=redirect));st.success('Saved securely in Keychain.')
                        except Exception:st.error('Could not save setup to macOS Keychain.')
        if st.button('Connect Instagram'):
            try:st.session_state['social_meta']=auth.begin_meta()
            except Exception:st.error('Save Meta setup and unlock Keychain before connecting.')
        pending=st.session_state.get('social_meta')
        if pending:
            st.link_button('Sign in with Facebook for Instagram',pending['url'])
            with st.form('finish-meta',clear_on_submit=True):
                callback=st.text_input('Paste the full redirected address after login',type='password')
                if st.form_submit_button('Finish connecting Instagram'):
                    try:auth.finish_meta(pending,callback);st.session_state.pop('social_meta',None);st.rerun()
                    except auth.SocialError as e:st.error(str(e))
                    except Exception:st.error('Connection failed. Start a new login and check Meta setup.')
    with st.expander('Setup guide & platform requirements'):
        st.markdown((store.ROOT/'SOCIAL_SETUP.md').read_text())


def draft_panel(draft):
    st.caption('Destination: '+draft['account_name']+' · '+draft['platform'].title())
    st.write('**'+draft['status']+'**')
    if draft.get('error'):st.warning(draft['error'])
    if draft.get('url'):st.link_button('Open on '+draft['platform'].title(),draft['url'])
    if draft.get('project_deleted'):
        st.info('This project was deleted. Posting history is kept, but publishing is disabled for this draft.')
        return
    if draft['status']=='Failed' and '-attempt-' not in draft['id']:
        if st.button('Start a new draft after this failure',key='retry-'+draft['id']):
            try:publisher.retry_failed(draft['id']);st.rerun()
            except auth.SocialError as e:st.error(str(e))
            except Exception:st.error('Could not reset this attempt. The history was preserved.')
    if draft['status']=='Published':
        st.success('Publication confirmed. This clip is marked Used.')
        if draft['platform']=='youtube':st.caption('Actual YouTube visibility: '+draft.get('actual_privacy','unknown'))
        return
    if draft['status']!='Draft':
        if st.button('Check status',key='check-'+draft['id']):
            try:
                with st.spinner('Checking the platform…'):publisher.check(draft['id'])
                st.rerun()
            except auth.SocialError as e:st.error(str(e))
            except Exception:st.error('Could not check status. Your saved attempt is unchanged.')
    resumable=draft['platform']=='youtube' and draft['status'] in ('Uploading','Needs check')
    if draft['status'] in ('Draft','Ready') or resumable:
        with st.expander('Review before publishing',expanded=True):
            if Path(draft['video']).is_file():st.video(draft['video'])
            st.write(draft['title']);st.text(draft['description'])
            st.caption(('Visibility: '+draft['privacy']+' · Made for kids: '+str(draft['made_for_kids'])) if draft['platform']=='youtube' else 'Public Instagram Reel · Share to feed: '+str(draft.get('share_to_feed',True)))
            from clip_usage import clip_key
            duplicates=[d for d in store.drafts(draft['folder']) if d['id']!=draft['id'] and d['account_id']==draft['account_id'] and clip_key(d['run'],d['candidate'])==clip_key(draft['run'],draft['candidate']) and d['status']!='Draft']
            if duplicates:st.warning('This clip already has a posting attempt for this account. Review its status in Publishing history before posting another version.')
            with st.form('confirm-'+draft['id']+'-'+str(draft['updated'])):
                confirmed=st.checkbox('I reviewed this exact video, destination and text and want to publish it now.')
                duplicate_ok=st.checkbox('I checked the previous attempt and intentionally want this additional post.') if duplicates else True
                submit=st.form_submit_button(('Continue publishing to ' if draft['status']!='Draft' else 'Publish to ')+draft['account_name'],type='primary')
            if submit:
                if not confirmed or not duplicate_ok:st.error('Check the review box before publishing.')
                else:
                    progress=st.progress(0,text='Connecting…')
                    try:
                        publisher.publish(draft['id'],lambda p,msg:progress.progress(min(1.,max(0.,p)),text=msg),expected_updated=draft['updated'])
                        st.rerun()
                    except (auth.SocialError,ValueError) as e:st.error(str(e))
                    except Exception:st.error('Publishing could not start. Check account setup and the saved attempt.')


def platform_default_copy(platform,copy):
    """Only defaults for NEW drafts; existing reviewed text remains authoritative."""
    post=copy.get('platforms',{}).get('Instagram Reels') if platform=='instagram' else None
    if post:
        from social_copy import inline_caption
        return dict(title=copy['title'],description=inline_caption(post.get('caption',''),post.get('hashtags',[])))
    return dict(title=copy['title'],description=copy['description'])


def composer(folder,run,candidate,video,render_id,copy):
    with st.expander('Publish to social media'):
        accounts=store.accounts()
        if not accounts:
            st.info('Open Accounts in the sidebar to connect YouTube or Instagram. Your clip and posting copy are already saved.')
            return
        account_id=st.selectbox('Destination account',[a['id'] for a in accounts],format_func=lambda key:next(a['name']+' · '+a['platform'].title() for a in accounts if a['id']==key),key='destination-'+render_id)
        account=next(a for a in accounts if a['id']==account_id)
        key=store.identity(folder,run,candidate,account_id,render_id);draft=store.get(key)
        if draft is None or draft['status']=='Draft':
            initial=draft or dict(platform_default_copy(account['platform'],copy),privacy='private',made_for_kids=None,share_to_feed=True)
            override_key='draft-copy-override-'+key
            suggested=platform_default_copy(account['platform'],copy)
            if draft and any(draft.get(k)!=suggested[k] for k in ('title','description')):
                if st.button('Use current posting text in this draft',key='apply-copy-'+key):
                    st.session_state[override_key]=suggested;st.rerun()
            if override_key in st.session_state:initial=dict(initial,**st.session_state[override_key])
            with st.form('social-draft-'+key):
                title=st.text_input('YouTube title' if account['platform']=='youtube' else 'Draft title · only for your records',value=initial['title'],max_chars=100)
                description=st.text_area('Description' if account['platform']=='youtube' else 'Instagram caption',value=initial['description'],height=150)
                st.caption('Review the suggested text and hashtags; they do not guarantee reach.' if copy.get('platforms') else 'You can add hashtags here if wanted. They are not generated automatically.')
                if account['platform']=='youtube':
                    privacy=st.selectbox('Visibility',['private','unlisted','public'],index=['private','unlisted','public'].index(initial['privacy']))
                    audience=st.selectbox('Is this video made for kids?',['Choose…','Yes','No'],index=0 if initial['made_for_kids'] is None else (1 if initial['made_for_kids'] else 2))
                    kids=None if audience=='Choose…' else audience=='Yes';feed=True
                    st.caption('YouTube may keep uploads private until your Google API project passes its audit.')
                else:
                    feed=st.checkbox('Also share to Instagram feed',value=initial['share_to_feed']);privacy='public';kids=None
                submitted=st.form_submit_button('Save draft & review')
            if submitted:
                new=dict(id=key,folder=str(folder),run=str(run),candidate={'start':candidate['start'],'end':candidate['end']},render_id=render_id,video=str(video),file_size=Path(video).stat().st_size,file_mtime=Path(video).stat().st_mtime_ns,account_id=account_id,account_name=account['name'],platform=account['platform'],title=title.strip(),description=description,privacy=privacy,made_for_kids=kids,share_to_feed=feed,status='Draft')
                try:store.validate(new);store.save_draft(new);st.session_state.pop(override_key,None);st.rerun()
                except ValueError as e:st.error(str(e))
        if draft:draft_panel(draft)


def history_screen():
    st.title('Publishing history')
    st.write('Saved drafts and posting attempts stay here when you close the app. Status checks never create a new post.')
    rows=store.drafts()
    if not rows:st.info('Open a finished clip and choose Publish to social media to create your first draft.')
    for draft in rows:
        with st.expander(draft['title']+' · '+draft['account_name']+' · '+draft['status']):
            draft_panel(draft)
