import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from jobs import analysis_path, analyze
from local_editor import QWEN35, QWEN3, SMALL, IDENTITIES, selected_editor, preferred_editor, installed
from shorts_editor import edit_candidate
from topic_cache import reviewed_topics
from upgrades import transcript_file
from test_shorts_editor import fixture


class LocalEditorTests(unittest.TestCase):
    def test_model_change_separates_analysis_and_preserves_transcription_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';source.write_bytes(b'fixture')
            p=dict(folder=tmp,source=str(source))
            s=dict(mode='Interview',minimum=5,maximum=30,vision=False,semantic=True,windows=6,quality='Higher quality')
            a=dict(s,editor_model=QWEN35);b=dict(s,editor_model=QWEN3)
            self.assertNotEqual(analysis_path(p,a),analysis_path(p,b))
            self.assertEqual(transcript_file(tmp,a),transcript_file(tmp,b))
            self.assertEqual(transcript_file(tmp,s),transcript_file(tmp,a))
            self.assertEqual(analysis_path(p,dict(a,mode='Sports')),analysis_path(p,dict(b,mode='Sports')))

    def test_explicit_model_applies_to_both_processing_modes_and_legacy_defaults_survive(self):
        for quality in ('Balanced','Higher quality'):
            for large in (True,False):
                self.assertEqual(selected_editor(dict(quality=quality,editor_model=QWEN35),large),QWEN35)
        self.assertEqual(selected_editor({'quality':'Balanced'}),SMALL)
        self.assertEqual(selected_editor({'quality':'Balanced'},large=True),QWEN3)
        with self.assertRaises(ValueError):selected_editor({'editor_model':'https://example.com/model'})

    def test_missing_new_model_selects_previous_and_partial_download_is_not_ready(self):
        with patch('local_editor.installed',return_value=False):self.assertEqual(preferred_editor(),QWEN3)
        with tempfile.TemporaryDirectory() as tmp,patch('local_editor.ROOT',Path(tmp)):
            path=Path(tmp)/'models'/QWEN35;path.mkdir(parents=True)
            (path/'.ready').write_text('{}')
            self.assertFalse(installed(QWEN35))
            from local_editor import load_bundle
            with patch('resource_limits.configure_mlx'),patch('mlx_lm.load',side_effect=AssertionError('Tried loading missing files')):
                with self.assertRaisesRegex(RuntimeError,'missing or incomplete'):load_bundle({'editor_model':QWEN35})

    def test_edit_decisions_are_cached_per_model_and_reopen_without_inference(self):
        c,s,w,raw,v=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            for key in (QWEN35,QWEN3):
                with patch('shorts_editor.generate_json',side_effect=[raw,v]) as generate:
                    result=edit_candidate(c,s,w,30,'Balanced',tmp,lambda:None,editor_identity=IDENTITIES[key])
                self.assertEqual(generate.call_count,2)
                self.assertEqual(result['edit_plan']['editor_model'],IDENTITIES[key])
            with patch('shorts_editor.generate_json',side_effect=AssertionError('Repeated inference')):
                for key in (QWEN35,QWEN3):
                    edit_candidate(c,s,w,30,'Balanced',tmp,Mock(side_effect=AssertionError('Loaded weights')),editor_identity=IDENTITIES[key])

    def test_topic_proposals_and_checks_cannot_cross_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=dict(cache_dir=tmp,mode='Podcast',quality='Balanced',sentences=[],minimum=5,maximum=30)
            c=dict(start=0,end=6,text='A complete useful point.',rank=1,passed=True)
            with patch('topic_cache.topic_candidates',return_value=[c]) as propose,patch('topic_cache.exact_cut_review',return_value=c) as review:
                for key in (QWEN35,QWEN3):reviewed_topics(dict(p,editor_model=key),lambda:(None,None,None,None))
            self.assertEqual(propose.call_count,2);self.assertEqual(review.call_count,2)
            with patch('topic_cache.topic_candidates',side_effect=AssertionError('Repeated proposals')):
                for key in (QWEN35,QWEN3):reviewed_topics(dict(p,editor_model=key),Mock(side_effect=AssertionError('Loaded model')))

    def test_analysis_passes_model_choice_and_reuses_saved_speech(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';source.write_bytes(b'fixture')
            p=dict(folder=tmp,source=str(source),duration=30)
            s=dict(mode='Podcast',minimum=5,maximum=30,vision=False,semantic=True,windows=6,quality='Balanced',editor_model=QWEN35)
            speech=dict(language='en',words=[],sentences=[])
            path=Path(tmp)/'transcript.json';path.write_text(json.dumps(speech));before=path.stat().st_mtime_ns
            c=dict(start=0,end=6,text='A complete useful point.',rank=1,passed=True,topic_group=True,title='Useful point')
            with patch('jobs.transcribe',side_effect=AssertionError('Retranscribed')),patch('jobs.worker',return_value=[c]) as worker:
                analyze(p,s,lambda *args:None)
                self.assertEqual(worker.call_args.args[1]['editor_model'],QWEN35)
                worker.reset_mock()
                analyze(p,s,lambda *args:None);worker.assert_not_called()
                analyze(p,dict(s,editor_model=QWEN3),lambda *args:None)
                self.assertEqual(worker.call_args.args[1]['editor_model'],QWEN3)
            self.assertEqual(path.stat().st_mtime_ns,before)

    def test_bounded_generation_keeps_source_intact_and_loads_only_local_files(self):
        from local_editor import load_bundle,MAX_PROMPT_TOKENS
        tokenizer=Mock();tokenizer.encode.return_value=[1]*10
        model=object()
        with patch('resource_limits.configure_mlx'),patch('local_editor.installed',return_value=True),patch('mlx_lm.load',return_value=(model,tokenizer)) as load,patch('mlx_lm.generate',return_value='{}') as generate:
            m,t,g,s=load_bundle({'editor_model':QWEN35})
            self.assertTrue(load.call_args.kwargs['tokenizer_config']['local_files_only'])
            self.assertFalse(load.call_args.kwargs['tokenizer_config']['trust_remote_code'])
            g(m,t,prompt='Exact source',max_tokens=200,sampler=s,verbose=False)
            self.assertEqual(generate.call_args.kwargs['prompt'],'Exact source')
            self.assertEqual(generate.call_args.kwargs['prefill_step_size'],256)
            tokenizer.encode.return_value=[1]*(MAX_PROMPT_TOKENS+1)
            with self.assertRaisesRegex(ValueError,'context limit'):g(m,t,prompt='Long source',max_tokens=200)
            self.assertEqual(generate.call_count,1)

    def test_recovered_old_runs_do_not_inherit_todays_editor_selection(self):
        from project_store import runs_for
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';source.write_bytes(b'fixture')
            p=dict(folder=tmp,source=str(source))
            s=dict(mode='Interview',minimum=5,maximum=30,vision=False,semantic=True,windows=6,quality='Balanced')
            (Path(tmp)/'ui-settings.json').write_text(json.dumps(dict(s,editor_model=QWEN35)))
            clips=[dict(start=0,end=6,text='Useful point.')]
            old=analysis_path(p,s);old.write_text(json.dumps(clips))
            current=analysis_path(p,dict(s,editor_model=QWEN3));current.write_text(json.dumps(clips))
            recovered={Path(r['result']).name:r['settings'] for r in runs_for(p)}
            self.assertNotIn('editor_model',recovered[old.name])
            self.assertEqual(recovered[current.name]['editor_model'],QWEN3)


if __name__=='__main__':unittest.main()
