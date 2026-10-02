import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from shorts_editor import editorial_units, compile_plan, edit_candidate
from edit_timeline import remap_words, validate_ranges, timeline_duration
from modes import select_highlights


def fixture():
    texts = ['What is the best cut?', 'The best cut is no cut.',
             'We discussed this last week.', 'You keep your speed and momentum.']
    sentences, words = [], []
    for index, text in enumerate(texts):
        start = index * 5.
        tokens = text.split()
        step = 4 / len(tokens)
        for i, token in enumerate(tokens):
            words.append(dict(start=start+i*step, end=start+(i+1)*step-.05, text=token))
        sentences.append(dict(start=start, end=start+3.95, text=text))
    candidate = dict(start=0., end=18.95, text=' '.join(texts), title='Moment', rank=1, passed=False)
    raw = dict(ranges=[dict(first=1,last=1,role='hook',reason='Strong contradiction.'),
                       dict(first=3,last=3,role='payoff',reason='Explains the benefit.')],
        removed=[dict(first=0,last=0,reason='Answer stands alone.'),dict(first=2,last=2,reason='Episode reference adds no information.')],
        standalone_context_check=dict(passed=True,reason='The subject is the best cut.'),
        meaning_preserved=True, ending_complete=True, title='The best cut is no cut',
        description='Why keeping momentum matters.', supported_variants=[])
    verdict = dict(standalone=True,faithful=True,complete_ending=True,metadata_grounded=True,reason='A complete explanation.',
        audience_review={k:dict(rating=2,evidence='best cut') for k in ('opening','clarity','value','payoff')})
    return candidate,sentences,words,raw,verdict


class ShortsEditorTests(unittest.TestCase):
    def test_internal_cut_and_answer_only_preserve_exact_source_words(self):
        c,s,w,raw,_ = fixture()
        plan = compile_plan(raw,c,editorial_units(c,s,w),w,30)
        self.assertEqual(plan['final_transcript'],'The best cut is no cut. You keep your speed and momentum.')
        self.assertEqual(len(plan['removed_ranges']),2)
        self.assertLess(plan['recommended_duration'],c['end']-c['start'])
        self.assertFalse(plan['meaning_preserved']) # A planner cannot approve its own edit.
        mapped = remap_words(w,plan['ranges'])
        self.assertLess(mapped[-1]['end'],plan['recommended_duration']+.001)
        self.assertTrue(all(a['end']<=b['start'] for a,b in zip(mapped,mapped[1:])))

    def test_reject_invented_ids_reordering_repeats_and_missing_cut_reasons(self):
        c,s,w,raw,_ = fixture();units=editorial_units(c,s,w)
        bads=[]
        for value in (99,True,-1):
            bad=copy.deepcopy(raw);bad['ranges'][0]['first']=value;bads.append(bad)
        bad=copy.deepcopy(raw);bad['ranges'].reverse();bads.append(bad)
        bad=copy.deepcopy(raw);bad['ranges'][1]['first']=1;bads.append(bad)
        bad=copy.deepcopy(raw);bad['removed']=[];bads.append(bad)
        bad=copy.deepcopy(raw);bad['standalone_context_check']['passed']=False;bads.append(bad)
        for bad in bads:
            with self.assertRaises(ValueError):compile_plan(bad,c,units,w,30)
        with self.assertRaises(ValueError):compile_plan(raw,c,units,w,3)

    def test_final_fidelity_veto_preserves_debug_attempt_and_never_caches_success(self):
        c,s,w,raw,v=fixture();v['faithful']=False
        with tempfile.TemporaryDirectory() as tmp, patch('shorts_editor.generate_json',side_effect=[raw,v]):
            with self.assertRaises(ValueError):edit_candidate(c,s,w,30,'Balanced',tmp,lambda:None)
            files=list(Path(tmp).glob('*.json'))
            self.assertEqual(len(files),1);self.assertTrue(files[0].name.endswith('.attempt.json'))
            self.assertFalse(json.loads(files[0].read_text())['validation']['faithful'])

    def test_cache_hit_skips_model_and_quality_and_word_changes_do_not_reuse_it(self):
        c,s,w,raw,v=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            with patch('shorts_editor.generate_json',side_effect=[raw,v]):
                first=edit_candidate(c,s,w,30,'Balanced',tmp,lambda:None)
            with patch('shorts_editor.generate_json',side_effect=AssertionError('Repeated inference')):
                second=edit_candidate(c,s,w,30,'Balanced',tmp,Mock(side_effect=AssertionError('Loaded model')))
            self.assertEqual(first,second)
            for quality,words in [('Higher quality',w),('Balanced',[dict(x,text='changed') if i==0 else x for i,x in enumerate(w)])]:
                with patch('shorts_editor.generate_json',side_effect=[raw,v]) as generate:
                    edit_candidate(c,s,words,30,quality,tmp,lambda:None)
                    self.assertEqual(generate.call_count,2)

    def test_small_source_does_not_offer_artificial_variants(self):
        c,s,w,raw,v=fixture();raw['supported_variants']=[dict(name='Fast',reason='Try shorter.')]
        with patch('shorts_editor.generate_json',side_effect=[raw,v]):
            result=edit_candidate(c,s,w,30,'Balanced',None,lambda:None)
        self.assertEqual(result['edit_plan']['supported_variants'],[])

    def test_identical_fast_edit_is_rejected_before_second_review(self):
        c,s,w,raw,v=fixture()
        baseline=compile_plan(raw,c,editorial_units(c,s,w),w,30)
        with patch('shorts_editor.generate_json',return_value=raw) as generate:
            with self.assertRaises(ValueError):edit_candidate(c,s,w,30,'Balanced',None,lambda:None,'Fast',baseline)
            generate.assert_called_once()

    def test_coverage_and_overlap_count_only_kept_source_ranges(self):
        a=dict(start=0,end=20,text='alpha beta',passed=True,rank=2,
            edit_plan=dict(ranges=[dict(start=0,end=3),dict(start=17,end=20)]))
        b=dict(start=5,end=10,text='gamma delta',passed=True,rank=1)
        self.assertEqual(select_highlights([a,b],30,'Podcast',None,coverage=.4),[a,b])
        c=dict(start=18,end=22,text='epsilon zeta',passed=True,rank=0)
        self.assertEqual(select_highlights([a,c],30,'Podcast',None,coverage=1),[a])

    def test_invalid_timeline_never_reaches_encoder(self):
        for r in ([dict(start=0,end=float('nan'))],[dict(start=5,end=6),dict(start=2,end=3)],[],[dict(start=0,end=50)]):
            with self.assertRaises(ValueError):validate_ranges(r,20)

    def test_unanswered_question_and_conflicting_removals_cannot_be_ai_approved(self):
        c,s,w,raw,v=fixture();units=editorial_units(c,s,w)
        conflict=copy.deepcopy(raw);conflict['removed'].append(dict(first=1,last=1,reason='Contradicts its kept range.'))
        with self.assertRaises(ValueError):compile_plan(conflict,c,units,w,30)
        question=copy.deepcopy(raw);question['ranges']=[dict(first=0,last=0,role='hook_payoff',reason='Wrong final question.')];question['removed']=[dict(first=1,last=3,reason='Removed answer.')]
        with self.assertRaises(ValueError):compile_plan(question,c,units,w,30)

    def test_explicit_ids_compile_to_chronological_phrase_ranges(self):
        c,s,w,raw,v=fixture();units=editorial_units(c,s,w)
        raw.pop('ranges');raw.update(keep_ids=[1,3],hook_ids=[1],payoff_ids=[3],removed=[dict(ids=[0],reason='Question omitted.'),dict(ids=[2],reason='Repeated context.')])
        plan=compile_plan(raw,c,units,w,30)
        self.assertEqual([r['first_unit'] for r in plan['ranges']],[1,3])
        self.assertNotIn('last week',plan['final_transcript'])
        raw['keep_ids']=[3,1]
        with self.assertRaises(ValueError):compile_plan(raw,c,units,w,30)

    def test_start_end_and_internal_cuts_have_one_unambiguous_meaning(self):
        c,s,w,raw,v=fixture();units=editorial_units(c,s,w)
        raw.pop('ranges');raw.pop('removed')
        raw.update(start_id=1,end_id=3,internal_cuts=[dict(ids=[2],reason='Unnecessary previous episode reference.')])
        plan=compile_plan(raw,c,units,w,30)
        self.assertEqual([r['first_unit'] for r in plan['ranges']],[1,3])
        self.assertEqual([r['first_unit'] for r in plan['removed_ranges']],[0,2])
        raw['internal_cuts'][0]['ids']=[3]
        shorter=compile_plan(raw,c,units,w,30)
        self.assertNotIn('momentum',shorter['final_transcript'])
        raw['internal_cuts'][0]['ids']=[9]
        with self.assertRaises(ValueError):compile_plan(raw,c,units,w,30)

    def test_copied_rating_template_is_not_a_verified_edit(self):
        c,s,w,raw,v=fixture()
        v['audience_review']={k:dict(rating=2,evidence='exact quote from FINAL') for k in ('opening','clarity','value','payoff')}
        with patch('shorts_editor.generate_json',side_effect=[raw,v]):
            with self.assertRaises(ValueError):edit_candidate(c,s,w,30,'Balanced',None,lambda:None)

    def test_unsupported_rating_is_omitted_without_overriding_grounded_checks(self):
        c,s,w,raw,v=fixture();v['audience_review']['opening']['evidence']='Invented opening quote'
        with patch('shorts_editor.generate_json',side_effect=[raw,v]):
            result=edit_candidate(c,s,w,30,'Balanced',None,lambda:None)
        self.assertTrue(result['passed'])
        self.assertNotIn('opening',result['audience_quality']['criteria'])
        self.assertIn('Other ratings were omitted',result['audience_quality']['reason'])

    def test_editorial_stage_reuses_transcript_and_skips_legacy_interview_veto(self):
        from jobs import analyze
        c,s,w,raw,v=fixture();plan=compile_plan(raw,c,editorial_units(c,s,w),w,30)
        edited=dict(c,start=plan['ranges'][0]['start'],end=plan['ranges'][-1]['end'],text=plan['final_transcript'],passed=True,topic_group=True,edit_plan=plan)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';source.write_bytes(b'fixture')
            project=dict(folder=tmp,source=str(source),duration=30)
            settings=dict(mode='Interview',minimum=5,maximum=30,vision=False,semantic=True,windows=6,quality='Balanced',shorts_editor=True,coverage=1)
            with patch('jobs.get_transcript',return_value=dict(words=w,sentences=s)),patch('jobs.worker',return_value=[edited]) as worker:
                path=analyze(project,settings,lambda *args:None)
                self.assertEqual(len(json.loads(Path(path).read_text())),1)
                self.assertEqual(worker.call_args.args[1]['words'],w)
                self.assertTrue(worker.call_args.args[1]['shorts_editor'])

if __name__=='__main__':unittest.main()
