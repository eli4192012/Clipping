import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from social_copy import VERSION,normalize,title_options,inline_title,inline_caption,generate_local,get_copy,identity,refresh_fields,copied_description,closing_qualification

TEXT='The best cut is no cut. You keep your speed and momentum.'

def raw_copy():
    return dict(title='Keep your speed and momentum',hashtags=['#Momentum','#Speed'],
        title_options=['Keep your speed and momentum','Why the Best Cut Is No Cut','No Cut, More Momentum'],
        description='The speaker explains how avoiding cuts helps preserve speed and momentum.',
        evidence_quotes=['You keep your speed and momentum.'])

def checked_verdict(best=0,indices=None,**extra):
    titles=raw_copy()['title_options']
    return dict(faithful=True,approved_titles=[titles[i] for i in (indices if indices is not None else range(3))],best_title=titles[best],**extra)


def checked_copy():
    return dict(normalize(raw_copy(),TEXT),title_options=title_options(raw_copy(),TEXT),source_check=checked_verdict(reason='Describes the final speech.'))


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
        with patch('shorts_editor.generate_json',side_effect=[raw_copy(),checked_verdict()]) as generate:
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
        bad=dict(raw_copy(),title='Maybe speed is preserved',title_options=['Maybe speed is preserved','Why the Best Cut Is No Cut'])
        with self.assertRaisesRegex(ValueError,'added uncertainty'):normalize(bad,TEXT)
        with patch('shorts_editor.generate_json',side_effect=[bad,raw_copy(),checked_verdict()]) as generate:
            self.assertTrue(generate_local(TEXT,None)['source_check']['faithful'])
        self.assertEqual(generate.call_count,3)
        self.assertIn('previous response was rejected',generate.call_args_list[1].args[0])

    def test_transcript_dump_and_stitched_quotes_are_rejected_but_fresh_teaser_is_accepted(self):
        text='An ugly win teaches you how to finish a close game. The defense did a phenomenal job after the turnovers. You cannot keep losing the turnover battle every week.'
        for desc in (text,'The speaker says: '+text,'The defense did a phenomenal job after the turnovers. You cannot keep losing the turnover battle every week.'):
            self.assertTrue(copied_description(desc,text))
            with self.assertRaisesRegex(ValueError,'copies the spoken words'):
                normalize(dict(raw_copy(),title='What an Ugly Win Teaches a Team',hashtags=['#Defense'],description=desc,evidence_quotes=['An ugly win teaches you how to finish']),text)
        fresh='Winning a messy game can build confidence. This explanation connects defensive responses with the risk of repeated giveaways.'
        self.assertFalse(copied_description(fresh,text))

    def test_checker_selects_stronger_hook_and_all_title_ideas_keep_inline_tags(self):
        with patch('shorts_editor.generate_json',side_effect=[raw_copy(),checked_verdict(best=1)]):result=generate_local(TEXT,None)
        self.assertEqual(result['title'],'Why the Best Cut Is No Cut #Momentum #Speed')
        self.assertEqual(result['title_options'][0],result['title'])
        self.assertEqual(len(result['title_options']),3)
        self.assertTrue(all('#' in t and len(t)<=100 for t in result['title_options']))

    def test_invalid_title_choice_and_generic_or_duplicate_options_are_rejected(self):
        for ideas in (['Selected moment','Why the Best Cut Is No Cut'],['No Cut, More Momentum']*2):
            with self.assertRaises(ValueError):title_options(dict(raw_copy(),title_options=ideas),TEXT)
        with patch('shorts_editor.generate_json',side_effect=[raw_copy(),dict(checked_verdict(),best_title=8)]*2):
            with self.assertRaisesRegex(ValueError,'existing title option'):generate_local(TEXT,None)

    def test_refresh_preserves_manual_fields_and_updates_legacy_defaults_or_old_ai(self):
        default=dict(title='A ton of confidence.',description='“Original transcript.”',hashtags=[])
        self.assertEqual(refresh_fields(None,default,'key'),{'title','description'})
        self.assertEqual(refresh_fields(default,default,'key'),{'title','description'})
        self.assertEqual(refresh_fields(dict(default,title='My chosen title'),default,'key'),{'description'})
        self.assertFalse(refresh_fields(dict(default,copy_origin='manual'),default,'key'))
        self.assertFalse(refresh_fields(dict(title='My title',description='My summary'),default,'key'))
        self.assertEqual(refresh_fields(dict(ai_model='qwen3-4b',ai_version='social-copy-1'),default,'key'),{'title','description'})
        self.assertFalse(refresh_fields(dict(ai_model='qwen3-4b',ai_version=VERSION,ai_key='key'),default,'key'))

    def test_new_writer_version_does_not_reuse_old_weak_copy_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            package=dict(fingerprint='one',final_transcript=TEXT)
            with patch('social_copy.VERSION','social-copy-1'):
                old_key,_=identity(package,{})
            old=Path(tmp)/'ai-social-copy-v520'/(old_key+'.json');old.parent.mkdir()
            old.write_text(json.dumps(dict(checked_copy(),version='social-copy-1')))
            original=old.read_bytes()
            with patch('upgrades.worker',return_value=checked_copy()) as worker:get_copy(tmp,package,{})
            worker.assert_called_once();self.assertEqual(old.read_bytes(),original)

    def test_hook_cannot_add_absolute_claims_or_override_reported_unsupported_claims(self):
        with self.assertRaisesRegex(ValueError,'unsupported absolute'):
            normalize(dict(raw_copy(),description='Skipping cuts is the only way to keep your speed.'),TEXT)
        rejected=checked_verdict(unsupported_claims=['unsupported promised result'])
        with patch('shorts_editor.generate_json',side_effect=[raw_copy(),rejected,raw_copy(),checked_verdict(best=1)]):
            result=generate_local(TEXT,None)
        self.assertTrue(result['title'].startswith('Why'))

    def test_unapproved_title_ideas_are_discarded_and_one_supported_title_can_be_cached(self):
        with patch('shorts_editor.generate_json',side_effect=[raw_copy(),checked_verdict(best=1,indices=[1])]):
            result=generate_local(TEXT,None)
        self.assertEqual(result['title_options'],[result['title']])
        with tempfile.TemporaryDirectory() as tmp:
            package=dict(fingerprint='filtered',final_transcript=TEXT)
            with patch('upgrades.worker',return_value=result):saved=get_copy(tmp,package,{})
            with patch('upgrades.worker',side_effect=AssertionError('Inferred again')):self.assertEqual(saved,get_copy(tmp,package,{}))

    def test_essential_closing_caution_must_pass_its_own_check(self):
        text=TEXT+" We don't want to keep losing the turnover battle."
        bad=checked_verdict(indices=[0],ending_preserved=False)
        good=checked_verdict(best=1,indices=[1],ending_preserved=True)
        first=dict(raw_copy(),closing_summary='That final caution can be ignored.')
        repair=dict(raw_copy(),description='Avoiding cuts preserves momentum.',closing_summary='The turnover problem still needs attention.')
        with patch('shorts_editor.generate_json',side_effect=[first,bad,repair,good]) as generate:
            result=generate_local(text,None)
        self.assertTrue(result['source_check']['ending_preserved'])
        self.assertIn("We don't want to keep losing the turnover battle.",generate.call_args_list[0].args[0])
        self.assertEqual(closing_qualification('If you can avoid a cut, you keep your momentum.'),'')

    def test_legacy_tags_move_inline_without_mutating_saved_inputs(self):
        tags=['#London','#London'];original=copy.deepcopy(tags)
        self.assertEqual(inline_caption('A conversation.\n\nIts main point.',tags),'A conversation. #London\n\nIts main point.')
        self.assertEqual(inline_title('A conversation',tags),'A conversation #London')
        self.assertEqual(tags,original)


if __name__=='__main__':unittest.main()
