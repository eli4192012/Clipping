import unittest
from interview import intro_start,apply_review_opening,apply_review_ending,protect_endings
from comparison import target_candidate

def sentences(texts):return [dict(start=i*4.,end=i*4.+3,text=text) for i,text in enumerate(texts)]
class V22Tests(unittest.TestCase):
    def test_previous_answer_fragment_not_setup(self):
        s=sentences(['Then guys up front did well.','And then a big kick.','How did you stay calm?','We trusted the preparation every day.'])
        c=target_candidate(s,10,55)
        self.assertEqual(c['first'],2)
    def test_speaker_switch_stops_named_subject_expansion(self):
        s=sentences(['Jonathan Taylor played well.','How did you stay calm?'])
        s[0]['speaker']='A';s[1]['speaker']='B'
        self.assertEqual(intro_start(s,1,0),1)
    def test_opening_cannot_drop_question_or_referenced_subject(self):
        s=sentences(['DeForest Buckner led the defense.','How does he set the standard?','He works hard every day.'])
        c=dict(first=0,question=1,last=2,start=0,end=11)
        for first in (1,2,-1,True):
            with self.assertRaises(ValueError):apply_review_opening(c,s,first)
    def test_answer_cannot_be_shortened_without_transition(self):
        s=sentences(['Why did you start?','I wanted to help my community.','That is still what motivates me.'])
        c=dict(first=0,question=0,last=2,start=0,end=11)
        with self.assertRaises(ValueError):apply_review_ending(c,s,{'end_sentence':1})
        self.assertEqual(c['end'],11)
    def test_padding_respects_next_word(self):
        c=dict(start=0,end=10)
        protect_endings([c],[dict(start=10.2,end=11,text='Next')],20)
        self.assertLess(c['end'],10.2)
        self.assertGreaterEqual(c['end'],10)
    def test_target_never_substitutes_unrelated_question(self):
        s=sentences(['Why did you start?','I wanted to help my community.'])
        with self.assertRaises(ValueError):target_candidate(s,50,55)
    def test_unpunctuated_word_at_end_prevents_padding(self):
        c=dict(start=0,end=10)
        protect_endings([c],[dict(start=9,end=11,text='word')],20)
        self.assertEqual(c['end'],10)
