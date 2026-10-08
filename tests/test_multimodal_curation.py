import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audience_quality import annotate,selection_key
from edit_timeline import ranges_for
from modes import select_highlights
from multimodal_curation import VERSION,curate,fingerprint,frame_times,fuse,genre,valid_priority
from sound_analysis import summarize


def clip(start=0,end=9,text='This is one useful complete point.',passed=True):
    return dict(start=start,end=end,text=text,rank=0,passed=passed,title='Moment')


def audio():
    return dict(status='Measured',frames=[dict(start=i,end=i+.96,tags=[dict(label='Speech',score=.8),dict(label='Applause',score=.4)]) for i in range(20)],
                levels=[dict(start=i,end=i+1,rms_db=-20) for i in range(20)])


class CurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.source=self.root/'source.mp4';self.source.write_bytes(b'original')
        self.project=dict(source=str(self.source),folder=str(self.root),duration=20,title='Fixture')
        model=self.root/'model';model.mkdir();(model/'.ready').touch();(model/'config.json').write_text('{}')
        self.model_patch=patch('multimodal_curation.vision_model',return_value=model);self.model_patch.start()
        self.settings=dict(mode='Podcast',curation_windows=2,categories=['Podcast'])
        self.transcript=dict(words=[],sentences=[]);self.candidates=annotate([clip(),clip(10,19,'A different worthwhile explanation.')],'Podcast')
    def tearDown(self):self.model_patch.stop();self.tmp.cleanup()

    def sample(self,source,ranges,folder):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);path=folder/'sample.jpg';path.write_bytes(b'fixture')
        return [dict(time=ranges[0]['start']+.5,path=str(path))]

    def vision(self,task,payload,**kwargs):
        self.assertEqual(task,'curation_visual')
        return [dict(f,status='Observed',shot='talking_heads',action_visible=False,reaction_visible=False,description='Two people are visible.') for f in payload['frames']]

    def review(self,worker=None,sound=None):
        with patch('sound_analysis.scan',side_effect=sound) if sound else patch('sound_analysis.scan',return_value=audio()), \
             patch('multimodal_curation.visual_scan',return_value=[dict(time=1,motion=.1,cut=False)]), \
             patch('multimodal_curation.sample_frames',side_effect=self.sample), \
             patch('upgrades.worker',side_effect=worker or self.vision):
            return curate(self.project,self.transcript,self.candidates,self.settings)

    def test_curation_preserves_source_transcript_boundaries_and_pass_state(self):
        before=copy.deepcopy(self.candidates);transcript=copy.deepcopy(self.transcript)
        reviewed,report=self.review()
        self.assertEqual(self.source.read_bytes(),b'original');self.assertEqual(self.candidates,before);self.assertEqual(self.transcript,transcript)
        self.assertTrue(report['complete']);self.assertEqual(report['emotion'],'Not used')
        for a,b in zip(before,reviewed):
            self.assertEqual(ranges_for(a),ranges_for(b));self.assertEqual(a['passed'],b['passed']);self.assertTrue(valid_priority(b))

    def test_cache_reuses_models_and_scans_including_already_annotated_input(self):
        first,report=self.review()
        with patch('sound_analysis.scan',side_effect=AssertionError('Sound repeated')),patch('upgrades.worker',side_effect=AssertionError('Vision repeated')),patch('multimodal_curation.visual_scan',side_effect=AssertionError('Scan repeated')):
            self.assertEqual(curate(self.project,self.transcript,first,self.settings),(first,report))

    def test_failed_model_evidence_stays_unknown_and_never_approves_draft(self):
        self.candidates[0]['passed']=False
        def failed(*args,**kwargs):raise RuntimeError('Unavailable model')
        reviewed,report=self.review(worker=failed,sound=failed)
        self.assertTrue(report['failures']);self.assertFalse(report['complete']);self.assertFalse(reviewed[0]['passed'])
        self.assertIsNone(reviewed[0]['multimodal_curation']['signals']['visuals']);self.assertIsNone(reviewed[0]['multimodal_curation']['signals']['sound'])

    def test_explicit_review_rebuilds_missing_sample_instead_of_reusing_complete_report(self):
        first,_=self.review()
        Path(first[0]['multimodal_curation']['visual']['samples'][0]['path']).unlink()
        with patch('upgrades.worker',side_effect=self.vision) as worker:
            again,report=self.review(worker=worker)
        self.assertEqual(worker.call_count,1);self.assertTrue(report['complete'])
        self.assertTrue(Path(again[0]['multimodal_curation']['visual']['samples'][0]['path']).is_file())

    def test_changed_source_during_review_never_saves_combined_report(self):
        def changed(*args,**kwargs):self.source.write_bytes(b'changed');return self.vision(*args,**kwargs)
        with self.assertRaisesRegex(ValueError,'source changed'):self.review(worker=changed)
        self.assertFalse(list((self.root/'multimodal-curation').glob('review-*.json')))

    def test_two_real_interview_questions_are_vetoed_before_visual_review(self):
        self.settings['mode']='Interview';self.settings['categories']=['Interview']
        self.transcript['words']=[dict(start=0,end=1,text='Why?'),dict(start=2,end=3,text='How?'),dict(start=4,end=5,text='Answer.')]
        self.candidates=[annotate([clip(text='Why? How? Answer.')],'Interview')[0]]
        reviewed,_=self.review();self.assertTrue(reviewed[0]['boundary_rejected']);self.assertFalse(reviewed[0]['passed'])
        self.assertEqual(select_highlights(reviewed,20,'Interview',None,coverage=1.),[])

    def test_frame_sampling_and_sound_windows_never_bridge_removed_ranges(self):
        ranges=[dict(start=0,end=2),dict(start=10,end=12)]
        self.assertEqual(frame_times(ranges),[.4,10.,11.6])
        summary=summarize(audio(),ranges)
        self.assertTrue(all(any(r['start']<=e['start'] and e['end']<=r['end'] for r in ranges) for e in summary['events']))
        only_straddling=dict(frames=[dict(start=1.8,end=2.76,tags=[dict(label='Applause',score=.9)])],levels=[])
        self.assertFalse(summarize(only_straddling,ranges)['available'])

    def test_unknown_grounded_speech_rating_is_not_invented(self):
        report=fuse(self.candidates[0],'Podcast',summarize(audio(),ranges_for(self.candidates[0])),[],[],self.settings)
        self.assertIsNone(report['signals']['speech']);self.assertEqual(report['available_weight'],.15)

    def test_genre_rules_preserve_interview_priority_over_sports_subject(self):
        self.assertEqual(genre(dict(mode='Interview',categories=['American football','Interview'])),'Interview')
        self.assertEqual(genre(dict(mode='Podcast',categories=['Music'])),'Music')

    def test_supporting_priority_changes_choice_but_cannot_override_integrity(self):
        a,b=annotate([clip(),clip(0,10,'Another complete interesting point.')],'Podcast')
        for c,score in ((a,2.1),(b,2.5)):
            c['multimodal_curation']=dict(version=VERSION,fingerprint=fingerprint(c),ranking_score=score)
        self.assertEqual(select_highlights([a,b],20,'Podcast',None,coverage=1.),[b])
        b['boundary_rejected']=True
        self.assertEqual(select_highlights([a,b],20,'Podcast',None,coverage=1.),[a])
        b.pop('boundary_rejected');b['passed']=False
        self.assertEqual(select_highlights([a,b],20,'Podcast',None,coverage=1.,strict=True),[a])

    def test_changed_cut_cannot_reuse_prior_ranking(self):
        reviewed,_=self.review();c=reviewed[0];c['end']-=1
        self.assertFalse(valid_priority(c));self.assertEqual(selection_key(c)[2],c['audience_quality']['score'])


class PipelineTests(unittest.TestCase):
    def test_enabled_curation_runs_before_selection_and_reuses_discovery(self):
        from jobs import analyze,analysis_path,estimate_seconds
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);source=folder/'source';source.write_bytes(b'fixture')
            project=dict(folder=temp,source=str(source),duration=20,title='Fixture')
            settings=dict(mode='Podcast',minimum=5,maximum=15,quality='Balanced',vision=False,semantic=True,windows=6,coverage=1.)
            clips=[dict(clip(),topic_group=True),dict(clip(0,10,'Another complete point.'),topic_group=True)]
            def combined(p,t,c,s,update):
                out=copy.deepcopy(c)
                for item,score in zip(out,(2.1,2.5)):item['multimodal_curation']=dict(version=VERSION,fingerprint=fingerprint(item),ranking_score=score)
                update(1,'Done')
                return out,dict(total_moments=2,visual_moments=2,seconds=1,failures=[])
            events=[]
            with patch('jobs.get_transcript',return_value=dict(words=[],sentences=[])),patch('jobs.worker',return_value=clips) as worker,patch('multimodal_curation.curate',side_effect=combined) as review:
                old=analyze(project,settings,lambda *a:None)
                new_settings=dict(settings,multimodal_curation=True,curation_windows=2)
                new=analyze(project,new_settings,lambda p,label:events.append(p))
                worker.assert_called_once();review.assert_called_once()
                self.assertNotEqual(old,new);self.assertEqual(json.loads(Path(new).read_text())[0]['end'],10)
                self.assertEqual(events,sorted(events))
                with patch('jobs.get_transcript',side_effect=AssertionError('Repeated transcription')):
                    self.assertEqual(analyze(project,new_settings,lambda *a:None),new)
                self.assertEqual(review.call_count,1)
            self.assertNotEqual(analysis_path(project,new_settings),analysis_path(project,dict(new_settings,curation_windows=3)))
