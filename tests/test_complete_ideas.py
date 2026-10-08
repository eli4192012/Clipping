import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shorts_editor import compile_plan, editorial_units, edit_candidate
from shorts_context import interview_sources, question_ids, restore_sentences, structural_check
from topic_cache import reviewed_topics
from test_shorts_editor import fixture


def timed(texts):
    words=[];sentences=[]
    for i,text in enumerate(texts):
        start=i*7.;tokens=text.split();step=5.9/len(tokens)
        for j,token in enumerate(tokens):words.append(dict(start=start+j*step,end=start+(j+1)*step-.01,text=token))
        sentences.append(dict(start=start,end=words[-1]['end'],text=text))
    c=dict(first=0,last=len(sentences)-1,start=0.,end=sentences[-1]['end'],text=' '.join(texts),topic_group=True,rank=1)
    return c,sentences,words


def decision(first,last,omitted=()):
    return dict(start_id=first,end_id=last,internal_cuts=[dict(ids=list(omitted),reason='Proposed removal.')] if omitted else [],
        meaning_preserved=True,ending_complete=True,standalone_context_check=dict(passed=True,reason='Pending independent review.'))


class CompleteIdeaTests(unittest.TestCase):
    def test_balanced_restores_a_clause_and_whisper_continuation(self):
        c,s,w=timed(['The rotation changes because we lost a starter, so everyone shares the work.',
                     'Our reserve enters in a pass situation', 'where we expect a throw.', 'The roles stay different.'])
        units=editorial_units(c,s,w)
        selected=next(u['id'] for u in units if u['sentence_start']==s[1]['start'])
        raw,restored=restore_sentences(decision(selected,selected),units,60)
        plan=compile_plan(raw,c,units,w,60)
        self.assertEqual(plan['final_transcript'],'Our reserve enters in a pass situation where we expect a throw.')
        self.assertTrue(restored)
        structural_check(plan,units,'Podcast')

    def test_balanced_does_not_delete_the_middle_of_an_explanation(self):
        c,s,w=timed(['The backup gets more playing time.', 'His practice work earned the opportunity.',
                     'The rotation gives every player a useful role.', 'The whole group improves together.'])
        units=editorial_units(c,s,w)
        raw,restored=restore_sentences(decision(0,3,(1,2)),units,60)
        plan=compile_plan(raw,c,units,w,60)
        self.assertEqual(plan['final_transcript'],c['text'])
        self.assertEqual(restored,[1,2])

    def test_restoring_context_never_squeezes_a_long_thought_into_the_limit(self):
        c,s,w=timed(['The reason is a shortage of players, and we share the work across the whole rotation.'])
        units=editorial_units(c,s,w)
        self.assertGreater(len(units),1)
        with self.assertRaisesRegex(ValueError,'exceeds the maximum'):
            restore_sentences(decision(0,0),units,3)

    def test_one_interview_question_cannot_be_overruled_by_model_approval(self):
        c,s,w=timed(['What changed in the rotation?', 'The backup joins the rotation.',
                     'Why did that happen?', 'His practice work earned the opportunity.'])
        units=editorial_units(c,s,w,'Interview')
        plan=compile_plan(decision(0,3),c,units,w,60)
        with self.assertRaisesRegex(ValueError,'at most one'):
            structural_check(plan,units,'Interview')

    def test_a_complete_earlier_answer_can_stop_before_another_question(self):
        c,s,w=timed(['What changed in the rotation?', 'The backup joins the rotation.',
                     'Why did that happen?', 'His practice work earned the opportunity.'])
        units=editorial_units(c,s,w,'Interview')
        raw=decision(0,1);raw['internal_cuts']=[]
        plan=compile_plan(raw,c,units,w,60)
        structural_check(plan,units,'Interview')

    def test_punctuation_free_confirmation_inside_a_whisper_sentence_is_counted(self):
        c,s,w=timed(['What role does the reserve play?',
                     'He earns playing time so with the reserve he plays middle for you as opposed to outside.',
                     "That's correct, yeah."])
        self.assertEqual(question_ids(s),[0,1])
        units=editorial_units(c,s,w,'Interview')
        plan=compile_plan(decision(0,len(units)-1),c,units,w,60)
        with self.assertRaisesRegex(ValueError,'at most one'):
            structural_check(plan,units,'Interview')

    def test_real_question_with_first_person_setup_is_not_hidden(self):
        _,s,_=timed(['We saw you change the rotation, why did you do that?', 'The backup earned a chance.'])
        self.assertEqual(question_ids(s),[0])
        _,s,_=timed(['Well, what changed in the rotation?', 'The backup earned a chance.'])
        self.assertEqual(question_ids(s),[0])

    def test_fragment_is_not_a_question_and_source_excludes_followup_announcement(self):
        c,s,w=timed(['What changes with the rotation?', 'The reserve enters in a pass situation',
                     'where we were', 'expecting a throw.', 'One other follow -up.',
                     'How did the reserve improve?', 'His practice work made the difference.'])
        self.assertEqual(question_ids(s),[0,5])
        sources=interview_sources(s,60)
        self.assertEqual([(x['first'],x['last']) for x in sources],[(0,3),(5,6)])
        self.assertNotIn('follow -up',sources[0]['text'])

    def test_reporter_setup_or_unfinished_speech_cannot_be_final_payoff(self):
        for ending in ('One other follow -up.', "It seems like you're getting stronger.", 'The reserve enters in a pass situation'):
            c,s,w=timed(['The rotation helps the defense.',ending]);units=editorial_units(c,s,w)
            plan=compile_plan(decision(0,len(units)-1),c,units,w,60)
            with self.assertRaises(ValueError):structural_check(plan,units,'Podcast')

    def test_unexplained_comparison_cannot_be_the_final_answer(self):
        c,s,w=timed(['How do the roles differ?', 'Two totally different positions.'])
        units=editorial_units(c,s,w,'Interview');plan=compile_plan(decision(0,1),c,units,w,60)
        with self.assertRaisesRegex(ValueError,'before explaining'):
            structural_check(plan,units,'Interview')
        c,s,w=timed(['How do the roles differ?', 'The reserve covers passes while the starter stops the run.',
                     'Two totally different positions.'])
        units=editorial_units(c,s,w,'Interview');plan=compile_plan(decision(0,len(units)-1),c,units,w,60)
        structural_check(plan,units,'Interview')

    def test_a_question_is_not_accepted_as_evidence_of_an_explanation(self):
        c,s,w,_,v=fixture();raw=decision(0,3)
        v['context_ids']=dict(subject=0,explanation=0,conclusion=3);v['question_answered']=True
        with patch('shorts_editor.generate_json',side_effect=[raw,v,copy.deepcopy(v)]):
            with self.assertRaisesRegex(ValueError,'evidence is missing'):
                edit_candidate(c,s,w,30,'Balanced',None,lambda:None,mode='Interview')

    def test_structural_repair_is_bounded_and_checked_before_saving(self):
        c,s,w,raw,v=fixture();bad=decision(0,0)
        with patch('shorts_editor.seed_decision',return_value=bad),patch('shorts_editor.generate_json',side_effect=[bad,raw,v]) as generate:
            result=edit_candidate(c,s,w,30,'Balanced',None,lambda:None,mode='Interview')
        self.assertEqual(generate.call_count,3)
        self.assertIn('One local repair',result['edit_plan']['decision_basis'])
        self.assertEqual(result['text'],'The best cut is no cut. You keep your speed and momentum.')

    def test_missing_beginning_of_a_reporter_question_is_not_a_complete_opening(self):
        for text in ("things but like what's impressed you about the player?", "things, but what's impressed you about the player?"):
            c,s,w=timed([text, 'The player uses quickness to beat blockers.'])
            units=editorial_units(c,s,w,'Interview');plan=compile_plan(decision(0,len(units)-1),c,units,w,60)
            with self.assertRaisesRegex(ValueError,'unfinished interviewer question'):
                structural_check(plan,units,'Interview')

    def test_an_unnamed_person_opening_cannot_use_a_name_only_from_outside_context(self):
        c,s,w=timed(["He's always working hard.", 'His teammates appreciate his effort.'])
        units=editorial_units(c,s,w);plan=compile_plan(decision(0,1),c,units,w,60)
        with self.assertRaisesRegex(ValueError,'lost the subject'):structural_check(plan,units,'Podcast')

    def test_genuinely_brief_complete_idea_still_passes_below_preferred_minimum(self):
        c,s,w,raw,v=fixture()
        v.pop('context_evidence');v['context_ids']=dict(subject=0,explanation=1,conclusion=1)
        with patch('shorts_editor.generate_json',side_effect=[raw,v]):
            result=edit_candidate(c,s,w,30,'Balanced',None,lambda:None,minimum=20)
        self.assertLess(result['edit_plan']['recommended_duration'],20)
        self.assertEqual(result['edit_plan']['validation']['context_evidence']['explanation'],'You keep your speed and momentum.')

    def test_all_true_booleans_with_invented_or_missing_context_evidence_are_rejected(self):
        c,s,w,raw,v=fixture()
        for change in (dict(context_evidence={}),dict(context_evidence=dict(subject='Invented subject from outside',explanation='You keep your speed',conclusion='speed and momentum.')),
                       dict(context_ids=dict(subject=True,explanation=1,conclusion=1)),dict(context_ids=dict(subject=99,explanation=1,conclusion=1)),
                       dict(short_complete_reason='')):
            bad=dict(copy.deepcopy(v),**change)
            with self.subTest(change=change),patch('shorts_editor.generate_json',side_effect=[raw,bad,copy.deepcopy(bad)]):
                with self.assertRaises(ValueError):edit_candidate(c,s,w,30,'Balanced',None,lambda:None)

    def test_invalid_evidence_ids_get_one_recheck_without_retranscription_or_replanning(self):
        c,s,w,raw,v=fixture();wrong=copy.deepcopy(v)
        wrong['context_ids']=dict(subject=0,explanation=1,conclusion=99)
        v['context_ids']=dict(subject=0,explanation=1,conclusion=1)
        with patch('shorts_editor.generate_json',side_effect=[raw,wrong,v]) as generate:
            result=edit_candidate(c,s,w,30,'Balanced',None,lambda:None)
        self.assertEqual(generate.call_count,3)
        self.assertEqual(result['edit_plan']['validation_attempts'][0]['context_ids']['conclusion'],99)
        self.assertEqual(result['edit_plan']['validation']['context_evidence']['conclusion'],'You keep your speed and momentum.')

    def test_failed_edit_is_diagnostic_only_even_in_balanced_processing_mode(self):
        c,s,w=timed(['What changed in the rotation?', 'The backup joins the rotation.'])
        payload=dict(sentences=s,words=w,maximum=60,minimum=20,mode='Interview',quality='Balanced',shorts_editor=True)
        with patch('shorts_editor.edit_candidate',side_effect=ValueError('Missing explanation')):
            result=reviewed_topics(payload,lambda:None)
        self.assertEqual(len(result),1)
        self.assertFalse(result[0]['passed']);self.assertTrue(result[0]['boundary_rejected'])
        self.assertEqual(result[0]['text'],c['text'])

    def test_old_analysis_and_transcript_are_kept_when_new_selection_is_requested(self):
        from jobs import analysis_path
        from project_store import runs_for
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);source=folder/'source.mp4';source.write_bytes(b'preserve')
            project=dict(folder=tmp,source=str(source),duration=60,title='Fixture')
            settings=dict(mode='Interview',minimum=20,maximum=65,vision=False,semantic=True,windows=6,shorts_editor=True,quality='Balanced')
            new=analysis_path(project,settings)
            old=folder/new.name.replace('-shorts5-','-shorts1-');old.write_text('[]')
            transcript=folder/'transcript.json';transcript.write_text('{"words": []}')
            prior=[p.read_bytes() for p in (source,old,transcript)]
            self.assertNotEqual(new,old);self.assertFalse(new.exists())
            new.write_text('[]')
            runs=runs_for(project)
            self.assertEqual(len(runs),2);self.assertTrue(all(r['settings']['shorts_editor'] for r in runs))
            self.assertEqual(prior,[p.read_bytes() for p in (source,old,transcript)])


if __name__=='__main__':unittest.main()
