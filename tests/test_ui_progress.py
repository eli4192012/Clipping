import unittest
from ui_jobs import remaining_text,clock
class ProgressTests(unittest.TestCase):
    def test_estimate_overrun(self):
        self.assertIn('longer',remaining_text(150,100))
        self.assertNotIn('0s remaining',remaining_text(150,100))
    def test_eta_labeled_estimate(self):
        self.assertIn('estimate',remaining_text(30,100))
        self.assertEqual(clock(70),'1m 10s')
