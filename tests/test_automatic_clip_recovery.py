import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from clip_queue import QueueStore, AUTO_RETRY_LIMIT
from queue_runner import run
from youtube_import import download, HLS_FORMAT
from yt_dlp.utils import DownloadError

SETTINGS=dict(mode='Interview',minimum=30,maximum=120,windows=6,vision=False,semantic=True,
              quality='Balanced',shorts_editor=True,portrait=True)
META=dict(id='vid00000001',url='https://www.youtube.com/watch?v=vid00000001',title='Upload',
          duration=300,channel_id='UC'+'a'*22,published=100)


class AutomaticRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=QueueStore(self.root)

    def tearDown(self):self.tmp.cleanup()

    def test_transient_failure_retries_after_delay_and_processes_other_upload_first(self):
        first,_=self.store.add_youtube(META,SETTINGS)
        second,_=self.store.add_youtube(dict(META,id='vid00000002',url='https://www.youtube.com/watch?v=vid00000002'),SETTINGS)
        calls=[]
        def process(store,item):
            calls.append(item['id'])
            if item['id']==first['id']:
                store.update(item['id'],result='cached.json',exports=[dict(video='retained.mp4')])
                raise TimeoutError('Local analysis reached its time limit. Completed reviews are saved; retry to resume them.')
        self.store.set_enabled(True);before=time.time();run(self.root,process)
        retry=self.store.get(first['id'])
        self.assertEqual(calls,[first['id'],second['id']])
        self.assertEqual(retry['state'],'queued');self.assertEqual(retry['auto_retries'],1)
        self.assertGreaterEqual(retry['retry_at'],before+60)
        self.assertEqual(retry['result'],'cached.json');self.assertEqual(retry['exports'],[dict(video='retained.mp4')])
        self.assertEqual(self.store.get(second['id'])['state'],'done')
        self.store.auto_start();self.assertFalse(self.store.enabled())
        with patch('clip_queue.time.time',return_value=retry['retry_at']+1):
            self.store.auto_start();run(self.root,lambda store,item:None)
        self.assertEqual(self.store.get(first['id'])['state'],'done')

    def test_automatic_retries_are_bounded_and_manual_retry_resets_budget(self):
        item,_=self.store.add_youtube(META,SETTINGS);self.store.set_enabled(True)
        for count in range(AUTO_RETRY_LIMIT):
            claimed=self.store.claim()
            self.assertIsNotNone(claimed)
            self.assertTrue(self.store.retry_upload(item['id'],'HTTP Error 503',now=0))
            self.assertEqual(self.store.get(item['id'])['auto_retries'],count+1)
        self.store.claim();self.assertFalse(self.store.retry_upload(item['id'],'HTTP Error 503'))
        self.store.finish(item['id'],'HTTP Error 503')
        self.store.retry_failed_uploads([META['channel_id']]);self.assertEqual(self.store.get(item['id'])['state'],'failed')
        self.assertTrue(self.store.retry(item['id']))
        self.assertEqual(self.store.get(item['id'])['auto_retries'],0)
        self.assertEqual(self.store.get(item['id'])['retry_at'],0)

    def test_permanent_errors_and_manual_projects_do_not_auto_retry(self):
        item,_=self.store.add_youtube(META,SETTINGS);self.store.set_enabled(True);self.store.claim()
        for reason in ('The source video changed','Model missing','Source check failed','Video unavailable: private'):
            self.assertFalse(self.store.retry_upload(item['id'],reason))
        folder=self.root/'data/manual';folder.mkdir();source=folder/'source.mp4';source.write_bytes(b'fixture')
        manual,_=self.store.add(dict(folder=str(folder),source=str(source),title='Manual',duration=300),SETTINGS)
        self.store.finish(item['id']);self.store.claim()
        self.assertFalse(self.store.retry_upload(manual['id'],'HTTP Error 403'))

    def test_403_refreshes_formats_and_uses_bounded_hls_fallback_without_cookies(self):
        folder=self.root/'data'/('youtube-'+META['id'])
        attempts=[]
        def extract(url,download):
            attempts.append(url)
            if len(attempts)==1:raise DownloadError('HTTP Error 403: Forbidden')
            (folder/'source.mp4').write_bytes(b'fixture')
        with patch('youtube_import.YoutubeDL') as downloader,patch('youtube_import.duration',return_value=300):
            downloader.return_value.__enter__.return_value.extract_info.side_effect=extract
            source,path=download(META,root=self.root)
            self.assertEqual(downloader.call_count,2)
            fallback=downloader.call_args_list[-1].args[0]
            self.assertEqual(fallback['format'],HLS_FORMAT)
            self.assertEqual(fallback['max_filesize'],4*1024**3)
            self.assertNotIn('cookiefile',fallback)
        self.assertEqual(source,folder/'source.mp4');self.assertEqual(path,folder)
        self.assertEqual(json.loads((folder/'import.json').read_text())['id'],META['id'])

    def test_other_download_errors_or_failed_fallback_keep_failure_and_no_manifest(self):
        for message,expected_calls in [('HTTP Error 429',1),('HTTP Error 403',2)]:
            with patch('youtube_import.YoutubeDL') as downloader:
                downloader.return_value.__enter__.return_value.extract_info.side_effect=DownloadError(message)
                with self.assertRaises(DownloadError):download(META,root=self.root)
                self.assertEqual(downloader.call_count,expected_calls)
            self.assertFalse((self.root/'data'/('youtube-'+META['id'])/'import.json').exists())

    def test_completed_import_is_reused_without_network_or_rewriting_source(self):
        folder=self.root/'data'/('youtube-'+META['id']);folder.mkdir()
        source=folder/'source.mp4';source.write_bytes(b'original')
        (folder/'import.json').write_text(json.dumps(dict(META,filename=source.name)))
        with patch('youtube_import.YoutubeDL') as downloader,patch('youtube_import.duration',return_value=300):
            self.assertEqual(download(META,root=self.root),(source,folder));downloader.assert_not_called()
        self.assertEqual(source.read_bytes(),b'original')


if __name__=='__main__':unittest.main()
