import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analysis_settings import AnalysisSettings
from jobs import analysis_path, estimate_seconds, timing_key
from local_editor import cache_tag as editor_tag
from multimodal_curation import cache_tag as curation_tag
from upgrades import signature


class SettingsCompatibilityTests(unittest.TestCase):
    def settings(self):
        return dict(mode='Interview', minimum=5, maximum=60, windows=6,
                    semantic=True, vision=False, shorts_editor=True,
                    quality='Balanced', coverage=1., future_option={'keep': True})

    def test_validation_leaves_saved_values_and_unknown_fields_intact(self):
        settings = self.settings()
        original = copy.deepcopy(settings)
        self.assertEqual(AnalysisSettings.read(settings).mode, 'Interview')
        self.assertEqual(settings, original)

    def test_invalid_controls_fail_before_source_access_or_analysis(self):
        for changes in (dict(mode='invalid'), dict(minimum=float('nan')), dict(maximum=2),
                        dict(coverage=0), dict(windows=True), dict(semantic='true'), dict(minimum='5'), dict(maximum=True)):
            with self.assertRaises(ValueError):
                analysis_path({}, dict(self.settings(), **changes))

    def test_measured_estimates_keep_the_original_key_and_handle_corrupt_history(self):
        for mode in ('Interview', 'Podcast', 'Sports'):
            settings = dict(self.settings(), mode=mode)
            legacy = mode+str(settings['vision'])+str(settings['semantic'])+str(settings['windows'])+signature(settings)+('-shorts1' if settings.get('shorts_editor') and mode!='Sports' else '')+editor_tag(settings)+curation_tag(settings)
            self.assertEqual(timing_key(settings), legacy)
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source.mp4'
            source.write_text('Source metadata only')
            project = dict(folder=temp, source=str(source), duration=60)
            history = Path(temp) / 'ui-timing.json'
            settings = self.settings()
            history.write_text(json.dumps({timing_key(settings): 123.45}))
            self.assertEqual(estimate_seconds(project, settings), 123.45)
            for content in ('broken JSON', '[]', json.dumps({timing_key(settings): 'bad'})):
                history.write_text(content)
                self.assertGreater(estimate_seconds(project, settings), 0)

    def test_saved_analysis_is_reused_without_transcription_or_review(self):
        from jobs import analyze
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source.mp4'
            source.write_bytes(b'fixture')
            project = dict(folder=temp, source=str(source), duration=60, title='Fixture')
            settings = self.settings()
            saved = analysis_path(project, settings)
            saved.write_text('[]')
            with patch('jobs.get_transcript', side_effect=AssertionError('Repeated transcription')):
                self.assertEqual(analyze(project, settings, lambda *_: None), str(saved))
