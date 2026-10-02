import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import time
import social_store as store
import social_auth as auth
import social_publish as pub
from clip_usage import is_used

class Response:
    def __init__(self,status=200,data=None,headers=None):self.status_code=status;self.data=data or {};self.headers=headers or {}
    def json(self):return self.data

class SocialTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.patch=patch.object(store,'DB',self.root/'social.sqlite3');self.patch.start()
        self.video=self.root/'clip.mp4';self.video.write_bytes(b'fake video bytes')
        self.account=dict(id='youtube:channel',platform='youtube',remote_id='channel',name='My channel');store.save_account(self.account)
        self.draft=dict(id='draft',folder=str(self.root),run='clips-test.json',candidate={'start':1,'end':5},render_id='render',video=str(self.video),account_id=self.account['id'],account_name=self.account['name'],platform='youtube',title='A good title',description='A complete description',privacy='private',made_for_kids=False,status='Draft')
        store.save(self.draft)
        self.secrets={}
        def secret(k,v=None):
            if v is not None:self.secrets[k]=v;return v
            return self.secrets.get(k)
        self.vault=patch.object(auth,'secret',side_effect=secret);self.vault.start()
        self.access=patch.object(auth,'access',return_value='token');self.access.start()
    def tearDown(self):
        self.access.stop();self.vault.stop();self.patch.stop();self.temp.cleanup()
    def instagram(self):
        self.account.update(id='instagram:ig',platform='instagram',remote_id='ig');store.save_account(self.account)
        self.draft.update(account_id=self.account['id'],platform='instagram');store.save(self.draft)
    def test_drafts_persist_and_cannot_overwrite_started_attempt(self):
        store.validate(self.draft);store.save_draft(self.draft)
        self.assertEqual(store.get('draft')['title'],'A good title')
        store.save(dict(self.draft,status='Uploading'))
        with self.assertRaises(ValueError):store.save_draft(self.draft)
        self.assertEqual(store.get('draft')['status'],'Uploading')
    def test_limits_audience_and_changed_file(self):
        for change in ({'title':'x'*101},{'made_for_kids':None},{'description':'💚'*1300},{'file_size':1}):
            with self.assertRaises(ValueError):store.validate(dict(self.draft,**change))
        self.instagram()
        with self.assertRaises(ValueError):store.validate(dict(self.draft,description='x'*2201))
    def test_google_config_and_callback_state(self):
        with self.assertRaises(ValueError):auth.google_config({'web':{'client_id':'x','client_secret':'y'}})
        c=auth.google_config({'installed':{'client_id':'x','client_secret':'y','token_uri':'https://evil'}})
        self.assertNotIn('token_uri',c)
        pending={'created':time.time(),'state':'safe','redirect_uri':'https://my.example/callback'}
        self.assertEqual(auth.callback_code(pending,'https://my.example/callback?state=safe&code=abc'),'abc')
        for url in ('https://my.example/callback?state=wrong&code=abc','https://evil.example/callback?state=safe&code=abc'):
            with self.assertRaises(auth.SocialError):auth.callback_code(pending,url)
    def test_upload_address_does_not_leak_tokens(self):
        for url in ('http://www.googleapis.com/upload','https://evil.example/upload','https://www.googleapis.com@evil.example/upload'):
            with self.assertRaises(auth.SocialError):pub.trusted_url(url,'www.googleapis.com')
    def test_youtube_processing_then_confirm_used(self):
        calls=[Response(headers={'Location':'https://www.googleapis.com/upload/session'}),Response(308),Response(201,{'id':'posted','status':{'privacyStatus':'private'}})]
        with patch.object(auth,'request',side_effect=calls) as req:
            pub.publish('draft');self.assertEqual(req.call_count,3)
        self.assertEqual(store.get('draft')['status'],'Processing');self.assertFalse(is_used(self.root,self.draft['run'],self.draft['candidate']))
        with patch.object(auth,'request',return_value=Response(data={'items':[{'status':{'uploadStatus':'processed','privacyStatus':'private'}}]})):
            pub.check('draft')
        self.assertEqual(store.get('draft')['status'],'Published');self.assertTrue(is_used(self.root,self.draft['run'],self.draft['candidate']))
        with patch.object(auth,'request') as req:
            with self.assertRaises(auth.SocialError):pub.publish('draft')
            req.assert_not_called()
    def test_youtube_lost_receipt_checks_same_session_without_new_upload(self):
        self.secrets['upload:draft']='https://www.googleapis.com/upload/session';store.save(dict(self.draft,status='Needs check'))
        with patch.object(auth,'request',return_value=Response(201,{'id':'already-uploaded'})) as req:
            pub.publish('draft')
            self.assertEqual(req.call_count,1);self.assertEqual(req.call_args.args[0],'PUT')
        self.assertEqual(store.get('draft')['remote_id'],'already-uploaded')
    def test_youtube_resume_uses_server_offset(self):
        self.secrets['upload:draft']='https://www.googleapis.com/upload/session';store.save(dict(self.draft,status='Uploading'))
        with patch.object(auth,'request',side_effect=[Response(308,headers={'Range':'bytes=0-3'}),Response(201,{'id':'done'})]) as req:
            pub.publish('draft')
            self.assertEqual(req.call_args.kwargs['data'],b' video bytes')
            self.assertTrue(req.call_args.kwargs['headers']['Content-Range'].startswith('bytes 4-'))
    def test_network_failure_is_not_retried(self):
        with patch.object(auth,'request',side_effect=auth.SocialError('interrupted')) as req:
            with self.assertRaises(auth.SocialError):pub.publish('draft')
            self.assertEqual(req.call_count,1)
        self.assertEqual(store.get('draft')['status'],'Needs check')
        self.assertFalse(is_used(self.root,self.draft['run'],self.draft['candidate']))
    def test_instagram_streams_then_publishes(self):
        self.instagram()
        calls=[Response(data={'id':'container','uri':'https://rupload.facebook.com/upload'}),Response(data={'success':True}),Response(data={'status_code':'FINISHED'}),Response(data={'id':'media'}),Response(data={'permalink':'https://www.instagram.com/reel/abc/'})]
        with patch.object(auth,'request',side_effect=calls) as req:
            pub.publish('draft')
            self.assertTrue(hasattr(req.call_args_list[1].kwargs['data'],'read'))
        self.assertEqual(store.get('draft')['status'],'Published')
        self.assertEqual(store.get('draft')['url'],'https://www.instagram.com/reel/abc/')
        self.assertTrue(is_used(self.root,self.draft['run'],self.draft['candidate']))
    def test_instagram_uncertain_publish_never_retries(self):
        self.instagram();store.save(dict(self.draft,status='Needs check',container_id='container',publish_requested=True))
        with patch.object(auth,'request',return_value=Response(data={'status_code':'FINISHED'})) as req:
            pub.check('draft');self.assertEqual(req.call_count,1);self.assertEqual(req.call_args.args[0],'GET')
        self.assertEqual(store.get('draft')['status'],'Needs check')
        with self.assertRaises(auth.SocialError):pub.publish('draft')
    def test_instagram_recover_upload_without_republishing(self):
        self.instagram();store.save(dict(self.draft,status='Needs check',container_id='container'))
        with patch.object(auth,'request',return_value=Response(data={'status_code':'FINISHED'})):
            pub.check('draft')
        self.assertEqual(store.get('draft')['status'],'Ready')
        self.assertFalse(is_used(self.root,self.draft['run'],self.draft['candidate']))
    def test_reviewed_snapshot_cannot_be_replaced(self):
        before=store.get('draft')
        store.save_draft(dict(before,title='Changed in another tab'))
        with self.assertRaises(auth.SocialError):pub.publish('draft',expected_updated=before['updated'])
        current=store.get('draft');store.claim('draft',current['updated'])
        with self.assertRaises(ValueError):store.save_draft(current)
    def test_failed_retry_archives_history_and_requires_new_review(self):
        store.save(dict(self.draft,status='Failed',remote_id='old-video'))
        with patch.object(auth,'forget') as forget:
            pub.retry_failed('draft');forget.assert_called_once_with('upload:draft')
        self.assertEqual(store.get('draft')['status'],'Draft')
        self.assertNotIn('remote_id',store.get('draft'))
        self.assertEqual(len(store.drafts()),2)
        self.assertTrue(any(r.get('remote_id')=='old-video' for r in store.drafts()))
    def test_two_uploads_cannot_run_together(self):
        with pub.upload_lock():
            with self.assertRaises(auth.SocialError):
                with pub.upload_lock():pass
    def test_readonly_check_youtube_rejected_never_marks_used(self):
        store.save(dict(self.draft,status='Processing',remote_id='remote'))
        with patch.object(auth,'request',return_value=Response(data={'items':[{'status':{'uploadStatus':'rejected'}}]})):
            pub.check('draft')
        self.assertEqual(store.get('draft')['status'],'Failed')
        self.assertFalse(is_used(self.root,self.draft['run'],self.draft['candidate']))

if __name__=='__main__':unittest.main()
