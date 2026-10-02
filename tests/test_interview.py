import unittest
from interview import interview_candidates,apply_review_ending,interview_content

def transcript(texts):
    return [dict(start=i*4,end=i*4+3,text=t) for i,t in enumerate(texts)]

class InterviewTests(unittest.TestCase):
    def test_intro_and_declarative_next_setup(self):
        s=transcript(['Nothing new for DeForest Buckner leading the way.', 'How much is he setting the standard?', 'Yeah, he works hard.', 'He sets the standard for our defense.', 'Against the Chiefs, no sacks allowed by your offensive line.', 'And Jonathan Taylor had four touchdowns.', 'How good is your line?', 'They are excellent.'])
        c=next(x for x in interview_candidates(s,20,55) if x['question']==1)
        self.assertEqual((c['first'],c['last']),(0,3))
        self.assertLess(c['end']-c['start'],20)
        self.assertNotIn('offensive line',c['text'])
    def test_unresolved_pronoun(self):
        s=transcript(['How much does he contribute?', 'He works hard every day.'])
        self.assertTrue(interview_candidates(s,20,55)[0]['context_uncertain'])
    def test_complete_short_answer(self):
        s=transcript(['Why did you start?', 'I wanted to help my community.', 'What comes next?', 'I plan to expand.'])
        c=interview_candidates(s,30,55)
        self.assertEqual(len(c),2)
        self.assertTrue(all(x['end']-x['start']<30 for x in c))
    def test_overlong_answer_not_truncated(self):
        s=transcript(['Why did you start?']+['I wanted to help my community.']*20)
        self.assertEqual(interview_candidates(s,20,30),[])
    def test_semantic_ending_bounds(self):
        s=transcript(['Why did you start?', 'I wanted to help.', 'It worked.', 'Let us discuss another topic.'])
        c=interview_candidates(s,20,55)[0]
        apply_review_ending(c,s,{'end_sentence':2})
        self.assertEqual(c['end'],11)
        for invalid in (True,-1,0,99,'2'):
            with self.assertRaises(ValueError): apply_review_ending(c,s,{'end_sentence':invalid})
    def test_sports_interview_routing(self):
        self.assertTrue(interview_content('Head Coach and WR preview matchup | Colts360'))
        self.assertFalse(interview_content('NFL Game Highlights'))

class SetupChainTests(unittest.TestCase):
    def test_declarative_setup_with_aside(self):
        s=transcript(['How good is your line?', 'They protect our offense very well.', "It's only fitting that we give more love to JT.", 'The first since Christian McCaffrey, I believe, to achieve this.', 'Now the first player in franchise history to do so.', 'How impressive is that?', 'It is very impressive for everyone.'])
        c=next(x for x in interview_candidates(s,20,55) if x['question']==0)
        self.assertEqual(c['last'],1)
