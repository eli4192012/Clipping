"""Render suggested edits with the studio's default look and reusable manifests."""
import hashlib
import json
from pathlib import Path
from project_store import read, write


def default_style(settings):
    from presentation import default_layout
    return dict(layout=default_layout(settings.get('portrait', False)), burn=True, position=.5, second=.75,
                pacing='Off' if settings['mode']=='Sports' else 'Subtle',
                conversation='Off' if settings['mode']=='Sports' else 'Automatic',
                semantic_emphasis=True, emphasis_style='Bold', packaging_version=1)


def render_identity(folder, source, transcript_path, start, end, style, words, final_ranges, package, render_ranges):
    signature = [Path(folder).name, Path(source).stat().st_mtime_ns, Path(transcript_path).stat().st_mtime_ns,
                 start, end, style, words]
    signature += ([final_ranges, package['fingerprint'], 'v517'] if style.get('packaging_version')
                  else ([render_ranges, 'v516'] if render_ranges else ['v55']))
    return hashlib.sha256(json.dumps(signature).encode()).hexdigest()[:24]


def export_suggestions(project, settings, result, progress=lambda p, label: None, checkpoint=lambda exports: None):
    from engine import export_clip
    from upgrades import transcript_file
    from final_package import get_package
    from edit_timeline import remap_words, timeline_duration
    from presentation import LAYOUTS
    from combined_video import register_clip
    folder, source = Path(project['folder']), Path(project['source'])
    transcript_path = transcript_file(folder, settings)
    transcript = read(transcript_path, None)
    candidates = read(result, None)
    if not isinstance(transcript, dict) or not isinstance(candidates, list):
        raise ValueError('The saved transcript or selected clips could not be read.')
    outputs, errors = [], []
    progress(0., 'Preparing selected clips for export')
    for index, original in enumerate(candidates):
        candidate = dict(original)
        ranges = (candidate.get('edit_plan') or {}).get('ranges')
        final_ranges = ranges or [dict(start=candidate['start'], end=candidate['end'])]
        # Match the editor's default candidate/package identity for direct cache reuse.
        candidate['edit_plan'] = candidate.get('edit_plan') or {}
        label = f'Exporting clip {index+1} of {len(candidates)}'
        try:
            from polish import corrected_words
            words = corrected_words(transcript['words'], read(transcript_path.with_suffix('.corrections.json'), {}))
            package = get_package(folder, source, candidate, words, final_ranges, settings['mode'], read(folder/'confirmed-names.json', []))
            style = dict(default_style(settings), title=package['hook'])
            style['_emphasis'] = package['emphasis']
            if style['layout'] == LAYOUTS[4]:
                from visual_pacing import inspect_scene, plan_camera
                try:
                    if settings['mode'] == 'Sports':
                        import av
                        with av.open(str(source)) as media:
                            scene = dict(width=media.streams.video[0].width, height=media.streams.video[0].height, samples=[])
                    else:
                        scene = inspect_scene(source, final_ranges)
                    style['_visual_plan'] = plan_camera(scene, remap_words(words, final_ranges), final_ranges, package, style, settings['mode'])
                except Exception:
                    from app_logging import log_exception
                    log_exception('Queued clip camera planning unavailable')
                    style['layout'] = LAYOUTS[1]
            identity = render_identity(folder, source, transcript_path, candidate['start'], candidate['end'], style, words, final_ranges, package, ranges)
            manifest = folder/f'render-{identity}.json'
            saved = read(manifest, None)
            if isinstance(saved, list) and len(saved)==2 and all(Path(p).is_file() for p in saved):
                video, captions = map(Path, saved)
            else:
                video, captions = export_clip(source, candidate['start'], candidate['end'], words, settings.get('portrait', False),
                    presentation=style, ranges=ranges, progress=lambda p, text: progress((index+p)/max(1, len(candidates)), label+' · '+text))
                write(manifest, [str(video), str(captions)])
            item = register_clip(folder, video, captions, candidate.get('title') or package['hook'], project['title'])
            outputs.append(dict(item, duration=timeline_duration(final_ranges)))
            checkpoint(outputs)
        except Exception as error:
            from app_logging import log_exception, redact
            log_exception('Queued clip export failed')
            errors.append(f'Clip {index+1}: '+redact(str(error))[:400])
        progress((index+1)/max(1, len(candidates)), f'Checked exports for {index+1} of {len(candidates)} clips')
    if errors:
        raise RuntimeError('Some clips could not export. Saved clips are kept; retry reuses them. '+'; '.join(errors))
    progress(1., f'{len(outputs)} clips exported' if outputs else 'No clips passed selection')
    return outputs
