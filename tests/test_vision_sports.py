import unittest
from vision_sports import event_proposals,validate_review,football_hint
class VisionTests(unittest.TestCase):
    def test_event_deduplication(self):
        s=[dict(start=x,end=x+2,text='Touchdown!') for x in (10,15,20,70)]
        self.assertEqual(len(event_proposals(s,100)),2)
    def test_invalid_model_output(self):
        t=list(range(160,208,2))
        for v in [{},dict(setup_frame=1,action_frame=12,outcome_frame=13,end_frame=14,original_action_visible=True),dict(setup_frame=10,action_frame=9,outcome_frame=13,end_frame=14,original_action_visible=True)]:
            with self.assertRaises(ValueError):validate_review(v,t,185)
    def test_valid_indices(self):
        t=list(range(160,208,2))
        self.assertEqual(validate_review(dict(setup_frame=10,action_frame=12,outcome_frame=13,end_frame=20,original_action_visible=True),t,185),(180,200))
    def test_replay_only_rejected(self):
        with self.assertRaises(ValueError):validate_review(dict(setup_frame=10,action_frame=12,outcome_frame=13,end_frame=20,original_action_visible=False),list(range(160,208,2)),185)
    def test_mode_warning(self):
        self.assertTrue(football_hint('NFL highlights'))
        self.assertFalse(football_hint('A cooking interview'))

class SequenceTests(unittest.TestCase):
    def test_nearest_visible_play(self):
        from vision_sports import boundaries_from_labels
        labels=['CLOSEUP']*4+['SETUP','ACTION','ACTION','CLOSEUP','CLOSEUP','CLOSEUP','CLOSEUP','SETUP','ACTION','ACTION','ACTION','CLOSEUP']
        start,end=boundaries_from_labels({'labels':labels},[173.5+i*2 for i in range(16)],185.5)
        self.assertEqual(start,181.5)
        self.assertEqual(end,193.5)
    def test_no_setup_fails_closed(self):
        from vision_sports import boundaries_from_labels
        with self.assertRaises(ValueError):boundaries_from_labels({'labels':['ACTION']*16},[173.5+i*2 for i in range(16)],185.5)
    def test_missing_frames_fails_closed(self):
        from vision_sports import boundaries_from_labels
        with self.assertRaises(ValueError):boundaries_from_labels({'labels':[]},[1,2,3],2)

class EarlierPlayTests(unittest.TestCase):
    def test_previous_play_cannot_stand_in_for_event(self):
        from vision_sports import boundaries_from_labels
        times=[161.5+i*2 for i in range(24)]
        labels=['CLOSEUP','CLOSEUP','ACTION','SETUP','ACTION','ACTION','ACTION','CLOSEUP','CLOSEUP','CLOSEUP']+['ACTION']*6+['CLOSEUP']*8
        with self.assertRaises(ValueError):boundaries_from_labels({'labels':labels},times,185.5)

    def test_uncertain_draft_follows_action_at_event(self):
        from vision_sports import uncertain_bounds
        times=[161.5+i*2 for i in range(24)]
        labels=['CLOSEUP']*10+['ACTION']*6+['CLOSEUP']*8
        self.assertEqual(uncertain_bounds({'labels':labels},times,185.5,1100),(179.5,195.5))
