import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from analysis_recovery import recover_checked_edits, resume_saved_analysis
from clip_queue import QueueStore
from jobs import analysis_path
from local_editor import IDENTITIES, cache_folder
from project_store import read, write, runs_for
from shorts_editor import edit_candidate
from upgrades import transcript_file
from test_shorts_editor import fixture


class AnalysisRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.folder=self.root/'data'/'saved';self.folder.mkdir(parents=True)
        source=self.folder/'source.mp4';source.write_bytes(b'original video')
        self.project=dict(folder=str(self.folder),source=str(source),title='Saved video',duration=40)
        self.settings=dict(mode='Podcast',minimum=5,maximum=30,windows=6,vision=False,semantic=True,
            quality='Higher quality',shorts_editor=True,portrait=True,coverage=1.,editor_model='qwen3-4b')
        self.c,self.s,self.w,self.raw,self.verdict=fixture()
        write(transcript_file(self.folder,self.settings),dict(sentences=self.s,words=self.w,language='en'))
        self.cache=cache_folder(self.folder/'topic-reviews-v37',self.settings['editor_model'])
        inputs=[self.s,5,30,'Podcast','Higher quality',[],'shorts-proposals-1','proposals-v58']
        key=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
        self.proposals=self.cache/('proposals-'+key+'.json')
        write(self.proposals,[self.c,dict(self.c,start=1.)])
        with patch('shorts_editor.generate_json',side_effect=[self.raw,self.verdict]):
            edit_candidate(self.c,self.s,self.w,30,'Higher quality',self.cache/'shorts',lambda:None,
                editor_identity=IDENTITIES['qwen3-4b'],minimum=5,mode='Podcast')
        self.originals={p:p.read_bytes() for p in self.folder.rglob('*') if p.is_file()}

    def tearDown(self):self.tmp.cleanup()

    def test_recovery_opens_only_checked_edits_without_inference_or_overwriting_final(self):
        final=analysis_path(self.project,self.settings);write(final,[dict(start=0,end=1,text='Old final result')])
        original_final=final.read_bytes()
        with patch('shorts_editor.generate_json',side_effect=AssertionError('Recovery must not infer')):
            recovery=recover_checked_edits(self.project,self.settings)
        self.assertEqual(recovery['recovered_edits'],1);self.assertEqual(recovery['source_candidates'],2)
        self.assertTrue(recovery['partial_analysis']);self.assertEqual(recovery['kept'],1)
        self.assertNotEqual(recovery['result'],str(final));self.assertEqual(final.read_bytes(),original_final)
        self.assertTrue(read(recovery['result'],[])[0]['passed'])
        self.assertTrue(any(r['result']==recovery['result'] and r['settings']==self.settings for r in runs_for(self.project)))
        for path,data in self.originals.items():self.assertEqual(path.read_bytes(),data)

    def test_other_quality_model_or_duration_never_relabels_old_work(self):
        for changed in (dict(quality='Balanced'),dict(editor_model='qwen3.5-4b'),dict(maximum=40)):
            self.assertIsNone(recover_checked_edits(self.project,dict(self.settings,**changed)))

    def test_unapproved_or_corrupt_cached_edit_is_not_recovered(self):
        saved=next(p for p in (self.cache/'shorts').glob('*.json') if '.attempt.' not in p.name)
        data=read(saved,{});data['passed']=False;write(saved,data)
        self.assertIsNone(recover_checked_edits(self.project,self.settings))
        saved.write_text('{broken json')
        self.assertIsNone(recover_checked_edits(self.project,self.settings))

    def test_resume_keeps_settings_reuses_queue_receipt_and_does_not_interrupt_current_job(self):
        store=QueueStore(self.root)
        current,_=store.add(self.project,dict(self.settings,quality='Balanced'))
        store.set_enabled(True);store.claim()
        with patch('clip_queue.ensure_runner'):
            resumed=resume_saved_analysis(self.root,self.project,self.settings)
            again=resume_saved_analysis(self.root,self.project,self.settings)
        self.assertEqual(resumed['id'],again['id']);self.assertEqual(resumed['settings'],self.settings)
        self.assertTrue(resumed['export_clips']);self.assertEqual(store.get(current['id'])['state'],'running')
        for path,data in self.originals.items():self.assertEqual(path.read_bytes(),data)

    def test_resume_respects_an_explicit_queue_pause(self):
        store=QueueStore(self.root);store.set_enabled(False)
        with patch('clip_queue.ensure_runner'):
            resumed=resume_saved_analysis(self.root,self.project,self.settings)
        self.assertEqual(resumed['state'],'queued');self.assertFalse(store.enabled());self.assertTrue(store.paused())

    def test_recovery_ui_opens_partial_results_and_shows_existing_recovery(self):
        app=AppTest.from_string(f"import streamlit as st\nfrom pathlib import Path\nfrom analysis_recovery_ui import show\ndef go(page):\n st.session_state.page=page\nshow(Path({str(self.root)!r}),{self.project!r},{self.settings!r},go)",default_timeout=15)
        with patch('clip_queue.ensure_runner'):
            app.run();self.assertFalse(app.exception)
            next(b for b in app.button if b.key=='open-recovered-clips').click().run()
            self.assertEqual(app.session_state['page'],'results')
            self.assertTrue(read(Path(app.session_state['result_path']).with_suffix('.diagnostics.json'),{})['partial_analysis'])
            next(b for b in app.button if b.key=='resume-saved-analysis').click().run()
            self.assertEqual(app.session_state['page'],'queue')
            app.run();self.assertFalse(app.exception)
            self.assertFalse(any(b.key=='resume-saved-analysis' for b in app.button))
            self.assertTrue(any('already in the video queue' in info.value for info in app.info))

    def test_partial_notice_does_not_claim_analysis_is_finished(self):
        recovery=recover_checked_edits(self.project,self.settings)
        app=AppTest.from_string(f"from pathlib import Path\nfrom analysis_recovery_ui import partial_notice\npartial_notice(Path({recovery['result']!r}),lambda page:None)")
        app.run();self.assertFalse(app.exception)
        self.assertTrue(any('unfinished' in warning.value for warning in app.warning))

    def test_processing_failure_rerun_does_not_start_another_analysis(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15)
        app.session_state['page']='processing';app.session_state['project']=self.project
        app.session_state['settings']=self.settings
        with (patch('clip_queue.resume_enabled_queue'),patch('channel_watch.ensure_watcher'),
              patch('clip_queue.QueueStore') as store,patch('analysis_recovery_ui.show'),
              patch('ui_jobs.run_job',side_effect=TimeoutError('Local analysis reached its time limit.')) as run):
            store.return_value.items.return_value=[]
            app.run();self.assertFalse(app.exception)
            app.run();self.assertFalse(app.exception)
            self.assertEqual(run.call_count,1)
            self.assertTrue(any('time limit' in error.value for error in app.error))

    def test_processing_page_does_not_duplicate_an_already_queued_recovery(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=15)
        app.session_state['page']='processing';app.session_state['project']=self.project
        app.session_state['settings']=self.settings
        with (patch('clip_queue.resume_enabled_queue'),patch('channel_watch.ensure_watcher'),
              patch('clip_queue.QueueStore') as store,patch('analysis_recovery_ui.show') as recovery,
              patch('ui_jobs.run_job',side_effect=AssertionError('Duplicated active recovery'))):
            store.return_value.items.return_value=[dict(state='queued',project=self.project,settings=self.settings)]
            app.run();self.assertFalse(app.exception);recovery.assert_called_once()


if __name__=='__main__':unittest.main()
