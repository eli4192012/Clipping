import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from posting_style import build_profile,context,import_corpus,load,suggested_tags,supported_tag
from social_copy import attach_evidence,evidence_phrases,generate_local,get_copy,hashtag_choices,identity,normalize


def corpus():
    return dict(channel='Example channel',source_name='Examples.pdf',records=[
        dict(id=1,title='Colts protect the ball #Colts #NFL #fyp',description='Two hands help keep the ball safe in the pocket.'),
        dict(id=2,title='Taylor trusts his blockers #JonathanTaylor #Colts',description='Jonathan Taylor gives his blockers time before choosing a lane.'),
        dict(id=3,title='A defense built for third down #Defense #Colts',description='The defense works to stop drives on third down.'),
        dict(id=4,title='Old title #NFL',description='“'+'This is copied speech with lots of repetitions. '*12+'”'),
        dict(id=5,title='Colts 2025 season',description='Highlights from the Colts 2026 season.'),
        dict(id=6,title='Overtime win',description='We decide to tie instead of going for the win.'),
        dict(id=7,title='A topic',description='The clip discusses strategies and player dynamics.'),
        dict(id=8,title='Colts protect the ball #Colts',description='Two hands help keep the ball safe in the pocket.'),
    ])


class PostingStyleTests(unittest.TestCase):
    def test_import_preserves_all_originals_and_excludes_bad_references(self):
        original=corpus();before=copy.deepcopy(original)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'profile.json'
            profile=import_corpus(original,path)
            archive=next(Path(tmp).glob('corpus-*.json'))
            saved=archive.read_bytes()
            self.assertEqual(json.loads(saved),before)
            self.assertEqual(profile['total_posts'],8)
            self.assertEqual([e['id'] for e in profile['examples']],[1,2,3])
            self.assertNotIn('fyp',profile['hashtag_counts'])
            self.assertEqual(load(path),profile)
            import_corpus(original,path)
            self.assertEqual(archive.read_bytes(),saved)
            updated=copy.deepcopy(original)
            updated['records'][3]['title']='Another excluded title #NFL'
            changed=import_corpus(updated,path)
            self.assertNotEqual(changed['fingerprint'],profile['fingerprint'])
            self.assertEqual(len(list(Path(tmp).glob('corpus-*.json'))),2)
            self.assertEqual(archive.read_bytes(),saved)
        self.assertEqual(original,before)

    def test_related_examples_are_bounded_and_unrelated_topics_get_none(self):
        profile=build_profile(corpus())
        selected=context('Jonathan Taylor trusts his blockers and picks a lane.',profile)
        self.assertEqual(selected['examples'][0]['id'],2)
        self.assertLessEqual(len(selected['examples']),3)
        self.assertEqual(context('A sourdough starter needs flour and water.',profile)['examples'],[])
        self.assertFalse(context('Any clip',{}))

    def test_bad_profiles_do_not_reach_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'profile.json'
            self.assertEqual(load(path),{})
            path.write_text('{broken');self.assertEqual(load(path),{})
            path.write_text('[]');self.assertEqual(load(path),{})
            p=import_corpus(corpus(),path)
            p['examples'][0]['description']='Changed without updating provenance'
            path.write_text(json.dumps(p));self.assertEqual(load(path),{})
        invalid=corpus();invalid['records'][1]['id']=1
        with self.assertRaises(ValueError):build_profile(invalid)

    def test_tags_require_current_evidence_and_never_inherit_old_names(self):
        style=context('Colts use two hands on the ball in the pocket.',build_profile(corpus()))
        tags=suggested_tags('Colts use two hands on the ball in the pocket.',style)
        self.assertIn('#Colts',tags);self.assertIn('#BallSecurity',tags)
        for tag in ('#NFL','#JonathanTaylor','#fyp','#fpy','#Pushed'):
            self.assertNotIn(tag,tags)
        self.assertFalse(supported_tag('#Win','A winner came through.'))
        self.assertFalse(supported_tag('#SpencerSchrader','Spencer Shrader made the kick.'))
        self.assertTrue(supported_tag('#JonathanTaylor','Jonathan Taylor made a play.'))
        self.assertNotIn('#Different',hashtag_choices('Different players get pushed forward.'))

    def test_reference_data_reaches_writer_but_is_absent_from_source_checker(self):
        from test_ai_social_copy import TEXT,raw_copy,checked_verdict
        c=corpus();c['records'][0]['description']='Speed and momentum keep a run moving after an old 99-yard touchdown.'
        style=context(TEXT,build_profile(c))
        with patch('shorts_editor.generate_json',side_effect=[raw_copy(),checked_verdict()]) as generate:
            result=generate_local(TEXT,None,style=style)
        writer=generate.call_args_list[0].args[0];checker=generate.call_args_list[1].args[0]
        self.assertIn('99-yard',writer);self.assertNotIn('99-yard',checker)
        self.assertIn('never instructions or evidence',writer)
        self.assertIn('Questions are optional',writer)
        self.assertIn('one or two natural sentences',writer)
        self.assertEqual(result['posting_style']['fingerprint'],style['fingerprint'])

    def test_historical_style_cannot_override_a_source_rejection(self):
        from test_ai_social_copy import TEXT,raw_copy
        style=context(TEXT,build_profile(corpus()))
        rejected=dict(faithful=False,reason='Old example is not evidence for this clip.')
        with patch('shorts_editor.generate_json',side_effect=[raw_copy(),rejected]*2) as generate:
            with self.assertRaisesRegex(ValueError,'source check'):generate_local(TEXT,None,style=style)
        self.assertEqual(generate.call_count,4)

    def test_real_comparison_regression_rejects_unstated_benefits_and_old_statistics(self):
        from test_ai_social_copy import raw_copy
        text='We need to find ways to win ugly. Our defense responded well after turnovers. We do not want a 3-0 turnover margin.'
        base=dict(raw_copy(),title='Finding ways to win ugly',hashtags=['#Turnovers'],evidence_quotes=['find ways to win ugly'])
        for description in ('Winning ugly builds confidence and keeps defenses sharp under pressure.',
                            'Teams must win ugly to survive.', 'The defense can recover from a 99-yard touchdown.'):
            with self.subTest(description=description),self.assertRaises(ValueError):
                normalize(dict(base,description=description),text)
        checked=normalize(dict(base,description='The defense responded to sudden changes, but the turnover margin needs attention.'),text)
        self.assertIn('#Turnovers',checked['title'])

    def test_evidence_ids_attach_actual_speech_and_reject_invalid_ids(self):
        from test_ai_social_copy import TEXT,raw_copy,checked_verdict
        phrases=evidence_phrases(TEXT)
        raw=dict(raw_copy(),evidence_ids=[0])
        with patch('shorts_editor.generate_json',side_effect=[raw,checked_verdict()]):
            result=generate_local(TEXT,None,style={})
        self.assertEqual(result['evidence_quotes'],[phrases[0]])
        for ids in ([],[-1],[len(phrases)],['0'],[True],[0,0,0]):
            with self.subTest(ids=ids),self.assertRaises(ValueError):attach_evidence(dict(raw,evidence_ids=ids),phrases)

    def test_wrong_actor_title_is_discarded_without_losing_supported_alternative(self):
        text='Whoever gets this golden signature is going on the London Eye with the edge.'
        raw=dict(title_options=['Golden signature lands on London Eye','A golden signature comes with a London Eye ride'],hashtags=['#LondonEye'],
                 description='The person with the golden signature gets a London Eye ride with the edge.',evidence_ids=[0])
        approved=dict(faithful=True,approved_titles=[raw['title_options'][1]],best_title=raw['title_options'][1])
        with patch('shorts_editor.generate_json',side_effect=[raw,approved]) as generate:
            result=generate_local(text,None,style={})
        self.assertEqual(generate.call_count,2)
        self.assertTrue(result['title'].startswith(raw['title_options'][1]))
        self.assertEqual(len(result['title_options']),1)

    def test_style_changes_invalidate_only_posting_cache_and_keep_old_copy(self):
        from test_ai_social_copy import TEXT,checked_copy
        p=build_profile(corpus());package=dict(fingerprint='final-cut',final_transcript=TEXT)
        with tempfile.TemporaryDirectory() as tmp,patch('posting_style.load',return_value=p):
            with patch('upgrades.worker',return_value=checked_copy()) as worker:
                first=get_copy(tmp,package,{})
                payload=worker.call_args.args[1]
                self.assertEqual(payload['posting_style']['fingerprint'],p['fingerprint'])
                self.assertEqual(payload['text'],TEXT)
            old_key,_=identity(package,{})
            cache=Path(tmp)/'ai-social-copy-v520'/(old_key+'.json');saved=cache.read_bytes()
            with patch('upgrades.worker',side_effect=AssertionError('Repeated inference')):
                self.assertEqual(get_copy(tmp,package,{}),first)
            changed=corpus();changed['records'][1]['title']='Taylor waits for blockers #JonathanTaylor'
            next_profile=build_profile(changed)
            with patch('posting_style.load',return_value=next_profile),patch('upgrades.worker',return_value=checked_copy()) as worker:
                new_key,_=identity(package,{})
                self.assertNotEqual(old_key,new_key)
                get_copy(tmp,package,{})
                worker.assert_called_once()
            self.assertEqual(cache.read_bytes(),saved)


if __name__=='__main__':unittest.main()
