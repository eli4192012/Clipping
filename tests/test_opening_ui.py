import json
import unittest
from unittest.mock import patch

import test_packaging_ui
from test_opening_hooks import checked


class OpeningUITests(test_packaging_ui.PackagingUITests):
    # Use the existing full-editor fixture, but only run this feature's tests here.
    test_review_screen_preserves_editor_and_uses_final_packages_without_model_work = None
    test_user_can_disable_hook_and_pacing_and_saved_look_is_retained = None
    test_legacy_manual_style_does_not_silently_gain_automatic_effects = None
    test_collection_assesses_candidates_without_rendering_or_reanalysis = None
    test_finished_clip_is_indexed_and_can_open_the_combination_builder = None

    def generate(self):
        with patch('upgrades.worker', return_value=checked()) as worker:
            next(b for b in self.app.button if b.label=='Generate AI opening').click().run()
        self.assertFalse(self.app.exception);worker.assert_called_once()
        return worker

    def test_generate_does_not_apply_or_rerender_then_apply_preserves_ranges_and_posting_text(self):
        app=self.app.run();self.assertFalse(app.exception)
        ranges=self.export.call_args.kwargs['ranges']
        next(t for t in app.text_input if t.label=='YouTube title').set_value('My posting title #Football')
        next(b for b in app.button if b.label=='Save YouTube Shorts text').click().run()
        posting=(self.folder/'platform-posts-v517.json').read_bytes()
        self.generate();self.assertEqual(self.export.call_count,1)
        self.assertFalse(self.analysis.with_suffix('.styles.json').exists())
        next(b for b in app.button if b.label=='Apply this opening text').click().run()
        self.assertFalse(app.exception);self.assertEqual(self.export.call_count,2)
        self.assertEqual(self.export.call_args.kwargs['ranges'],ranges)
        self.assertEqual(self.export.call_args.kwargs['presentation']['title'],checked()['opening_text'])
        self.assertEqual((self.folder/'platform-posts-v517.json').read_bytes(),posting)
        self.assertEqual(next(t for t in app.text_input if t.label=='Opening hook · leave blank to hide').value,checked()['opening_text'])
        self.assertEqual(json.loads(self.analysis.read_text()),[self.primary])
        app.run();self.assertFalse(app.exception);self.assertEqual(self.export.call_count,2)

    def test_failed_generation_preserves_legacy_manual_style_and_requires_no_repeated_job(self):
        key=f"{self.primary['start']}-{self.primary['end']}:Balanced"
        old=dict(layout='Portrait · two speakers',burn=False,title='Manual opening',position=.15,second=.8,trim_edges=False)
        path=self.analysis.with_suffix('.styles.json');path.write_text(json.dumps({key:old}))
        original=path.read_bytes();app=self.app.run()
        with patch('upgrades.worker',side_effect=RuntimeError('Inference failed')) as worker:
            next(b for b in app.button if b.label=='Generate AI opening').click().run()
            self.assertFalse(app.exception);app.run();worker.assert_called_once()
        self.assertTrue(path.read_bytes()==original);self.assertEqual(self.export.call_count,1)
        self.generate()
        next(b for b in app.button if b.label=='Apply this opening text').click().run()
        updated=next(iter(json.loads(path.read_text()).values()))
        self.assertEqual({k:v for k,v in updated.items() if k not in ('title','opening_hook_key','opening_hook_fingerprint')},
                         {k:v for k,v in old.items() if k!='title'})

    def test_manual_override_and_restore_clear_ai_provenance(self):
        app=self.app.run();self.generate()
        next(b for b in app.button if b.label=='Apply this opening text').click().run()
        next(t for t in app.text_input if t.label=='Opening hook · leave blank to hide').set_value('My reviewed opening')
        next(b for b in app.button if b.label=='Apply style').click().run()
        style=next(iter(json.loads(self.analysis.with_suffix('.styles.json').read_text()).values()))
        self.assertEqual(style['title'],'My reviewed opening');self.assertNotIn('opening_hook_key',style)
        next(b for b in app.button if b.label=='Apply this opening text').click().run()
        next(b for b in app.button if b.label=='Use suggested hook').click().run()
        style=next(iter(json.loads(self.analysis.with_suffix('.styles.json').read_text()).values()))
        self.assertNotIn('opening_hook_fingerprint',style);self.assertFalse(app.exception)

    def test_sports_and_empty_transcript_offer_manual_text_without_inference(self):
        app=self.app.run();self.assertFalse(app.exception)
        from streamlit.testing.v1 import AppTest
        script='''from opening_ui import opening_form
import streamlit as st
opening_form('.', '.', {'final_transcript': ''}, [], {'mode': 'Sports'}, {}, 'empty')
'''
        for code in [script,script.replace("'Sports'","'Interview'")]:
            test=AppTest.from_string(code).run();self.assertFalse(test.exception)
            self.assertTrue(any('write opening text' in i.value for i in test.info))
            self.assertFalse(test.button)

    def test_running_app_refreshes_older_opening_controls_without_new_inference(self):
        import importlib
        import opening_ui, opening_hooks
        app=self.app.run();self.assertFalse(app.exception)
        def old_form(folder,package):
            raise AssertionError('Older opening controls were called.')
        with patch.object(opening_ui,'OPENING_FORM_API',0),patch.object(opening_ui,'opening_form',old_form),patch('importlib.reload',wraps=importlib.reload) as reload:
            app.run();self.assertFalse(app.exception)
            self.assertEqual([c.args[0] for c in reload.call_args_list],[opening_hooks,opening_ui])
            self.assertEqual(opening_ui.OPENING_FORM_API,1)
        self.assertEqual(self.export.call_count,1)


if __name__=='__main__':unittest.main()
