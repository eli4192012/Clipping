import unittest
from modes import speech_candidates, select_highlights, sports_candidates, PROFILES

class ModesTest(unittest.TestCase):
    def test_overlap_and_budget(self):
        candidates=[dict(start=a,end=b,text=f'unique word{a} item{a}',rank=10-a,passed=True) for a,b in [(0,50),(30,85),(90,145),(150,175)]]
        for mode in PROFILES:
            result=select_highlights(candidates,180,mode)
            self.assertLessEqual(sum(c['end']-c['start'] for c in result),180*PROFILES[mode]['coverage'])
            self.assertTrue(all(a['end']<=b['start'] or b['end']<=a['start'] for i,a in enumerate(result) for b in result[i+1:]))
    def test_question_answer_not_next_question(self):
        sentences=[dict(start=i*10,end=(i+1)*10,text=t) for i,t in enumerate(['Why did you start?', 'I wanted to learn.', 'Practice helped me.', 'What happened next?', 'I won.'])]
        clips=speech_candidates(sentences,15,50,'Interview')
        self.assertTrue(clips)
        self.assertTrue(all(c['first'] not in (1,4) for c in clips))
        self.assertTrue(all(not c['text'].endswith('?') for c in clips))
        self.assertTrue(all(c['text'].count('?') <=1 for c in clips))
    def test_modes_differ(self):
        s=[dict(start=i*10,end=(i+1)*10,text=t) for i,t in enumerate(['Why did you start?', 'Once I faced a problem.', 'I practiced.', 'Finally I learned the lesson.'])]
        self.assertNotEqual(speech_candidates(s,15,50,'Interview'),speech_candidates(s,15,50,'Podcast'))
    def test_sports_without_speech(self):
        samples=[dict(time=i*.5,motion=.1 if i%40 in range(5,30) else .005,cut=i%40==0) for i in range(360)]
        clips=select_highlights(sports_candidates([],samples,180,10,35),180,'Sports')
        self.assertTrue(clips)
        self.assertTrue(all(not c['passed'] for c in clips))
        self.assertLessEqual(sum(c['end']-c['start'] for c in clips),63)
    def test_no_forced_full_video(self):
        self.assertEqual(select_highlights([dict(start=0,end=29,text='story',rank=1)],29,'Podcast'),[])

if __name__=='__main__': unittest.main()
