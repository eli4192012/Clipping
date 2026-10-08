"""Connect public source channels and inspect automatic clipping without OAuth."""
from datetime import datetime
from pathlib import Path
import time

import streamlit as st
from channel_watch import WatchStore, ensure_watcher, watcher_alive
from clip_queue import QueueStore
from youtube_channels import discover, UPLOAD_LIMIT
from project_store import library, read
CHANNEL_FORM_API = 2


def presets(root):
    from local_editor import preferred_editor
    from sound_analysis import installed as sound_installed
    base = dict(resource_defaults=1,mode='Interview',minimum=30,maximum=120,windows=6,
                vision=False,semantic=True,quality='Balanced',shorts_editor=True,portrait=True,
                coverage=1.,scenes=False,speakers=False,alignment=False,sports_discovery_version=3,
                categories=['Interview','American football'],category_selection=['Interview','American football'],
                auto_mode=False,editor_model=preferred_editor(),multimodal_curation=sound_installed(),curation_windows=3)
    choices = {'Automatic per upload (recommended)':dict(base,watch_auto_type=True,auto_mode=True,category_selection=['Let AI detect']),
               'Colts interviews':base,
               'Podcasts and discussions':dict(base,mode='Podcast',categories=['Podcast'],category_selection=['Podcast']),
               'Football highlights':dict(base,mode='Sports',minimum=10,maximum=35,coverage=.35,vision=True,
                                          semantic=False,shorts_editor=False,scenes=True,
                                          categories=['American football'],category_selection=['American football'])}
    from analysis_settings import AnalysisSettings
    for entry in library(Path(root)/'data'):
        folder = Path(entry['project']['folder'])
        settings = read(folder/'ui-settings.json',{}) or (entry['runs'][0]['settings'] if entry['runs'] else {})
        try:AnalysisSettings.read(settings)
        except ValueError:continue
        choices['Saved: '+entry['project']['title']+' · '+folder.name] = settings
    return choices


def ready(settings):
    from engine import SPEECH
    from upgrades import TURBO, VISION4
    from vision_sports import VISION
    from local_editor import installed, selected_editor
    speech_ready = (TURBO/'.ready').exists() if settings.get('quality')=='Higher quality' else (SPEECH/'model.bin').exists()
    editor_ready = not settings['semantic'] or settings['mode']=='Sports' or installed(selected_editor(settings))
    vision_ready = settings['mode']!='Sports' or not settings['vision'] or (
        (VISION4 if settings.get('quality')=='Higher quality' else VISION)/'.ready').exists()
    return speech_ready and editor_ready and vision_ready


def sports_vision_ready(settings):
    from upgrades import VISION4
    from vision_sports import VISION
    return ((VISION4 if settings.get('quality')=='Higher quality' else VISION)/'.ready').exists()


def show(root, go):
    root = Path(root)
    st.markdown('<div class="eyebrow">NEW UPLOADS TO READY CLIPS</div>',unsafe_allow_html=True)
    st.title('YouTube channels')
    st.write('Connect a public channel. New uploads go straight into your video queue to be clipped and exported.')
    st.caption('No Google sign-in or API key needed. Uses the channel’s Videos tab; Shorts, live streams and upcoming premieres are skipped. Eligible sources are from the last two days, or the newest finished upload if it is older. Checks about every five minutes, including when the browser is closed.')
    choices = presets(root)
    with st.container(border=True):
        st.subheader('Connect a source channel')
        choice = st.selectbox('Clip settings',list(choices))
        template = choices[choice]
        with st.form('connect-youtube-channel'):
            url = st.text_input('YouTube channel link or @handle',value='https://www.youtube.com/@Colts',max_chars=500)
            minimum,maximum = st.slider('Preferred clip length (seconds)',5,180,
                                       (int(template['minimum']),int(template['maximum'])),step=5)
            quality = st.selectbox('Processing quality',['Balanced','Higher quality'],
                                  index=int(template.get('quality')=='Higher quality'))
            portrait = st.checkbox('Export vertical clips (9:16)',value=template.get('portrait',True))
            label = 'Automatic' if template.get('watch_auto_type') else template['mode']
            st.caption(f"{label} · keeps complete ideas and uses the selected settings for each future upload. The duration range is a preference; incomplete ideas are skipped. Reconnecting a channel updates future jobs; waiting jobs retain their saved preferences.")
            if template.get('watch_auto_type'):
                st.caption('Reuses the full transcript and local face samples to choose Interview, Podcast or Sports for each upload. Speech uses your selected length; sports highlights use 10–35 seconds. Detection can be wrong; review the finished clips.')
            st.caption('Connecting also queues eligible existing uploads and starts an idle queue. Exports include captions. A queue you paused stays paused. Nothing is posted automatically.')
            submitted = st.form_submit_button('Connect and start watching',type='primary')
        if submitted:
            settings = dict(template,minimum=minimum,maximum=maximum,quality=quality,portrait=portrait)
            if settings.get('watch_auto_type'):settings['watch_sports_vision']=sports_vision_ready(settings)
            if not ready(settings):st.error('A required local model is missing. Run Download Models.command before connecting.')
            else:
                try:
                    with st.spinner('Finding this public YouTube channel…'):
                        channel = discover(url,limit=1)
                    WatchStore(root).connect(channel,settings)
                    ensure_watcher(root)
                except Exception as error:
                    from app_logging import redact, log_exception
                    log_exception('Connect source channel failed')
                    st.error(redact(str(error)) or 'Could not connect this channel. Check its public link and try again.')
                else:st.success('Watching '+channel['name']+'. Eligible uploads will appear in Video queue.')
    st.caption('Watching prevents idle sleep while the watcher runs. Keep this Mac powered on and online. Closing its lid still requires your keep-awake setup; shutdown stops watching. Opening the app again resumes saved channel watches. Each check looks at the latest '+str(UPLOAD_LIMIT)+' regular uploads.')
    if st.button('Open video queue'):go('queue')
    live_channels(root)


@st.fragment(run_every=3)
def live_channels(root):
    store = WatchStore(root)
    channels = store.channels()
    if not channels:
        st.info('Connect your first channel above to start automatic clipping.')
        return
    ensure_watcher(root)
    enabled = any(c['enabled'] for c in channels)
    if enabled and not watcher_alive(root):st.info('Starting the channel watcher…')
    if QueueStore(root).paused():st.warning('Your video queue is paused. Uploads can still be added; start the queue when you want processing to continue.')
    st.subheader('Connected channels')
    queue = QueueStore(root)
    for channel in channels:
        identity = channel['id']
        with st.container(border=True):
            st.subheader(channel['name'])
            st.caption(('Watching · ' if channel['enabled'] else 'Paused · ')+channel['status'])
            mode = 'Automatic' if channel['settings'].get('watch_auto_type') else channel['settings']['mode']
            st.caption(f"{mode} · {channel['settings'].get('quality','Balanced')} · {channel['settings']['minimum']}–{channel['settings']['maximum']} seconds · automatic exports")
            if channel['checked']:
                st.caption('Last checked '+datetime.fromtimestamp(channel['checked']).strftime('%b %d, %I:%M %p')+
                           (f" · next check in about {max(0,int((channel['next_check']-time.time())/60))} minutes" if channel['enabled'] else ''))
            if channel['error']:st.error(channel['error'])
            a,b,c = st.columns(3)
            if a.button('Pause watching' if channel['enabled'] else 'Resume watching',key='watch-toggle-'+identity):
                store.set_enabled(identity,not channel['enabled']);ensure_watcher(root);st.rerun()
            if b.button('Check now',key='watch-check-'+identity,disabled=not channel['enabled']):
                store.request_check(identity);ensure_watcher(root);st.rerun()
            c.link_button('View source channel',channel['url'])
            st.caption('Pausing watching stops new discoveries. Already queued videos continue unless you also pause Video queue.')
            videos = [v for v in store.videos(identity) if v['state']!='old']
            with st.expander(f'Upload history · {len(videos)}'):
                for video in videos[:30]:
                    item = queue.get(video['queue_id']) if video['queue_id'] else None
                    state = item['state'] if item else video['state']
                    st.write(video['title']+' · '+{'queued':'In video queue','running':'Processing','done':'Complete',
                             'failed':'Needs attention','skipped':'Skipped: too old or unfinished','cancelled':'Removed from queue',
                             'waiting':'Not ready yet','ready':'Waiting to enter queue','error':'Could not read upload'}.get(state,state))
                    error = item['error'] if item else video['error']
                    if error:st.caption(error)
                if len(videos)>30:st.caption('Showing the latest 30 records. All history is retained locally.')
