import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from before_after import build, directory, identity, reports, save_rating, signature, valid_report, snapshot
from ending_review import checked, CHECKS
from engine import subtitles
from project_store import read, write


class BeforeAfterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import imageio_ffmpeg
        cls.media=tempfile.TemporaryDirectory()
        cls.videos={}
        for length in (9.9,5.9):
            path=Path(cls.media.name)/(str(length)+'.mp4')
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-f','lavfi','-i','color=c=blue:s=64x64:r=10',
                            '-t',str(length),'-c:v','libx264','-pix_fmt','yuv420p','-y',str(path)],check=True)
            cls.videos[length]=path

    @classmethod
    def tearDownClass(cls):cls.media.cleanup()

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.source=self.root/'source.mp4';self.source.write_bytes(b'Original source; renderer isolated for tests')
        texts=['The golden signature earns a London Eye trip.','Thanks for coming to the pub.']
        words=[];sentences=[]
        for text,start,end in zip(texts,(0.,6.2),(5.8,9.8)):
            tokens=text.split();step=(end-start)/len(tokens)
            words += [dict(start=start+i*step,end=start+(i+1)*step,text=t) for i,t in enumerate(tokens)]
            sentences.append(dict(start=start,end=end,text=text))
        self.transcript=dict(words=words,sentences=sentences)
        self.tp=self.root/'transcript.json';write(self.tp,self.transcript)
        self.project=dict(source=str(self.source),folder=str(self.root),duration=10.,title='Prize fixture')
        self.spec=dict(root=str(self.root),project=self.project,transcript=str(self.tp),ranges=[dict(start=0.,end=9.9)],
                       mode='Podcast',name='Same prize moment',opening_text='Thanks for coming',
                       posting=dict(title='Saved title',description='My manual description'),editor_model='qwen3-4b')
        self.renders=0

    def tearDown(self):self.tmp.cleanup()

    def render(self,source,start,end,words,vertical,presentation,ranges):
        from edit_timeline import remap_words,timeline_duration
        self.renders+=1;length=round(timeline_duration(ranges),1)
        video=self.root/f'render-{self.renders}.mp4';shutil.copyfile(self.videos[length],video)
        captions=video.with_suffix('.srt');captions.write_text(subtitles(remap_words(words,ranges),0,length))
        return video,captions

    def ending(self,folder,data):
        endpoint=next(e['id'] for e in data['offered_endpoints'] if 'golden' in e['last_sentence'])
        return checked(dict(endpoint_id=endpoint,main_point_quote='golden signature earns a London Eye trip',
            payoff_quote='a London Eye trip',reason='Stops at the prize.',
            source_check=dict(checked_endpoint_id=endpoint,**{k:True for k in CHECKS},reason='Complete prize.')),data)

    def run_comparison(self,ending=None,opening=None,posting=None):
        with patch('engine.export_clip',side_effect=self.render), \
             patch('ending_review.get_ending',side_effect=ending or self.ending), \
             patch('opening_hooks.get_hook',side_effect=opening) if opening else patch('opening_hooks.get_hook',return_value=dict(opening_text='Golden signature earns a London Eye trip',source_check={})), \
             patch('social_copy.get_copy',side_effect=posting) if posting else patch('social_copy.get_copy',return_value=dict(title='Golden signature prize #LondonEye',description='The signature holder earns a special London outing.',source_check=dict(faithful=True))):
            return build(self.spec)

    def test_same_moment_trim_has_playable_assets_and_does_not_apply_project_state(self):
        originals={str(p):p.read_bytes() for p in (self.source,self.tp)}
        manual=self.root/'manual.edits.json';write(manual,{'keep':'my edit'})
        copy_file=self.root/'platform-posts-v517.json';write(copy_file,{'keep':'my copy'})
        report=self.run_comparison()
        self.assertTrue(valid_report(report));self.assertEqual(report['before']['source'],report['after']['source'])
        self.assertAlmostEqual(report['before']['duration'],9.9,places=1)
        self.assertAlmostEqual(report['after']['duration'],5.9,places=1)
        self.assertEqual(report['before']['posting']['description'],'My manual description')
        self.assertNotIn('Thanks',report['after']['final_transcript'])
        self.assertEqual(read(manual,{}),{'keep':'my edit'});self.assertEqual(read(copy_file,{}),{'keep':'my copy'})
        self.assertTrue(all(Path(p).read_bytes()==body for p,body in originals.items()))
        self.assertEqual(len(reports(self.root)),1)

    def test_saved_report_reopens_without_inference_or_rendering(self):
        first=self.run_comparison()
        with patch('engine.export_clip',side_effect=AssertionError('Render repeated')),patch('upgrades.worker',side_effect=AssertionError('Inference repeated')):
            self.assertEqual(build(self.spec),first)

    def test_failed_reviews_keep_cut_and_leave_unverified_new_posting_copy_empty(self):
        def failed(*args):raise RuntimeError('Local review failed')
        report=self.run_comparison(ending=failed,opening=failed,posting=failed)
        self.assertTrue(valid_report(report));self.assertEqual(report['before']['video'],report['after']['video'])
        self.assertEqual(report['after']['posting'],{})
        self.assertEqual([s['status'] for s in report['stages']].count('failed'),3)
        self.assertEqual(self.renders,1)

    def test_changed_source_or_subtitles_invalidates_saved_pair_without_deleting_it(self):
        report=self.run_comparison();saved=(directory(self.root)/(report['id']+'.json')).read_bytes()
        Path(report['after']['captions']['path']).write_text('Different captions')
        self.assertFalse(valid_report(report));self.assertFalse(reports(self.root)[0]['available'])
        self.assertEqual((directory(self.root)/(report['id']+'.json')).read_bytes(),saved)
        self.source.write_bytes(b'Changed source');self.assertFalse(valid_report(report))

    def test_cross_source_changed_opening_reordering_and_extended_cuts_are_not_valid_pairs(self):
        report=self.run_comparison()
        for mutation in ('source','range','extension','text'):
            altered=copy.deepcopy(report)
            if mutation=='source':altered['after']['source']['path']='/different/source.mp4'
            elif mutation=='range':altered['after']['ranges'][0]['start']=1
            elif mutation=='extension':altered['after']['ranges']=[dict(start=0.,end=10.)]
            else:altered['after']['final_transcript']='London trip first. The signature second.'
            with self.subTest(mutation=mutation):self.assertFalse(valid_report(altered))

    def test_ratings_persist_separately_from_comparison_and_reject_stale_assets(self):
        report=self.run_comparison();path=directory(self.root)/(report['id']+'.json');saved=path.read_bytes()
        review=save_rating(self.root,report['id'],'After is better','The prize finishes sooner.')
        self.assertEqual(review['choice'],'After is better');self.assertEqual(path.read_bytes(),saved)
        for report_id,choice in (('../bad','After is better'),(report['id'],'AI approved')):
            with self.assertRaises(ValueError):save_rating(self.root,report_id,choice,'')
        Path(report['after']['video']['path']).unlink()
        with self.assertRaises(ValueError):save_rating(self.root,report['id'],'After is better','')

    def test_changed_transcript_during_work_never_saves_mixed_report(self):
        def changed(*args):self.tp.write_text(self.tp.read_text()+' ');return dict(title='New copy',description='New description')
        with self.assertRaisesRegex(ValueError,'changed during'):self.run_comparison(posting=changed)
        self.assertFalse(list(directory(self.root).glob('*.json')))

    def test_invalid_subtitles_and_malformed_reports_are_not_silently_certified(self):
        report=self.run_comparison();side=report['after'];Path(side['captions']['path']).write_text('1\n00:00:00,000 --> 00:00:20,000\nInvented words.\n')
        with self.assertRaisesRegex(ValueError,'subtitles do not match'):
            snapshot(self.project,self.transcript,self.transcript['words'],side['ranges'],side['video']['path'],side['captions']['path'],'',{})
        write(directory(self.root)/'malformed.json',dict(version='before-after-1'))
        self.assertEqual(len(reports(self.root)),1)

    def test_opening_precedes_ending_and_is_rechecked_against_trimmed_speech(self):
        calls=[]
        def opening(folder,package,info):
            calls.append(('opening',package['final_transcript']))
            return dict(opening_text='Golden signature earns a London Eye trip',source_check={})
        def ending(folder,data):
            calls.append(('ending',data['opening_text']))
            return self.ending(folder,data)
        report=self.run_comparison(ending=ending,opening=opening)
        self.assertEqual([c[0] for c in calls],['opening','ending','opening'])
        self.assertEqual(calls[1][1],'Golden signature earns a London Eye trip')
        self.assertIn('Thanks',calls[0][1]);self.assertNotIn('Thanks',calls[2][1])
        self.assertTrue(valid_report(report))

    def test_failed_final_opening_check_does_not_put_the_old_title_on_a_shorter_cut(self):
        count=0
        def opening(*args):
            nonlocal count
            count+=1
            if count==2:raise ValueError('The opening no longer matches the final cut')
            return dict(opening_text='Prize headline',source_check={})
        report=self.run_comparison(opening=opening)
        self.assertEqual(report['after']['opening_text'],'')
        self.assertTrue(any(s['name']=='Final-cut opening text' and s['status']=='failed' for s in report['stages']))


if __name__=='__main__':unittest.main()
