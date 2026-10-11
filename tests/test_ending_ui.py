import json
import unittest
from unittest.mock import patch

import test_packaging_ui
from ending_review import context, compile_choice, CHECKS
from project_store import read


class EndingUITests(test_packaging_ui.PackagingUITests):
    test_review_screen_preserves_editor_and_uses_final_packages_without_model_work = None
    test_user_can_disable_hook_and_pacing_and_saved_look_is_retained = None
    test_legacy_manual_style_does_not_silently_gain_automatic_effects = None
    test_collection_assesses_candidates_without_rendering_or_reanalysis = None
    test_finished_clip_is_indexed_and_can_open_the_combination_builder = None

    def setUp(self):
        super().setUp()
        availability=patch('ending_ui.installed',return_value=True);availability.start();self.patches.append(availability)
        transcript=read(self.folder/'transcript.json',{})
        trailing="Thanks for coming to this week's show."
        tokens=trailing.split();step=3.95/len(tokens)
        transcript['words'] += [dict(start=20+i*step,end=20+(i+1)*step,text=t) for i,t in enumerate(tokens)]
        transcript['sentences'].append(dict(start=20,end=23.95,text=trailing))
        (self.folder/'transcript.json').write_text(json.dumps(transcript))
        self.primary['edit_plan']['ranges'][-1]['role']='context'
        self.primary['edit_plan']['ranges'].append(dict(start=20.,end=24.,role='payoff',reason='Old trailing ending.'))
        self.primary['end']=24.;self.primary['text']+=' '+trailing
        self.primary['edit_plan']['final_transcript']=self.primary['text']
        self.primary['edit_plan']['recommended_duration']+=4
        self.analysis.write_text(json.dumps([self.primary]))
        self.data=context(test_packaging_ui.ROOT,transcript,self.primary['edit_plan']['ranges'],25,self.settings,self.primary['title'],str(self.source)+':'+str(self.source.stat().st_mtime_ns))
        endpoint=next(e['id'] for e in self.data['offered_endpoints'] if 'momentum' in e['last_sentence'])
        self.result=dict(compile_choice(self.data,endpoint),main_point_quote='You keep your speed and momentum',payoff_quote='your speed and momentum',reason='Stops before the closing thanks.',source_check=dict(checked_endpoint_id=endpoint,**{k:True for k in CHECKS},reason='The explanation is complete.'))

    def generate(self):
        with patch('local_editor.installed',return_value=True),patch('upgrades.worker',return_value=self.result) as worker:
            next(b for b in self.app.button if b.label=='Review ending with AI').click().run()
        self.assertFalse(self.app.exception);worker.assert_called_once()
        return worker

    def test_generation_is_review_only_and_apply_preserves_internal_cuts_and_sources(self):
        app=self.app.run();self.assertFalse(app.exception)
        analysis=self.analysis.read_bytes();transcript=(self.folder/'transcript.json').read_bytes()
        prior=self.export.call_args.kwargs['ranges']
        next(t for t in app.text_input if t.label=='YouTube title').set_value('My posted title #Momentum')
        next(b for b in app.button if b.label=='Save YouTube Shorts text').click().run()
        posts=(self.folder/'platform-posts-v517.json').read_bytes()
        self.generate();self.assertEqual(self.export.call_count,1)
        self.assertFalse(self.analysis.with_suffix('.endings.json').exists())
        from final_package import get_package
        with patch('final_package.get_package',wraps=get_package) as package:
            next(b for b in app.button if b.label=='Apply this ending').click().run()
        plan=package.call_args.args[2]['edit_plan']
        self.assertEqual(plan['reason_for_each_cut'],[r['reason'] for r in plan['ranges']])
        self.assertEqual(plan['standalone_context_check']['reason'],self.result['source_check']['reason'])
        self.assertFalse(app.exception);self.assertEqual(self.export.call_count,2)
        self.assertEqual(self.export.call_args.kwargs['ranges'],self.result['ranges'])
        self.assertEqual(self.export.call_args.kwargs['ranges'][0]['start'],prior[0]['start'])
        self.assertEqual(self.analysis.read_bytes(),analysis);self.assertEqual((self.folder/'transcript.json').read_bytes(),transcript)
        self.assertEqual((self.folder/'platform-posts-v517.json').read_bytes(),posts)
        app.run();self.assertFalse(app.exception);self.assertEqual(self.export.call_count,2)

    def test_restore_uses_previous_export_and_does_not_reinfer(self):
        app=self.app.run();self.generate()
        next(b for b in app.button if b.label=='Apply this ending').click().run()
        next(b for b in app.button if b.label=='Restore prior ending').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(read(self.analysis.with_suffix('.endings.json'),{}),{})
        self.assertEqual(self.export.call_count,2)  # Original cached render reopens.

    def test_failed_fresh_review_preserves_applied_cut(self):
        app=self.app.run();self.generate()
        next(b for b in app.button if b.label=='Apply this ending').click().run()
        saved=self.analysis.with_suffix('.endings.json').read_bytes()
        with patch('local_editor.installed',return_value=True),patch('upgrades.worker',side_effect=RuntimeError('Local review failed')):
            next(b for b in app.button if b.label=='Review ending again').click().run()
        self.assertFalse(app.exception);self.assertEqual(self.analysis.with_suffix('.endings.json').read_bytes(),saved)
        self.assertEqual(self.export.call_count,2)

    def test_manual_opening_change_keeps_applied_speech_and_warns_about_old_review(self):
        app=self.app.run();self.generate()
        next(b for b in app.button if b.label=='Apply this ending').click().run()
        next(t for t in app.text_input if t.label=='Opening hook · leave blank to hide').set_value('A different reviewed opening')
        next(b for b in app.button if b.label=='Apply style').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(self.export.call_args.kwargs['ranges'],self.result['ranges'])
        self.assertTrue(any('earlier opening text' in w.value for w in app.warning))

    def test_restoring_suggested_boundaries_clears_only_the_ending_override(self):
        app=self.app.run();self.generate()
        next(b for b in app.button if b.label=='Apply this ending').click().run()
        next(b for b in app.button if b.label=='Restore suggested boundaries').click().run()
        self.assertFalse(app.exception);self.assertFalse(read(self.analysis.with_suffix('.endings.json'),{}))
        self.assertEqual(self.export.call_count,2)

    def test_sports_controls_never_start_ending_inference(self):
        from streamlit.testing.v1 import AppTest
        script="from ending_ui import ending_form\nending_form('.', None, None, 'sports')"
        app=AppTest.from_string(script).run();self.assertFalse(app.exception)
        self.assertFalse(app.button);self.assertTrue(any('boundary controls' in i.value for i in app.info))

    def test_editor_choice_is_local_to_this_review_and_does_not_change_project_settings(self):
        app=self.app.run();self.assertFalse(app.exception)
        next(s for s in app.selectbox if s.label=='Ending review editor').set_value('qwen3.5-4b').run()
        self.assertEqual(app.session_state['settings'],self.settings)
        worker=self.generate()
        self.assertEqual(worker.call_args.args[1]['editor_model'],'qwen3.5-4b')
        self.assertEqual(self.export.call_count,1)

    def test_loaded_older_controls_refresh_without_inference_or_changing_sources(self):
        import importlib,ending_ui,ending_review
        app=self.app.run();saved=self.analysis.read_bytes()
        with patch.object(ending_ui,'ENDING_FORM_API',0),patch.object(ending_ui,'ending_form',side_effect=AssertionError('Old controls')),patch('importlib.reload',wraps=importlib.reload) as reload:
            app.run();self.assertFalse(app.exception)
            self.assertEqual([c.args[0] for c in reload.call_args_list],[ending_review,ending_ui])
        self.assertEqual(self.analysis.read_bytes(),saved);self.assertEqual(self.export.call_count,1)

    def test_comparison_handoff_uses_the_prior_timeline_without_replacing_applied_end(self):
        app=self.app.run();self.generate()
        next(b for b in app.button if b.label=='Apply this ending').click().run()
        saved=self.analysis.with_suffix('.endings.json').read_bytes()
        with patch('before_after_ui.show') as show:
            next(b for b in app.button if b.label=='Compare before and after').click().run()
        self.assertFalse(app.exception);show.assert_called_once()
        request=app.session_state['before_after_pending']
        self.assertEqual(request['ranges'],self.data['ranges'])
        self.assertEqual(request['editor_model'],'qwen3-4b')
        self.assertEqual(request['transcript'],str(self.folder/'transcript.json'))
        self.assertEqual(self.analysis.with_suffix('.endings.json').read_bytes(),saved)
        self.assertEqual(self.export.call_count,2)


if __name__=='__main__':unittest.main()
