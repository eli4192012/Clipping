import unittest
from sports_discovery import discover,choose_events,classify_frame
from modes import select_highlights
class DiscoveryTests(unittest.TestCase):
    def test_non_scoring_events_are_proposed(self):
        s=[dict(start=t,end=t+2,text=text) for t,text in [(5,'Pass is complete.'),(30,'Stroud is sandwiched.'),(60,'He has the first down.'),(90,'Touchdown!')]]
        self.assertEqual(len(discover(s,120)),4)
    def test_repeated_call_grouped_but_adjacent_play_kept(self):
        s=[dict(start=t,end=t+1,text='Touchdown!') for t in [10,15,30]]
        self.assertEqual(len(discover(s,80)),2)
    def test_negation_never_means_setup(self):
        self.assertEqual(classify_frame('Wide view of a play in progress, not lined up before the snap.'),'ACTION')
        self.assertEqual(classify_frame('A wide view of both teams lined up before the snap.'),'SETUP')
        self.assertEqual(classify_frame('A wide view of a play in progress from a sideline perspective.'),'ACTION')
    def test_word_timing_prevents_long_sentence_midpoint(self):
        s=[dict(start=0,end=60,text='He runs. Touchdown! More commentary.')]
        words=[dict(start=3,end=4,text='Touchdown!')]
        self.assertEqual(discover(s,100,words)[0]['anchor'],3.5)
    def test_silent_visual_proposals(self):
        self.assertEqual(discover([],60,samples=[dict(time=25,motion=.1,cut=False)])[0]['origin'],'motion')
    def test_count_limit_records_excluded_candidates(self):
        cs=[dict(start=t,end=t+10,text=str(t),rank=1) for t in (0,30,60)]
        reasons=[];selected=select_highlights(cs,120,'Sports',1,diagnostics=reasons)
        self.assertEqual(len(selected),1);self.assertEqual(len(reasons),2)
        self.assertTrue(all(r['reason']=='Clip count limit' for r in reasons))
    def test_review_budget_enforced(self):
        events=discover([dict(start=t,end=t+1,text='Touchdown') for t in range(0,100,20)],100)
        self.assertEqual(len(choose_events(events,2)),2)
