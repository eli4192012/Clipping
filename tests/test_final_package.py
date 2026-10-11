import copy
import math
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from edit_timeline import remap_words
from final_package import get_package,hook_from_final,contains,semantic_emphasis,broll_suggestions,entities_from_final,editorial_assessment
from presentation import write_ass
from creator_profile import summarize


def words(text,start=0,speaker=None):
    return [dict(text=t,start=start+i*.3,end=start+(i+1)*.3,speaker=speaker) for i,t in enumerate(text.split())]


class FinalPackageTests(unittest.TestCase):
    def test_removed_context_does_not_leak_into_hooks_entities_tags_or_broll(self):
        speech=words('The Colts won in London.')+words('Spencer Schrader has a golden right foot.',5)
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.mp4';source.write_bytes(b'test source fingerprint')
            ranges=[dict(start=5,end=7.4)]
            candidate=dict(text='The Colts won in London. Spencer Schrader has a golden right foot.',title='Colts win in London',passed=False)
            package=get_package(tmp,source,candidate,speech,ranges,'Interview')
            self.assertNotIn('London',json.dumps(package))
            self.assertNotIn('Colts',json.dumps(package))
            self.assertNotIn('#NFL',json.dumps(package['posting']))
            self.assertIn('Spencer Schrader',package['entities'])
            self.assertEqual(len(set(json.dumps(p) for p in package['posting'].values())),3)
            self.assertTrue(contains(package['final_transcript'],package['hook']))
            self.assertTrue(all(s['start']>=0 and s['end']<=2.4+.001 for s in package['broll']))

    def test_packaging_cache_reuses_analysis_and_invalidates_only_on_final_input_changes(self):
        speech=words('It was an ugly win, but they found a way.')
        candidate=dict(passed=False);ranges=[dict(start=0,end=3.3)]
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';source.write_text('source')
            first=get_package(tmp,source,candidate,speech,ranges,'Interview')
            with patch('final_package.hook_from_final',side_effect=AssertionError('reanalyzed')):
                self.assertEqual(first,get_package(tmp,source,candidate,speech,ranges,'Interview'))
            corrected=copy.deepcopy(speech);corrected[3]['text']='beautiful'
            self.assertNotEqual(first['fingerprint'],get_package(tmp,source,candidate,corrected,ranges,'Interview')['fingerprint'])
            self.assertNotEqual(first['fingerprint'],get_package(tmp,source,candidate,speech,[dict(start=.3,end=3.3)],'Interview')['fingerprint'])

    def test_hook_keeps_conditional_contradiction_and_later_qualification(self):
        speech=words("So if you can not cut at all, that's the best cut because you keep your speed.")
        # Editorial roles can touch without being a real internal cut.
        mapped=remap_words(speech,[dict(start=0,end=2.4),dict(start=2.4,end=5.1)])
        hook=hook_from_final(mapped)
        self.assertIn('if you can not cut at all',hook.lower())
        self.assertIn('best cut',hook)
        self.assertTrue(contains(' '.join(w['text'] for w in speech),hook))
        qualified="It might be the best cut, but I don't think so."
        self.assertEqual(hook_from_final(words(qualified)),qualified)
        uncertain='Jonathan Taylor might not play, but that is not confirmed.'
        self.assertEqual(hook_from_final(words(uncertain)),uncertain)

    def test_semantic_emphasis_keeps_negation_and_output_timing_after_removal(self):
        speech=words('Long irrelevant question here.')+words('You can not cut at all, that is the best cut.',6)
        mapped=remap_words(speech,[dict(start=6,end=9.6)])
        emphasis=semantic_emphasis(mapped,hook_from_final(mapped))
        phrases=' '.join(p['text'] for p in emphasis['phrases'])
        self.assertIn('not cut at all',phrases)
        self.assertLessEqual(len(emphasis['indices']),math.ceil(len(mapped)/3))
        self.assertTrue(all(p['end']<=3.6+.001 for p in emphasis['phrases']))
        self.assertFalse(any(i>=len(mapped) for i in emphasis['indices']))
        inverted=words('This is not an ugly win.')
        e=semantic_emphasis(inverted,'')
        self.assertFalse(e['phrases']) # budget cannot safely include the negation, so omit emphasis.

    def test_ass_animation_is_semantic_only_and_does_not_shift_caption_times(self):
        speech=words('A secret weapon wins games.')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'captions.ass'
            write_ass(path,speech,0,1.5,720,1280,True,'',dict(indices=[1,2]),'Gentle pop')
            data=path.read_text();events=[line for line in data.splitlines() if line.startswith('Dialogue')]
            self.assertEqual(len(events),len(speech))
            self.assertEqual(data.count('\\t('),2)
            self.assertIn('0:00:00.30,0:00:00.60',data)
            self.assertNotIn('\\t(',events[0])

    def test_editorial_unknowns_stay_unscored_and_grounded_evidence_is_required(self):
        speech=words('The best cut is no cut.')
        candidate=dict(passed=False,audience_quality=dict(criteria=dict(opening=dict(rating=2,evidence='not present'))))
        report=editorial_assessment(candidate,speech,[dict(start=0,end=1.8)],'Interview')
        self.assertEqual(report[0]['assessment'],'Needs review')
        self.assertEqual(len(report),8)
        self.assertTrue(all('score' not in entry for entry in report))
        self.assertIn('Draft',report[-1]['assessment'])

    def test_profile_is_descriptive_and_does_not_guess_old_review_attributes(self):
        review=dict(scores=dict(Opening=4,Ending=5,Context=4,Pacing=5),details=dict(start=2,end=12))
        profile=summarize([review,{'bad':'data'}])
        self.assertEqual(profile['review_count'],1)
        self.assertEqual(profile['median_rated_duration'],10)
        self.assertFalse(profile['enough_for_patterns'])
        self.assertEqual(profile['answer_only_samples'],0)
        self.assertFalse(profile['visual_pacing'])
        edited=copy.deepcopy(review);edited['details'].update(ranges=[dict(start=2,end=4),dict(start=8,end=12)],answer_only=True,visual_pacing='Subtle',entities=['London'])
        duplicate=summarize([edited]*5)
        self.assertEqual(duplicate['review_count'],1)
        self.assertFalse(duplicate['enough_for_patterns'])
        records=[dict(edited,identity='source-'+str(i)) for i in range(5)]
        profile=summarize(records)
        self.assertEqual(profile['median_rated_duration'],6)
        self.assertEqual(profile['common_entities'],[('London',5)])

    def test_caption_changes_do_not_inherit_approval_of_different_text(self):
        original=words('The best cut is no cut.')
        changed=copy.deepcopy(original);changed[4]['text']='a'
        candidate=dict(text=' '.join(w['text'] for w in original),passed=True,edit_plan=dict(validation=dict(complete_ending=True)))
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source';source.write_text('source')
            package=get_package(tmp,source,candidate,changed,[dict(start=0,end=1.8)],'Interview')
            self.assertTrue(package['corrections_changed_text'])
            self.assertIn('Draft',package['assessment'][-1]['assessment'])

if __name__=='__main__':unittest.main()
