import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import social_auth as auth
import social_store as store
from test_social import Response
from streamlit.testing.v1 import AppTest


class AuthErrorTests(unittest.TestCase):
    def test_expired_google_renewal_has_a_clear_private_reconnect_message(self):
        response=Response(400,dict(error='invalid_grant',error_description='PRIVATE token=secret credentials'))
        with patch('social_auth.requests.request',return_value=response):
            with self.assertRaises(auth.SocialError) as caught:
                auth.request('POST','https://oauth2.googleapis.com/token',data=dict(refresh_token='secret'))
        error=caught.exception
        self.assertEqual(error.reason,'invalid_grant');self.assertEqual(error.status_code,400)
        self.assertTrue(error.needs_reconnect);self.assertIn('reconnect YouTube',str(error))
        self.assertNotIn('secret',str(error));self.assertNotIn('PRIVATE',str(error))

    def test_bad_app_credentials_have_setup_guidance(self):
        error=auth.response_error(Response(400,dict(error='invalid_client')),'https://oauth2.googleapis.com/token')
        self.assertIn('Desktop OAuth JSON',str(error));self.assertFalse(error.needs_reconnect)

    def test_youtube_known_codes_use_our_messages_without_provider_text(self):
        for reason in ('invalidTitle','invalidDescription','invalidPublishAt','uploadLimitExceeded','quotaExceeded'):
            with self.subTest(reason=reason):
                body=dict(error=dict(message='secret token private URL',errors=[dict(reason=reason,message='secret')]))
                error=auth.response_error(Response(400,body),'https://www.googleapis.com/upload/youtube/v3/videos')
                self.assertEqual(error.reason,reason);self.assertNotIn('secret',str(error))
                self.assertEqual(str(error),auth.YOUTUBE_ERRORS[reason])

    def test_unknown_or_malformed_bodies_never_expose_credentials(self):
        for body in (dict(error='secret'),dict(error=dict(message='secret',errors='secret')),
                     dict(error=dict(errors=[dict(reason=['secret']),dict(reason='secret')])),['secret']):
            with self.subTest(body=body):
                error=auth.response_error(Response(400,body),'https://www.googleapis.com/upload/youtube/v3/videos')
                self.assertEqual(error.reason,None);self.assertIn('HTTP 400',str(error));self.assertNotIn('secret',str(error))
        response=Response(400)
        with patch.object(response,'json',side_effect=ValueError('secret')):
            self.assertIn('HTTP 400',str(auth.response_error(response,'https://www.googleapis.com/upload')))

    def test_known_oauth_words_from_other_hosts_are_not_trusted(self):
        error=auth.response_error(Response(400,dict(error='invalid_grant')),'https://graph.facebook.com/oauth/access_token')
        self.assertFalse(error.needs_reconnect);self.assertIsNone(error.reason)

    def test_renewal_failure_preserves_credentials_and_marks_account_for_reconnect(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(store,'DB',Path(tmp)/'social.sqlite3'):
            account=dict(id='youtube:channel',platform='youtube',name='Channel');store.save_account(account)
            token=dict(refresh_token='private-refresh',access_token='private-access',expires_at=0,client=dict(client_id='private-id',client_secret='private-secret'))
            with patch.object(auth,'secret',return_value=token) as secret,patch('social_auth.requests.request',return_value=Response(400,dict(error='invalid_grant'))):
                with self.assertRaises(auth.SocialError):auth.access(account)
            self.assertEqual(secret.call_count,1)
            saved=store.accounts()[0];self.assertIn('reconnect YouTube',saved['connection_error'])
            self.assertFalse(any('private' in str(value) for value in saved.values()))

    def test_reconnection_replaces_only_the_same_account_and_clears_warning(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(store,'DB',Path(tmp)/'social.sqlite3'):
            store.save_account(dict(id='youtube:channel',platform='youtube',name='Channel',connection_error='Reconnect'))
            store.save_account(dict(id='youtube:another',platform='youtube',name='Another channel'))
            token=dict(access_token='private-access',refresh_token='private-refresh',expires_in=3600)
            with patch('social_auth.time.time',return_value=1),patch.object(auth,'secret',return_value=dict(client_id='private-id',client_secret='private-secret')),patch.object(auth,'request',side_effect=[Response(data=token),Response(data=dict(items=[dict(id='channel',snippet=dict(title='Channel'))]))]):
                auth.finish_google(dict(created=1,code='private-code',verifier='private-verifier',redirect_uri='http://127.0.0.1:123/'))
            accounts={a['id']:a for a in store.accounts()}
            self.assertNotIn('connection_error',accounts['youtube:channel']);self.assertIn('youtube:another',accounts)

    def test_accounts_screen_shows_reconnect_message_and_reuses_existing_setup(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(store,'DB',Path(tmp)/'social.sqlite3'):
            store.save_account(dict(id='youtube:channel',platform='youtube',name='Channel',connection_error=auth.OAUTH_ERRORS['invalid_grant']))
            app=AppTest.from_string('from social_ui import accounts_screen\naccounts_screen()',default_timeout=15).run()
            self.assertFalse(app.exception)
            self.assertTrue(any('reconnect YouTube' in w.value for w in app.warning))
            self.assertTrue(any('saved app setup' in c.value for c in app.caption))
            self.assertTrue(any(b.label=='Connect YouTube' for b in app.button))


if __name__=='__main__':unittest.main()
