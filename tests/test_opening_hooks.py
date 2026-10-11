import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from opening_hooks import (CHECKS, VERSION, cached_hook, context, generate_local,
                           get_hook, normalize, opening_options, source_checked, style_lessons)
from project_store import write

TEXT = 'The best cut is no cut. You keep your speed and momentum.'


def proposal():
    return dict(opening_text='No cut means keeping momentum', subject_quote='The best cut is no cut',
                payoff_quote='keep your speed and momentum', reason='Specific subject and supported benefit.')


def checked():
    p = proposal()
    return dict(p, source_check=dict(checked_opening_text=p['opening_text'],
                                    **{k: True for k in CHECKS}, reason='The clip explains keeping momentum.'))


def draft():
    return dict(proposal(), opening_text_options=[proposal()['opening_text'], 'Why avoid a cut to keep speed?'])


class OpeningHookTests(unittest.TestCase):
    def test_late_payoff_can_clarify_first_screen_without_inventing_speech(self):
        p = draft(); verdict = checked()['source_check']; stages = []
        with patch('shorts_editor.generate_json', side_effect=[p, verdict]) as gen:
            result = generate_local(TEXT, 'The best cut', [], None, lambda *args: stages.append(args))
        self.assertEqual(result, checked())
        self.assertIn('The best cut', gen.call_args_list[0].args[0])
        self.assertIn('speed and momentum', gen.call_args_list[0].args[0])
        self.assertEqual([s[0] for s in stages], [.1, .35])

    def test_exact_evidence_and_no_unsupported_acronym_or_absolute(self):
        normalize(proposal(), TEXT)
        for changed in [dict(subject_quote='a running back'), dict(payoff_quote='maximum speed'),
                        dict(opening_text='NFL cuts keep your momentum'),
                        dict(opening_text='No cut guarantees maximum speed'),
                        dict(opening_text='No cut means keeping momentum #NFL'),
                        dict(opening_text='Wait for it right here'),
                        dict(opening_text='why question about the main point'),
                        dict(opening_text='An essential lesson for champions'),
                        dict(opening_text='Who gets to keep their speed?'),
                        dict(opening_text='You keep your momentum alone'),
                        dict(opening_text='Keeping momentum? Why.'),
                        dict(opening_text='Momentum beats speed in every game'),
                        dict(opening_text="Keeping momentum means you don't need to outrun anyone")]:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                normalize(dict(proposal(), **changed), TEXT)
        with self.assertRaises(ValueError):
            normalize(dict(proposal(), subject_quote='best cut'), 'The best cutting move keeps your speed and momentum.')
        with self.assertRaises(ValueError):
            normalize(dict(proposal(),opening_text="Best guys don't need to lead"),"I don't need to break my feet. Trust those guys up front.")
        text='The best guys know the best cut is no cut. You keep your speed and momentum.'
        repaired=normalize(dict(proposal(), subject_quote='The best guys'),text)
        self.assertIn('cut',repaired['subject_quote']);self.assertIn(repaired['subject_quote'],text)

    def test_reviewer_must_check_the_exact_headline_with_true_booleans(self):
        v = checked()['source_check']
        self.assertTrue(source_checked(v, proposal()['opening_text']))
        for key in CHECKS:
            for value in (False, 1, 'true', None):
                self.assertFalse(source_checked(dict(v, **{key: value}), proposal()['opening_text']))
        self.assertFalse(source_checked(dict(v, checked_opening_text='A different headline'), proposal()['opening_text']))

    def test_bad_options_are_discarded_and_checker_cannot_invent_a_new_hook(self):
        options = opening_options(dict(draft(), opening_text_options=['Their cut is guaranteed to win', proposal()['opening_text']]), TEXT)
        self.assertEqual(options, [proposal()])
        with patch('shorts_editor.generate_json', side_effect=[draft(), dict(checked()['source_check'], checked_opening_text='A new invented hook')]*2):
            with self.assertRaises(ValueError): generate_local(TEXT, '', [], None)

    def test_one_retry_then_failure_does_not_silently_return_an_unchecked_title(self):
        p = draft(); bad = dict(checked()['source_check'], payoff_supported=False, reason='Unsupported benefit.')
        with patch('shorts_editor.generate_json', side_effect=[p, bad, p, bad]) as gen:
            with self.assertRaisesRegex(ValueError, 'Unsupported benefit'):
                generate_local(TEXT, '', [], None)
        self.assertEqual(gen.call_count, 4)
        self.assertIn('Unsupported benefit', gen.call_args_list[2].args[0])

    def test_invalid_writer_can_retry_and_empty_speech_never_loads_inference(self):
        with patch('shorts_editor.generate_json', side_effect=[{}, draft(), checked()['source_check']]) as gen:
            self.assertEqual(generate_local(TEXT, '', [], None), checked())
        self.assertEqual(gen.call_count, 3)
        with patch('shorts_editor.generate_json', side_effect=AssertionError('Unnecessary inference')):
            with self.assertRaises(ValueError): generate_local('', '', [], None)

    def test_library_selects_only_opening_lessons_from_unexcluded_good_patterns(self):
        examples = [dict(id='a', label='Good pattern', status='Needs review',
                        observations=dict(strengths=['Clear opening names the point.', 'Highest views.'])),
                    dict(id='b', label='Good pattern', status='Excluded',
                        observations=dict(strengths=['Old headline lesson.'])),
                    dict(id='c', label='Avoid this pattern', status='Ready for future reference',
                        observations=dict(strengths=['Misleading hook.']))]
        with patch('example_library.load', return_value=dict(examples=examples)):
            self.assertEqual(style_lessons('.'), [dict(example_id='a', lessons=['Clear opening names the point.'])])

    def test_cache_tracks_final_text_opening_timing_model_and_lessons(self):
        package = dict(fingerprint='p', final_transcript=TEXT)
        words = [dict(start=0, text='The best cut'), dict(start=4, text='payoff')]
        with patch('opening_hooks.style_lessons', return_value=[]):
            info = context('.', package, words, {})
            self.assertEqual(info['opening_speech'], 'The best cut')
            self.assertNotEqual(info['key'], context('.', dict(package, fingerprint='q'), words, {})['key'])
            self.assertNotEqual(info['key'], context('.', dict(package, final_transcript=TEXT+' More.'), words, {})['key'])
            self.assertNotEqual(info['key'], context('.', package, [dict(start=5, text='The best cut')], {})['key'])
            self.assertNotEqual(info['key'], context('.', package, words, dict(editor_model='qwen3.5-4b'))['key'])
        with patch('opening_hooks.style_lessons', return_value=[dict(example_id='x', lessons=['Clear opening.'])]):
            self.assertNotEqual(info['key'], context('.', package, words, {})['key'])

    def test_checked_cache_reopens_without_worker_and_failed_fresh_keeps_previous_cache(self):
        package = dict(fingerprint='p', final_transcript=TEXT)
        with tempfile.TemporaryDirectory() as tmp, patch('opening_hooks.style_lessons', return_value=[]):
            info = context('.', package, [], {})
            with patch('upgrades.worker', return_value=checked()) as worker:
                saved = get_hook(tmp, package, info)
                self.assertEqual(worker.call_args.args[0], 'opening_hook')
            path = Path(tmp)/'opening-hooks'/(info['key']+'.json'); original = path.read_bytes()
            with patch('upgrades.worker', side_effect=AssertionError('Cache missed')):
                self.assertEqual(get_hook(tmp, package, info), saved)
            with patch('upgrades.worker', side_effect=RuntimeError('Failed')):
                with self.assertRaises(RuntimeError): get_hook(tmp, package, info, force=True)
            self.assertEqual(path.read_bytes(), original)
            for field, value in [('version', 'old'), ('fingerprint', 'q'), ('editor_model', 'other')]:
                write(path, dict(saved, **{field: value})); self.assertIsNone(cached_hook(tmp, package, info))
            bad = copy.deepcopy(saved); bad['source_check']['subject_clear'] = False
            write(path, bad); self.assertIsNone(cached_hook(tmp, package, info))

    def test_worker_output_needs_valid_evidence_and_review_before_persisting(self):
        package = dict(fingerprint='p', final_transcript=TEXT)
        with tempfile.TemporaryDirectory() as tmp, patch('opening_hooks.style_lessons', return_value=[]):
            info = context('.', package, [], {})
            for bad in [dict(checked(), payoff_quote='invented facts'), dict(checked(), source_check={})]:
                with patch('upgrades.worker', return_value=bad), self.assertRaises(ValueError):
                    get_hook(tmp, package, info)
            self.assertFalse((Path(tmp)/'opening-hooks').exists())
