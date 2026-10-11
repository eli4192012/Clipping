import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from audience_quality import annotate
from multimodal_curation import VERSION,fingerprint,fuse
from sound_analysis import summarize
from test_multimodal_curation import audio,clip


class CurationUITests(unittest.TestCase):
    def candidate(self):
        c=annotate([clip()],'Podcast')[0]
        data=fuse(c,'Podcast',summarize(audio(),[dict(start=0,end=9)]),[],[],dict(mode='Podcast'))
        data.update(version=VERSION,fingerprint=fingerprint(c),visual_model='Test model',failures=[])
        c['multimodal_curation']=data;return c

    def test_view_shows_evidence_without_model_or_render_calls(self):
        c=self.candidate();script='from multimodal_ui import show\nshow('+repr(c)+')'
        with patch('upgrades.worker',side_effect=AssertionError('Unexpected inference')),patch('engine.export_clip',side_effect=AssertionError('Unexpected render')):
            app=AppTest.from_string(script).run();self.assertFalse(app.exception)
            self.assertTrue(any('Sound:' in m.value for m in app.markdown));self.assertEqual(len(app.dataframe),2)
            self.assertTrue(any('No emotion model' in x.value for x in app.caption))

    def test_changed_cut_does_not_display_stale_evidence(self):
        c=self.candidate();c['end']=8
        app=AppTest.from_string('from multimodal_ui import show\nshow('+repr(c)+')').run()
        self.assertFalse(app.exception);self.assertFalse(app.dataframe)
        self.assertTrue(any('earlier cut' in x.value for x in app.caption))

    def test_changed_source_does_not_display_stale_evidence(self):
        from sound_analysis import signature
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';source.write_bytes(b'original')
            c=self.candidate();c['multimodal_curation']['source']=signature(source)
            source.write_bytes(b'changed original')
            app=AppTest.from_string('from multimodal_ui import show\nshow('+repr(c)+')').run()
            self.assertFalse(app.exception);self.assertFalse(app.dataframe)
            self.assertTrue(any('source file' in x.value for x in app.caption))

    def test_explicit_existing_clip_review_keeps_boundaries_and_copy(self):
        import copy
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.write_bytes(b'original')
            posting=root/'platform-posts-v517.json';posting.write_text('{"saved":"manual copy"}')
            c=clip();before=copy.deepcopy(c);reviewed=self.candidate()
            project=dict(source=str(source),folder=temp,duration=20,title='Fixture')
            script='from multimodal_ui import review_form\nreview_form('+repr(project)+',{},'+repr(c)+",{'mode':'Podcast'})"
            with patch('ui_jobs.run_job',side_effect=lambda key,work,estimate:work(lambda *a:None)),patch('multimodal_ui.curate',return_value=([reviewed],dict(failures=[]))) as review:
                app=AppTest.from_string(script).run();app.button[0].click().run();self.assertFalse(app.exception)
                review.assert_called_once();self.assertEqual(c,before);self.assertEqual(source.read_bytes(),b'original')
                self.assertEqual(posting.read_text(),'{"saved":"manual copy"}')
                self.assertTrue(app.dataframe)
