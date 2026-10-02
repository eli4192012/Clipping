"""Browser OAuth and macOS Keychain storage; never writes tokens to project files."""
import base64
import hashlib
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
import requests
import social_store as store

SERVICE = 'Clipping Social Publishing'
GRAPH = 'https://graph.facebook.com/v25.0'
SCOPES = 'https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly'

class SocialError(Exception):
    pass

def vault():
    # Explicit native backend: never silently fall back to a plaintext keyring.
    from keyring.backends.macOS import Keyring
    return Keyring()

def secret(name, value=None):
    keyring = vault()
    if value is not None:
        keyring.set_password(SERVICE, name, json.dumps(value))
        return value
    raw = keyring.get_password(SERVICE, name)
    return json.loads(raw) if raw else None

def forget(name):
    from keyring.errors import PasswordDeleteError
    try: vault().delete_password(SERVICE, name)
    except PasswordDeleteError: pass

def request(method, url, **kwargs):
    try:
        response = requests.request(method, url, timeout=(15,120), allow_redirects=False, **kwargs)
    except requests.RequestException:
        raise SocialError('Connection interrupted. Check status before trying again.') from None
    if response.status_code >= 400:
        # Do not surface request URLs or raw provider bodies: they can contain credentials.
        if response.status_code == 401:
            raise SocialError('Account permission expired. Reconnect this account.')
        if response.status_code == 403:
            raise SocialError('The platform refused access. Check app permissions, account eligibility and quota.')
        raise SocialError(f'Platform request failed (HTTP {response.status_code}). Check account/app setup and the saved post status.')
    return response

def payload(response):
    try:
        result = response.json()
        if not isinstance(result,dict) or 'error' in result: raise ValueError()
        return result
    except ValueError:
        raise SocialError('The platform returned an unexpected response. Check status before retrying.') from None

def google_config(config):
    c=config.get('installed',{})
    if not c.get('client_id') or not c.get('client_secret'):
        raise ValueError('Choose the downloaded OAuth JSON for a Desktop app, not an API key or Web app.')
    # Use fixed official endpoints, not endpoints supplied by the uploaded file.
    return {'client_id':c['client_id'], 'client_secret':c['client_secret']}

def begin_google():
    config=secret('config:youtube')
    if not config: raise SocialError('Save Google Desktop OAuth settings first.')
    pending={'state':secrets.token_urlsafe(32),'verifier':secrets.token_urlsafe(64),'created':time.time()}
    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            q=parse_qs(urlparse(self.path).query)
            valid=secrets.compare_digest(q.get('state',[''])[0],pending['state'])
            if not valid:
                self.send_response(400); self.end_headers(); self.wfile.write(b'Invalid login state. Return to Clipping.'); return
            pending['error']=bool(q.get('error'))
            pending['code']=q.get('code',[''])[0]
            self.send_response(200); self.send_header('Content-Type','text/plain'); self.end_headers()
            self.wfile.write(b'Return to Clipping and click Finish connecting. You can close this tab.')
            threading.Thread(target=server.shutdown,daemon=True).start()
        def log_message(self,*args): pass
    server=HTTPServer(('127.0.0.1',0),Callback)
    pending['redirect_uri']=f'http://127.0.0.1:{server.server_port}/'
    threading.Thread(target=server.serve_forever,daemon=True).start()
    def expire():
        server.shutdown(); server.server_close()
    timer=threading.Timer(600,expire);timer.daemon=True;timer.start()
    challenge=base64.urlsafe_b64encode(hashlib.sha256(pending['verifier'].encode()).digest()).decode().rstrip('=')
    pending['url']='https://accounts.google.com/o/oauth2/v2/auth?'+urlencode(dict(client_id=config['client_id'],redirect_uri=pending['redirect_uri'],response_type='code',scope=SCOPES,state=pending['state'],code_challenge=challenge,code_challenge_method='S256',access_type='offline',prompt='consent'))
    return pending

def finish_google(pending):
    if time.time()-pending['created']>600: raise SocialError('Login expired. Start again.')
    if pending.get('error'): raise SocialError('Login was cancelled. Start again when ready.')
    if not pending.get('code'): raise SocialError('Complete sign-in in the browser first.')
    config=secret('config:youtube')
    token=payload(request('POST','https://oauth2.googleapis.com/token',data=dict(config,code=pending.pop('code'),code_verifier=pending['verifier'],redirect_uri=pending['redirect_uri'],grant_type='authorization_code')))
    result=payload(request('GET','https://www.googleapis.com/youtube/v3/channels',headers={'Authorization':'Bearer '+token['access_token']},params={'part':'snippet','mine':'true'}))
    if not result.get('items'): raise SocialError('This Google account has no YouTube channel. Create one, then reconnect.')
    channel=result['items'][0]; account={'id':'youtube:'+channel['id'],'platform':'youtube','remote_id':channel['id'],'name':channel['snippet']['title']}
    token['expires_at']=time.time()+token.get('expires_in',3600)
    token['client']=config
    if not token.get('refresh_token'): raise SocialError('No offline permission was returned. Reconnect and allow access.')
    secret(account['id'],token);store.save_account(account)
    return [account]

def begin_meta():
    config=secret('config:instagram')
    if not config:raise SocialError('Save Meta app settings first.')
    pending={'state':secrets.token_urlsafe(32),'created':time.time(),'redirect_uri':config['redirect_uri']}
    pending['url']='https://www.facebook.com/v25.0/dialog/oauth?'+urlencode(dict(client_id=config['client_id'],redirect_uri=config['redirect_uri'],state=pending['state'],config_id=config['config_id'],response_type='code',override_default_response_type='true'))
    return pending

def callback_code(pending,callback):
    if time.time()-pending['created']>600:raise SocialError('Login expired. Start again.')
    u=urlparse(callback); expected=urlparse(pending['redirect_uri']);q=parse_qs(u.query)
    if (u.scheme,u.netloc,u.path)!=(expected.scheme,expected.netloc,expected.path) or not secrets.compare_digest(q.get('state',[''])[0],pending['state']):
        raise SocialError('This callback does not match the login you started.')
    if q.get('error') or not q.get('code'):raise SocialError('Login was cancelled or no authorization code was returned.')
    return q['code'][0]

def finish_meta(pending,callback):
    code=callback_code(pending,callback);config=secret('config:instagram')
    token=payload(request('GET',GRAPH+'/oauth/access_token',params=dict(client_id=config['client_id'],client_secret=config['client_secret'],redirect_uri=config['redirect_uri'],code=code)))
    long=payload(request('GET',GRAPH+'/oauth/access_token',params=dict(grant_type='fb_exchange_token',client_id=config['client_id'],client_secret=config['client_secret'],fb_exchange_token=token['access_token'])))
    headers={'Authorization':'Bearer '+long['access_token']}; accounts=[]; after=None
    while True:
        params={'fields':'id,name,access_token,instagram_business_account{id,username}','limit':100}
        if after:params['after']=after
        pages=payload(request('GET',GRAPH+'/me/accounts',headers=headers,params=params))
        for page in pages.get('data',[]):
            ig=page.get('instagram_business_account')
            if not ig or not page.get('access_token'):continue
            account={'id':'instagram:'+ig['id'],'platform':'instagram','remote_id':ig['id'],'name':'@'+ig.get('username',page['name'])}
            secret(account['id'],{'access_token':page['access_token']})
            store.save_account(account);accounts.append(account)
        if not pages.get('paging',{}).get('next'):break
        after=pages.get('paging',{}).get('cursors',{}).get('after')
        if not after:break
    if not accounts:raise SocialError('No linked Instagram professional account was returned. Check Page access and login permissions.')
    return accounts

def access(account):
    token=secret(account['id'])
    if not token:raise SocialError('Account credentials are missing. Reconnect in Accounts.')
    if account['platform']=='youtube' and token.get('expires_at',0)<time.time()+90:
        fresh=payload(request('POST','https://oauth2.googleapis.com/token',data=dict(token['client'],refresh_token=token['refresh_token'],grant_type='refresh_token')))
        token.update(fresh);token['expires_at']=time.time()+fresh.get('expires_in',3600);secret(account['id'],token)
    return token['access_token']

def disconnect(account):
    forget(account['id']);store.remove_account(account['id'])
