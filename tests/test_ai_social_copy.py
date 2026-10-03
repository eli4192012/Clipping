import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from social_copy import normalize,inline_title,inline_caption,generate_local,get_copy,identity

TEXT='The best cut is no cut. You keep your speed and momentum.'

def raw_copy():
    return dict(title='Keep your speed and momentum',hashtags=['#Momentum','#Speed'],
        description='The speaker explains how avoiding cuts helps preserve speed and momentum.',
        evidence_quotes=['You keep your speed and momentum.'])

def checked_copy():
    return dict(normalize(raw_copy(),TEXT),source_check=dict(faithful=True,reason='Describes the final speech.'))


class AISocialCopyTests(unittest.TestCase):
    def test_hashtags_are_part_of_title_and_description_is_a_summary(self):
        result=normalize(raw_copy(),TEXT)
        self.assertEqual(result['title'],'Keep your speed and momentum #Momentum #Speed')
        self.assertNotIn('hashtags',result)
        self.assertNotIn('#',result['description'])
        self.assertLessEqual(len(result['title']),100)

    def test_unsupported_tags_are_omitted_and_existing_tags_are_not_duplicated(self):
        raw=dict(raw_copy(),title='Keep momentum #Momentum',hashtags=['#Momentum','#NFL','#London','#Speed'])
        result=normalize(raw,TEXT)
        self.assertEqual(result['title'],'Keep momentum #Momentum #Speed')
        self.assertNotIn('#NFL',result['title'])

    def test_title_limit_keeps_whole_tags_and_does_not_truncate_qualifications(self):
        title='Jonathan Taylor might not play, but that is not confirmed'
        combined=inline_title(title,['#JonathanTaylor','#Availability','#UnconfirmedPlayerStatus'])
        self.assertLessEqual(len(combined),100);self.assertTrue(combined.startswith(title))
        self.assertNotIn('#UnconfirmedPlayerStatus',combined)
        raw=dict(raw_copy(),title='T'*100)
        with self.assertRaises(ValueError):normalize(raw,TEXT)

    def test_bad_fields_and_ungrounded_evidence_are_rejected(self):
        for fields in (dict(title=''),dict(title='#Momentum'),dict(title='T'*101),dict(description='Summary #Momentum'),
                       dict(evidence_quotes=['Invented source words']),dict(hashtags=['#FakeEvent']),dict(description='')):
            with self.subTest(fields=fields),self.assertRaises(ValueError):normalize(dict(raw_copy(),**fields),TEXT)

    def test_independent_fidelity_check_can_veto_generated_text(self):
        with patch('shorts_editor.generate_json',side_effect=[raw_copy(),dict(faithful=False,reason='Invented a guaranteed result.')]*2):
            with self.assertRaisesRegex(ValueError,'source check'):generate_local(TEXT,None)

    def test_prompts_use_only_final_clip_and_preserve_uncertainty_instruction(self):
        with patch('shorts_editor.generate_json',side_effect=[raw_copy(),dict(faithful=True)]) as generate:
            result=generate_local(TEXT,None)
        self.assertEqual(generate.call_count,2)
        self.assertIn('Preserve negation and uncertainty',generate.call_args_list[0].args[0])
        self.assertIn(TEXT,generate.call_args_list[0].args[0])
        self.assertIn('no other source context',generate.call_args_list[1].args[0])
        self.assertTrue(result['source_check']['faithful'])

    def test_cache_reuses_model_and_final_clip_and_never_retranscribes(self):
        with tempfile.TemporaryDirectory() as tmp:
            package=dict(fingerprint='one',final_transcript=TEXT,source_title='Colts in London',removed_text='Unheard question')
            settings=dict(editor_model='qwen3-4b')
            with patch('upgrades.worker',return_value=checked_copy()) as worker:
                first=get_copy(tmp,package,settings)
                self.assertEqual(worker.call_args.args[0],'social_copy')
                self.assertEqual(worker.call_args.args[1],dict(text=TEXT,editor_model='qwen3-4b'))
            with patch('upgrades.worker',side_effect=AssertionError('Repeated inference')):
                self.assertEqual(first,get_copy(tmp,package,settings))
            with patch('upgrades.worker',return_value=checked_copy()) as worker:
                get_copy(tmp,package,dict(editor_model='qwen3.5-4b'))
                get_copy(tmp,dict(package,fingerprint='changed'),settings)
                get_copy(tmp,package,settings,force=True)
                self.assertEqual(worker.call_count,3)

    def test_failed_regeneration_preserves_previously_saved_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            package=dict(fingerprint='one',final_transcript=TEXT)
            with patch('upgrades.worker',return_value=checked_copy()):first=get_copy(tmp,package,{})
            with patch('upgrades.worker',side_effect=RuntimeError('Inference failed')):
                with self.assertRaises(RuntimeError):get_copy(tmp,package,{},force=True)
            with patch('upgrades.worker',side_effect=AssertionError('Repeated inference')):
                self.assertEqual(first,get_copy(tmp,package,{}))

    def test_silent_clip_is_rejected_without_calling_inference(self):
        with patch('shorts_editor.generate_json',side_effect=AssertionError('Inferred silent clip')):
            with self.assertRaises(ValueError):generate_local('',None)

    def test_added_uncertainty_is_rejected_and_one_repair_can_succeed(self):
        bad=dict(raw_copy(),title='Maybe speed is preserved')
        with self.assertRaisesRegex(ValueError,'added uncertainty'):normalize(bad,TEXT)
        with patch('shorts_editor.generate_json',side_effect=[bad,raw_copy(),dict(faithful=True)]) as generate:
            self.assertTrue(generate_local(TEXT,None)['source_check']['faithful'])
        self.assertEqual(generate.call_count,3)
        self.assertIn('previous response was rejected',generate.call_args_list[1].args[0])

    def test_legacy_tags_move_inline_without_mutating_saved_inputs(self):
        tags=['#London','#London'];original=copy.deepcopy(tags)
        self.assertEqual(inline_caption('A conversation.\n\nIts main point.',tags),'A conversation. #London\n\nIts main point.')
        self.assertEqual(inline_title('A conversation',tags),'A conversation #London')
        self.assertEqual(tags,original)


if __name__=='__main__':unittest.main()
