"""Serialized publishing, durable checkpoints and read-only recovery checks."""
from app_logging import log_exception
import fcntl
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse
import social_auth as auth
import social_store as store
PUBLISH_WORKSPACE_API = 3


class UploadBusy(auth.SocialError):pass

@contextmanager
def upload_lock():
    path=store.DB.parent/'social-upload.lock'
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise UploadBusy('Another upload is running. Wait for it to finish.')
        try:yield
        finally:fcntl.flock(lock,fcntl.LOCK_UN)

def checkpoint(draft, **values):
    draft.update(values);store.save(draft)

def account_for(draft):
    account=next((a for a in store.accounts() if a['id']==draft['account_id']),None)
    if not account:raise auth.SocialError('Reconnect the destination account in Accounts.')
    return account

def published(draft, **values):
    checkpoint(draft,status='Published',error='',**values)
    from clip_usage import set_used
    set_used(Path(draft['folder']),draft['run'],draft['candidate'],True)

def trusted_url(url, host):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname!=host or parsed.username or parsed.password or parsed.port not in (None,443):
        raise auth.SocialError('The platform returned an unexpected upload address.')
    return url

def youtube_upload(draft, account, token, update):
    headers={'Authorization':'Bearer '+token};size=Path(draft['video']).stat().st_size
    uri=auth.secret('upload:'+draft['id'])
    if not uri:
        if draft['status']!='Draft':raise auth.SocialError('This attempt has no recoverable upload session. Check YouTube Studio before creating another draft.')
        status={'privacyStatus':draft['privacy'],'selfDeclaredMadeForKids':draft['made_for_kids']}
        if draft.get('publish_at'):
            from social_schedule import future_time
            status.update(privacyStatus='private',publishAt=future_time(draft['publish_at']))
        checkpoint(draft,status='Uploading')
        result=auth.request('POST','https://www.googleapis.com/upload/youtube/v3/videos',params={'uploadType':'resumable','part':'snippet,status'},headers=dict(headers,**{'X-Upload-Content-Length':str(size),'X-Upload-Content-Type':'video/mp4'}),json={'snippet':{'title':draft['title'],'description':draft['description'],'categoryId':'22'},'status':status})
        uri=trusted_url(result.headers.get('Location',''),'www.googleapis.com');auth.secret('upload:'+draft['id'],uri)
    else:
        trusted_url(uri,'www.googleapis.com')
    # Probe before every (re)start; never send a completed video twice.
    response=auth.request('PUT',uri,headers=dict(headers,**{'Content-Range':f'bytes */{size}'}),data=b'')
    if response.status_code in (200,201):
        youtube_uploaded(draft,auth.payload(response));return
    if response.status_code!=308:raise auth.SocialError('Unable to confirm upload position. Check YouTube Studio.')
    if draft.get('publish_at'):
        from social_schedule import future_time
        future_time(draft['publish_at'])
    offset=int(response.headers.get('Range','bytes=0--1').rsplit('-',1)[-1])+1 if 'Range' in response.headers else 0
    checkpoint(draft,status='Uploading',error='')
    with open(draft['video'],'rb') as video:
        while offset<size:
            video.seek(offset);chunk=video.read(8*1024*1024)
            response=auth.request('PUT',uri,headers=dict(headers,**{'Content-Type':'video/mp4','Content-Range':f'bytes {offset}-{offset+len(chunk)-1}/{size}'}),data=chunk)
            if response.status_code in (200,201):
                youtube_uploaded(draft,auth.payload(response));update(1,'Upload received by YouTube; processing will be checked next');return
            if response.status_code!=308:raise auth.SocialError('Unexpected upload response. Use Check status before continuing.')
            next_offset=int(response.headers.get('Range','').rsplit('-',1)[-1])+1
            if next_offset<=offset or next_offset>size:raise auth.SocialError('Upload made no confirmed progress. Check status before continuing.')
            offset=next_offset;update(offset/size,f'YouTube received {offset/size:.0%} of the video')
    raise auth.SocialError('Upload receipt is not confirmed. Check status.')

def youtube_uploaded(draft, result):
    if not result.get('id'):raise auth.SocialError('YouTube did not return a video ID. Check status.')
    status=result.get('status',{})
    checkpoint(draft,status='Scheduled' if draft.get('publish_at') and status.get('publishAt') else 'Processing',
        remote_id=result['id'],url='https://www.youtube.com/watch?v='+result['id'],
        actual_privacy=status.get('privacyStatus',draft['privacy']),remote_publish_at=status.get('publishAt'),error='')

def instagram_upload(draft, account, token, update):
    headers={'Authorization':'Bearer '+token}
    if draft['status']=='Draft':
        checkpoint(draft,status='Uploading')
        result=auth.payload(auth.request('POST',auth.GRAPH+'/'+account['remote_id']+'/media',headers=headers,data={'media_type':'REELS','upload_type':'resumable','caption':draft['description'],'share_to_feed':str(draft.get('share_to_feed',True)).lower()}))
        if not result.get('id') or not result.get('uri'):raise auth.SocialError('Instagram did not return a video upload session.')
        uri=trusted_url(result['uri'],'rupload.facebook.com')
        checkpoint(draft,container_id=result['id'])
        size=Path(draft['video']).stat().st_size
        update(.1,'Sending the finished video to Instagram')
        with open(draft['video'],'rb') as video:
            result=auth.payload(auth.request('POST',uri,headers={'Authorization':'OAuth '+token,'offset':'0','file_size':str(size)},data=video))
        if not result.get('success'):raise auth.SocialError('Instagram has not confirmed the upload. Check status.')
        checkpoint(draft,status='Processing');update(.8,'Instagram is processing the video')
    if draft['status'] not in ('Ready','Processing'):raise auth.SocialError('Check the existing attempt before continuing.')
    for _ in range(5):
        result=auth.payload(auth.request('GET',auth.GRAPH+'/'+draft['container_id'],headers=headers,params={'fields':'status_code'}))
        status=result.get('status_code')
        if status=='PUBLISHED':published(draft);return
        if status=='FINISHED':break
        if status in ('ERROR','EXPIRED'):checkpoint(draft,status='Failed',error='Instagram could not process this container.');return
        time.sleep(2)
    else:
        checkpoint(draft,status='Processing');return
    # Persist before the non-idempotent operation. An uncertain outcome is never retried automatically.
    checkpoint(draft,status='Publishing',publish_requested=True)
    result=auth.payload(auth.request('POST',auth.GRAPH+'/'+account['remote_id']+'/media_publish',headers=headers,data={'creation_id':draft['container_id']}))
    if not result.get('id'):raise auth.SocialError('Publication receipt is missing. Check Instagram before retrying.')
    published(draft,remote_id=result['id'])
    instagram_permalink(draft,headers)
    update(1,'Published to Instagram')

def instagram_permalink(draft,headers):
    if draft.get('remote_id') and not draft.get('url'):
        try:
            result=auth.payload(auth.request('GET',auth.GRAPH+'/'+draft['remote_id'],headers=headers,params={'fields':'permalink'}))
            if result.get('permalink'):checkpoint(draft,url=result['permalink'])
        except auth.SocialError:pass

def publish(draft_id,update=lambda *args:None,expected_updated=None,prevent_duplicate=False,scheduled_due=False):
    with upload_lock():
        draft=store.get(draft_id)
        if not draft:raise ValueError('Draft not found.')
        if expected_updated is not None and draft['updated']!=expected_updated:raise auth.SocialError('This draft changed after your review. Refresh and review it again.')
        local_schedule=scheduled_due and draft.get('schedule_provider')=='local' and draft['platform']=='instagram' and draft['status']=='Scheduled'
        if local_schedule:
            from social_schedule import parse_time
            if parse_time(draft['publish_at']).timestamp()>time.time():raise auth.SocialError('This scheduled post is not due yet.')
        allowed=('Draft','Ready','Scheduled') if local_schedule else ('Draft','Ready') if draft['platform']=='instagram' else ('Draft','Uploading','Needs check')
        if draft['status'] not in allowed:raise auth.SocialError('Check the existing post status before continuing.')
        if prevent_duplicate:
            from clip_usage import clip_key
            for prior in store.drafts(draft['folder']):
                if prior['id']==draft_id or prior['account_id']!=draft['account_id'] or prior['status'] in ('Draft','Failed'):continue
                if Path(prior['video']).resolve()==Path(draft['video']).resolve() or clip_key(prior['run'],prior['candidate'])==clip_key(draft['run'],draft['candidate']):
                    raise auth.SocialError('This clip already has a posting attempt for this account. Check its status before posting again.')
        store.validate(draft);account=account_for(draft)
        if account['platform']!=draft['platform']:raise auth.SocialError('The destination account does not match this draft.')
        original=draft
        store.claim(draft_id,draft['updated'])
        if local_schedule:draft=dict(draft,status='Draft')
        try:token=auth.access(account)
        except Exception as error:
            log_exception('social_publish')
            if local_schedule:store.save(dict(original,status='Schedule failed',error='Reconnect this account, then cancel and schedule the post again.'))
            else:store.save(dict(draft,error=str(error) if isinstance(error,auth.SocialError) else 'Account connection could not be renewed. Open Accounts and reconnect.')) # No upload request has happened; keep its previous state.
            raise
        try:
            if draft['platform']=='youtube':youtube_upload(draft,account,token,update)
            else:instagram_upload(draft,account,token,update)
        except Exception as error:
            log_exception('social_publish')
            # Only expose our allowlisted provider explanations, never raw messages.
            detail=str(error)+' ' if isinstance(error,auth.SocialError) and error.reason in auth.YOUTUBE_ERRORS else ''
            if draft['status']!='Published':checkpoint(draft,status='Needs check',error=detail+'The outcome needs checking. Use Check status; do not create another post until you check the destination.')
            raise auth.SocialError(detail+'Upload interrupted or refused. Your attempt is saved. Use Check status before taking another action.') from None
        return draft

def check(draft_id):
    with upload_lock():
        draft=store.get(draft_id);account=account_for(draft);token=auth.access(account);headers={'Authorization':'Bearer '+token}
        if draft['platform']=='youtube':
            if not draft.get('remote_id'):
                uri=auth.secret('upload:'+draft['id'])
                if not uri:raise auth.SocialError('No upload receipt is available. Check YouTube Studio before starting a new draft.')
                size=Path(draft['video']).stat().st_size
                response=auth.request('PUT',trusted_url(uri,'www.googleapis.com'),headers=dict(headers,**{'Content-Range':f'bytes */{size}'}),data=b'')
                if response.status_code==308:checkpoint(draft,status='Uploading',error='Upload paused. Continue to resume this same upload.');return draft
                youtube_uploaded(draft,auth.payload(response))
            result=auth.payload(auth.request('GET','https://www.googleapis.com/youtube/v3/videos',headers=headers,params={'id':draft['remote_id'],'part':'status,processingDetails'}))
            if not result.get('items'):raise auth.SocialError('Video is not available yet. Check YouTube Studio or check again later.')
            video=result['items'][0];status=video.get('status',{});processing=video.get('processingDetails',{}).get('processingStatus')
            if status.get('uploadStatus') in ('failed','rejected','deleted') or processing in ('failed','terminated'):
                checkpoint(draft,status='Failed',error='YouTube could not publish this upload. See YouTube Studio for details.')
            elif draft.get('publish_at'):
                if status.get('privacyStatus')=='public' and (status.get('uploadStatus')=='processed' or processing=='succeeded'):
                    published(draft,actual_privacy='public')
                elif status.get('publishAt'):
                    checkpoint(draft,status='Scheduled',remote_publish_at=status['publishAt'],actual_privacy=status.get('privacyStatus','private'),error='')
                elif status.get('uploadStatus')=='processed' or processing=='succeeded':
                    checkpoint(draft,status='Needs check',actual_privacy=status.get('privacyStatus','unknown'),error='YouTube has not confirmed a future public release. Check the video and schedule in YouTube Studio.')
                else:checkpoint(draft,status='Processing',error='')
            elif status.get('uploadStatus')=='processed' or processing=='succeeded':
                published(draft,actual_privacy=status.get('privacyStatus',draft['privacy']))
            else:checkpoint(draft,status='Processing',error='')
        elif draft.get('container_id'):
            result=auth.payload(auth.request('GET',auth.GRAPH+'/'+draft['container_id'],headers=headers,params={'fields':'status_code'}))
            code=result.get('status_code')
            if code=='PUBLISHED':published(draft);instagram_permalink(draft,headers)
            elif code=='FINISHED' and not draft.get('publish_requested'):checkpoint(draft,status='Ready',error='Video is ready. Continue publishing to finish.')
            elif code in ('ERROR','EXPIRED'):checkpoint(draft,status='Failed',error='Instagram reported an expired or failed container.')
            # FINISHED after an uncertain media_publish call is intentionally not retried.
            elif draft['status'] not in ('Needs check','Publishing','Published'):checkpoint(draft,status='Processing')
        else:raise auth.SocialError('No container receipt is available. Check Instagram before creating another draft.')
        return draft


def retry_failed(draft_id):
    """Archive a definitive failure before creating a new draft to review."""
    import uuid
    with upload_lock():
        draft=store.get(draft_id)
        if not draft or draft['status']!='Failed':
            raise auth.SocialError('Only a confirmed failed attempt can be reset. Check uncertain outcomes first.')
        auth.forget('upload:'+draft_id)
        archived=dict(draft,id=draft_id+'-attempt-'+uuid.uuid4().hex[:8])
        fresh={k:v for k,v in draft.items() if k not in ('remote_id','container_id','url','actual_privacy','publish_requested','error','publish_at','remote_publish_at','schedule_timezone','schedule_provider','schedule_next_check')}
        fresh.update(status='Draft',updated=time.time())
        with store.connection() as db:
            import json
            db.execute('INSERT INTO drafts VALUES (?,?)',(archived['id'],json.dumps(archived)))
            db.execute('UPDATE drafts SET data=? WHERE id=?',(json.dumps(fresh),draft_id))
