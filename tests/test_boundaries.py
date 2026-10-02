import unittest
from modes import refine_sports_boundaries,select_highlights

class BoundaryTests(unittest.TestCase):
    def test_waits_for_settling_and_finishes_commentary(self):
        samples=[dict(time=i*.5,motion=.2 if 10<=i*.5<22 else .005,cut=False) for i in range(80)]
        candidate=dict(start=10,end=20,text='play',rank=1)
        refined=refine_sports_boundaries([candidate],samples,[dict(start=24,end=27,text='The play ends here.')],40)[0]
        self.assertEqual(refined['start'],8)
        self.assertGreaterEqual(refined['end'],27)
        self.assertLessEqual(refined['end'],28)
    def test_clamps_and_rechecks_overlap(self):
        samples=[dict(time=i,motion=.05,cut=False) for i in range(100)]
        original=[dict(start=0,end=10,text='one',rank=2),dict(start=11,end=20,text='two',rank=1)]
        refined=refine_sports_boundaries(original,samples,[],100)
        self.assertEqual(refined[0]['start'],0)
        self.assertEqual(len(select_highlights(refined,100,'Sports')),1)
    def test_cut_is_not_settling(self):
        samples=[dict(time=i*.5,motion=.2,cut=i==40) for i in range(80)]
        c=refine_sports_boundaries([dict(start=10,end=20,text='',rank=1)],samples,[],40)[0]
        self.assertIn('No sustained',c['boundary_notes'][1])

if __name__=='__main__': unittest.main()
