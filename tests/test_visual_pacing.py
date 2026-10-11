import copy
import unittest
from visual_pacing import plan_camera,speaker_turns,camera_filter,pair_crops


def scene(two=False):
    faces=[[250,100,100,130],[850,100,100,130]] if two else [[540,100,100,130]]
    return dict(width=1280,height=720,samples=[dict(time=t,faces=copy.deepcopy(faces)) for t in (0,3,6,9,12)])


def speech():
    result=[]
    for speaker,start,end,text in [('A',0,4,'Here is a complete statement.'),('B',4,4.4,'Yeah.'),('A',4.4,7,'And here is more context.'),('B',7,11,'This is my real reply.')]:
        parts=text.split();step=(end-start)/len(parts)
        result += [dict(start=start+i*step,end=start+(i+1)*step,text=p,speaker=speaker) for i,p in enumerate(parts)]
    return result


class VisualPacingTests(unittest.TestCase):
    def test_sports_does_not_zoom_or_switch_even_with_confirmed_mapping(self):
        plan=plan_camera(scene(True),speech(),[dict(start=0,end=12)],{},dict(pacing='Dynamic',conversation='Active Speaker',speaker_mapping_confirmed=True,speaker_positions={'A':'Left','B':'Right'}),'Sports')
        self.assertEqual(plan['decision']['kind'],'blur')
        self.assertFalse(plan['shots']);self.assertFalse(plan['pacing'])

    def test_unverified_or_stale_speaker_mapping_cannot_guess_faces(self):
        package=dict(fingerprint='edit-1')
        options=dict(conversation='Active Speaker',speaker_positions={'A':'Left','B':'Right'},speaker_mapping_confirmed=False)
        for verified,fp in [(False,'edit-1'),(True,'old-edit')]:
            options.update(speaker_mapping_confirmed=verified,speaker_mapping_fingerprint=fp)
            plan=plan_camera(scene(True),speech(),[dict(start=0,end=12)],package,options,'Podcast')
            self.assertEqual(plan['decision']['kind'],'split');self.assertFalse(plan['shots'])
            self.assertTrue(plan['warnings'])

    def test_confirmed_mapping_ignores_acknowledgement_and_holds_camera(self):
        options=dict(conversation='Automatic',speaker_mapping_confirmed=True,speaker_mapping_fingerprint='edit-1',speaker_positions={'A':'Left','B':'Right'})
        plan=plan_camera(scene(True),speech(),[dict(start=0,end=12)],dict(fingerprint='edit-1'),options,'Podcast')
        self.assertEqual(plan['decision']['kind'],'active')
        self.assertEqual([s['start'] for s in plan['shots']],[0,7])
        self.assertTrue(all(s['end']-s['start']>=3 for s in plan['shots']))
        self.assertIn('concat=n=2',camera_filter(plan))

    def test_no_faces_and_unstable_scene_keep_full_picture(self):
        empty=dict(width=1280,height=720,samples=[dict(time=0,faces=[])])
        for s in (empty,dict(scene(True),samples=scene(True)['samples']+[dict(time=13,faces=[])])):
            plan=plan_camera(s,speech(),[dict(start=0,end=14)],dict(fingerprint='x'),dict(conversation='Active Speaker',pacing='Dynamic'),'Podcast')
            self.assertEqual(plan['decision']['kind'],'blur');self.assertFalse(plan['shots']);self.assertFalse(plan['pacing'])

    def test_final_short_reply_cannot_create_a_sub_hold_camera_cut(self):
        words=[dict(start=i*.7,end=(i+1)*.7,text='word',speaker='A' if i<12 else 'B') for i in range(16)]
        options=dict(conversation='Automatic',speaker_mapping_confirmed=True,speaker_mapping_fingerprint='edit-1',speaker_positions={'A':'Left','B':'Right'})
        plan=plan_camera(scene(True),words,[dict(start=0,end=11.2)],dict(fingerprint='edit-1'),options,'Podcast')
        self.assertEqual(plan['decision']['kind'],'split');self.assertFalse(plan['shots'])

    def test_punch_in_occurs_only_at_a_safe_semantic_beat_and_is_restrained(self):
        ranges=[dict(start=0,end=12)];package=dict(sentences=[dict(start=0,text='Start'),dict(start=5,text='A useful explanation.')])
        plan=plan_camera(scene(),speech(),ranges,package,dict(pacing='Subtle',conversation='Off'),'Interview')
        self.assertEqual(len(plan['pacing']),1)
        self.assertEqual(plan['pacing'][0]['start'],5)
        self.assertEqual(plan['pacing'][0]['amount'],.035)
        self.assertIn('eval=frame',camera_filter(plan))
        without=plan_camera(scene(),speech(),ranges,{},dict(pacing='Dynamic',conversation='Off'),'Interview')
        self.assertFalse(without['pacing'])
        moving=scene();moving['samples'][0]['faces']=[[20,10,180,220]]
        unsafe=plan_camera(moving,speech(),ranges,package,dict(pacing='Dynamic',conversation='Off'),'Interview')
        self.assertFalse(unsafe['pacing'])

if __name__=='__main__':unittest.main()
