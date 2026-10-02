import unittest
from upgrades import signature,transcript_file,assign_speakers,sentences_from_words,apply_scene_context
from jobs import analysis_path
class UpgradeTests(unittest.TestCase):
    def test_no_cross_model_cache_reuse(self):
        a=dict(mode='Interview',minimum=20,maximum=55,limit=3,vision=False,semantic=True,windows=2,quality='Balanced')
        b=dict(a,quality='Higher quality')
        self.assertNotEqual(analysis_path({'folder':'/tmp','source':__file__},a),analysis_path({'folder':'/tmp','source':__file__},b))
        self.assertNotEqual(transcript_file('/tmp',a),transcript_file('/tmp',b))
        self.assertNotEqual(signature(b),signature(dict(b,alignment=True)))
    def test_speaker_turn_splits_unpunctuated_speech(self):
        words=[dict(start=0,end=1,text='How'),dict(start=1,end=2,text='Fine')]
        assign_speakers(words,[dict(start=0,end=1,speaker='A'),dict(start=1,end=2,speaker='B')])
        self.assertEqual([s['speaker'] for s in sentences_from_words(words)],['A','B'])
    def test_scene_cut_only_extends_start(self):
        c=dict(start=10,end=22,passed=False)
        apply_scene_context([c],[8,15,20],40)
        self.assertEqual((c['start'],c['end'],c['passed']),(8,22,False))
    def test_distant_scene_does_not_add_unrelated_context(self):
        c=dict(start=10,end=22)
        apply_scene_context([c],[1,25],40)
        self.assertEqual(c['start'],10)
