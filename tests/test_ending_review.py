import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ending_review import context, compile_choice, checked, generate_local, get_ending, applied, with_editor, CHECKS


def speech(texts):
    words=[];sentences=[]
    for n,text in enumerate(texts):
        tokens=text.split();step=3.8/len(tokens);start=n*4.
        for i,token in enumerate(tokens):words.append(dict(start=start+i*step,end=start+(i+1)*step,text=token))
        sentences.append(dict(start=start,end=start+3.8,text=text))
    return dict(words=words,sentences=sentences)


def fixture(root,mode='Interview'):
    transcript=speech(['What does the signature get you?', 'A golden signature earns a trip on the London Eye.',
                       'Thanks for coming to the pub.', 'What about the next game?', 'We play on Sunday.'])
    data=context(root,transcript,[dict(start=0,end=19.9)],20,dict(mode=mode,editor_model='qwen3-4b'))
    endpoint=next(e['id'] for e in data['offered_endpoints'] if 'golden signature' in e['last_sentence'])
    raw=dict(endpoint_id=endpoint,main_point_quote='A golden signature earns a trip',payoff_quote='a trip on the London Eye',reason='Stops after the prize before the next topic.')
    verdict=dict(checked_endpoint_id=endpoint,**{k:True for k in CHECKS},reason='The reward and condition are complete.')
    return data,raw,verdict,transcript


class EndingReviewTests(unittest.TestCase):
    def test_prefix_trim_stops_after_payoff_without_changing_opening_words(self):
        with tempfile.TemporaryDirectory() as root:
            data,raw,v,t=fixture(root);result=checked(dict(raw,source_check=v),data)
        self.assertTrue(result['changed']);self.assertLess(result['duration'],result['previous_duration'])
        self.assertEqual(result['ranges'][0]['start'],0)
        self.assertIn('London Eye.',result['final_transcript']);self.assertNotIn('next game',result['final_transcript'])
        self.assertIn('What about the next game?',result['removed_transcript'])
        self.assertEqual(result['removed_ranges'][0]['start'],result['end'])

    def test_timestamps_booleans_invented_ids_and_unanswered_questions_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            data,raw,v,t=fixture(root)
            for value in (True,2.4,-1,100):
                with self.subTest(value=value),self.assertRaises(ValueError):compile_choice(data,value)
            question_id=next(e['id'] for e in data['endpoints'] if 'next game?' in e['last_sentence'])
            with self.assertRaisesRegex(ValueError,'unanswered'):compile_choice(data,question_id)
            with self.assertRaisesRegex(ValueError,'source'):checked(dict(raw,source_check=dict(v,checked_endpoint_id=True)),data)

    def test_keep_option_cannot_override_two_questions_per_interview(self):
        with tempfile.TemporaryDirectory() as root:
            data,raw,v,t=fixture(root)
            self.assertNotIn(0,data['allowed_ids'])
            with self.assertRaisesRegex(ValueError,'two questions'):compile_choice(data,0)

    def test_dependent_caution_cannot_be_removed_even_when_model_approves(self):
        with tempfile.TemporaryDirectory() as root:
            for caution in ("But he is not cleared yet.","He might not be cleared yet.","We don't want to keep losing the turnover battle."):
                t=speech(['Here is the latest injury update.', 'Recovery is going well for the injured player.',caution])
                data=context(root,t,[dict(start=0,end=11.9)],12,dict(mode='Podcast'))
                self.assertEqual(data['allowed_ids'],[0])
                short=next(e['id'] for e in data['endpoints'] if 'Recovery' in e['last_sentence'])
                with self.assertRaisesRegex(ValueError,'qualification'):compile_choice(data,short)

    def test_multi_range_suffix_keeps_internal_gap_and_source_order(self):
        with tempfile.TemporaryDirectory() as root:
            t=speech(['The signature prize is a special surprise.', 'This aside repeats the earlier setup.',
                      'A golden signature earns a trip on the London Eye.', 'Thanks for coming to the pub.'])
            ranges=[dict(start=0,end=3.9),dict(start=8,end=15.9)]
            data=context(root,t,ranges,16,dict(mode='Podcast'))
            endpoint=next(e['id'] for e in data['offered_endpoints'] if 'golden signature' in e['last_sentence'])
            result=compile_choice(data,endpoint)
            self.assertEqual(result['ranges'][0],ranges[0]);self.assertEqual(result['ranges'][1]['start'],8)
            self.assertNotIn('aside',result['final_transcript']);self.assertNotIn('Thanks',result['final_transcript'])
            self.assertEqual(ranges,[dict(start=0,end=3.9),dict(start=8,end=15.9)])

    def test_keep_current_is_a_valid_result_without_forcing_a_trim(self):
        with tempfile.TemporaryDirectory() as root:
            t=speech(['The golden signature is a special prize.', 'Its holder gets a ride on the London Eye.'])
            data=context(root,t,[dict(start=0,end=7.9)],8,dict(mode='Podcast'))
            raw=dict(endpoint_id=0,main_point_quote='gets a ride on the London Eye',payoff_quote='a ride on the London Eye',reason='Current ending completes the reward.')
            v=dict(checked_endpoint_id=0,**{k:True for k in CHECKS})
            result=checked(dict(raw,source_check=v),data)
            self.assertFalse(result['changed']);self.assertEqual(result['removed_transcript'],'')

    def test_fidelity_veto_stays_a_failure_after_one_bounded_retry(self):
        with tempfile.TemporaryDirectory() as root:
            data,raw,v,t=fixture(root)
            with patch('shorts_editor.generate_json',side_effect=[raw,dict(v,qualifications_preserved=False)]*2) as generate:
                with self.assertRaisesRegex(ValueError,'verified ending'):generate_local(data,None)
            self.assertEqual(generate.call_count,4)

    def test_final_quote_is_exact_and_cannot_come_from_an_earlier_sentence(self):
        with tempfile.TemporaryDirectory() as root:
            data,raw,v,t=fixture(root)
            for quote in ('The prize guarantees an elite football career','What does the signature get you?'):
                with self.assertRaisesRegex(ValueError,'last kept sentence'):checked(dict(raw,payoff_quote=quote,source_check=v),data)

    def test_cache_reuses_transcript_and_failed_fresh_review_preserves_cache(self):
        with tempfile.TemporaryDirectory() as root:
            data,raw,v,t=fixture(root);result=checked(dict(raw,source_check=v),data)
            with patch('upgrades.worker',return_value=result) as worker:first=get_ending(root,data)
            self.assertEqual(worker.call_args.args[0],'ending_review')
            with patch('upgrades.worker',side_effect=AssertionError('Repeated inference')):
                self.assertEqual(first,get_ending(root,data))
            cache=Path(root)/'ending-reviews'/(data['key']+'.json');saved=cache.read_bytes()
            with patch('upgrades.worker',side_effect=RuntimeError('Local failure')):
                with self.assertRaises(RuntimeError):get_ending(root,data,force=True)
            self.assertEqual(cache.read_bytes(),saved)
            self.assertEqual(applied(first,data)['ranges'],first['ranges'])
            self.assertIsNone(applied(first,dict(data,basis='different cut')))

    def test_choices_use_only_selected_speech_and_omit_unsafe_partial_sentences(self):
        with tempfile.TemporaryDirectory() as root:
            data,raw,v,t=fixture(root)
            with patch('shorts_editor.generate_json',side_effect=[raw,v]) as generate:generate_local(data,None)
            self.assertIn('complete thought',generate.call_args_list[1].args[0])
            self.assertIn('Style lessons guide editing, never supply facts',generate.call_args_list[0].args[0])
            cut=context(root,t,[dict(start=0,end=10.2)],20,dict(mode='Podcast'))
            self.assertNotIn(0,cut['allowed_ids'])

    def test_editor_and_opening_changes_refresh_cache_without_reverting_applied_cut(self):
        with tempfile.TemporaryDirectory() as root:
            data,raw,v,t=fixture(root)
            with patch('upgrades.worker',return_value=checked(dict(raw,source_check=v),data)):saved=get_ending(root,data)
            model=with_editor(data,'qwen3.5-4b')
            changed=context(root,t,data['ranges'],20,dict(mode='Interview',editor_model='qwen3-4b'),opening_text='A new opening')
            for other in (model,changed):
                self.assertNotEqual(other['key'],data['key']);self.assertEqual(other['basis'],data['basis'])
                self.assertEqual(applied(saved,other)['ranges'],saved['ranges'])

    def test_short_pause_inside_unfinished_question_does_not_block_a_complete_answer(self):
        with tempfile.TemporaryDirectory() as root:
            t=speech(['What preparation matters, whether it is how you practice,',
                      'how you study or how you recover?', 'I keep a steady routine before every game.',
                      'Thanks for coming to the show.'])
            data=context(root,t,[dict(start=0,end=15.9)],16,dict(mode='Interview'))
            endpoint=next(e['id'] for e in data['offered_endpoints'] if 'steady routine' in e['last_sentence'])
            self.assertNotIn('Thanks',compile_choice(data,endpoint)['final_transcript'])

    def test_finished_questions_or_changed_voices_never_merge_into_one_question(self):
        from interview_integrity import speech_question_count
        for first,second in [('What is your preparation?','how do you recover?'),
                             ('What is your preparation,','How do you recover?')]:
            groups=[dict(start=0,end=3,text=first),dict(start=3.5,end=6,text=second)]
            self.assertEqual(speech_question_count(groups),2)
        groups=[dict(start=0,end=3,text='What is your preparation,',speaker='A'),
                dict(start=3.5,end=6,text='how do you recover?',speaker='B')]
        self.assertEqual(speech_question_count(groups),2)
        with tempfile.TemporaryDirectory() as root:
            t=speech(['What is your preparation,','how do you recover?',
                      'I keep a steady routine before every game.'])
            for word in t['words']:word['speaker']='A' if word['start']<4 else 'B'
            with self.assertRaisesRegex(ValueError,'No complete, safe'):
                context(root,t,[dict(start=0,end=11.9)],12,dict(mode='Interview'))
            t=speech(['What is your preparation,','This intervening speech was removed.',
                      'how do you recover?','I keep a steady routine before every game.'])
            with self.assertRaisesRegex(ValueError,'No complete, safe'):
                context(root,t,[dict(start=0,end=3.9),dict(start=8,end=15.9)],16,dict(mode='Interview'))


if __name__=='__main__':unittest.main()
