"""Named local editors, bounded inference, and model-specific cache provenance."""
import hashlib
import json
from pathlib import Path
from engine import ROOT

QWEN35 = 'qwen3.5-4b'
QWEN3 = 'qwen3-4b'
SMALL = 'qwen3-1.7b'
QWEN35_REPO = 'mlx-community/Qwen3.5-4B-MLX-4bit'
QWEN35_REVISION = '32f3e8ecf65426fc3306969496342d504bfa13f3'
CHOICES = (QWEN35, QWEN3)
LABELS = {QWEN35: 'Qwen3.5 · 4B (experimental)', QWEN3: 'Qwen3 · 4B (recommended)', SMALL: 'Qwen3 · 1.7B'}
# Includes the loading/generation policy, without changing transcription caches.
IDENTITIES = {QWEN35: QWEN35 + ':' + QWEN35_REVISION + ':text-editor-1', QWEN3: QWEN3, SMALL: SMALL}
MAX_PROMPT_TOKENS = 8192


def model_path(key):
    if key not in LABELS: raise ValueError('Unknown local AI editor.')
    return ROOT / 'models' / key


def installed(key):
    path = model_path(key)
    if not (path / '.ready').exists(): return False
    if key != QWEN35: return (path / 'config.json').exists()
    try:
        ready = json.loads((path / '.ready').read_text())
        return (ready.get('revision') == QWEN35_REVISION and ready.get('repository') == QWEN35_REPO
                and all((path / name).is_file() for name in ('config.json', 'tokenizer.json', 'chat_template.jinja'))
                and (path / 'model.safetensors').stat().st_size == 3034300695)
    except (OSError, ValueError, AttributeError): return False


def preferred_editor():
    # The new model is installed for comparison; our saved-video checks did not
    # establish more reliable edits. Keep the existing editor as the default.
    return QWEN3 if installed(QWEN3) or not installed(QWEN35) else QWEN35


def selected_editor(payload, large=False):
    # Old saved jobs retain their original model unless the user selects another.
    key = payload.get('editor_model') or (QWEN3 if large or payload.get('quality') == 'Higher quality' else SMALL)
    model_path(key)
    return key


def cache_tag(settings):
    key = settings.get('editor_model')
    if not key or settings.get('mode') == 'Sports' or not settings.get('semantic', True): return ''
    return '-editor-' + hashlib.sha256(IDENTITIES[key].encode()).hexdigest()[:10]


def cache_folder(folder, key):
    return Path(folder) / ('editor-' + hashlib.sha256(IDENTITIES[key].encode()).hexdigest()[:10])


def load_bundle(payload, large=False):
    """Local files only. MLX LM loads the text tower, omitting unused vision weights."""
    import os
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from resource_limits import configure_mlx
    configure_mlx()
    key = selected_editor(payload, large)
    if not installed(key):
        raise RuntimeError(f'{LABELS[key]} is missing or incomplete. Run Download Models.command, or choose the previous editor in Advanced settings.')
    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler
    model, tokenizer = load(str(model_path(key)), tokenizer_config={'local_files_only': True, 'trust_remote_code': False})

    def bounded_generate(model, tokenizer, *, prompt, max_tokens, **kwargs):
        # Never truncate source text silently; retain it for manual review instead.
        if len(tokenizer.encode(prompt)) > MAX_PROMPT_TOKENS:
            raise ValueError('This moment exceeds the local editor context limit. Use a shorter source neighborhood or review it manually.')
        return generate(model, tokenizer, prompt=prompt, max_tokens=max_tokens, prefill_step_size=256, **kwargs)

    return model, tokenizer, bounded_generate, make_sampler(temp=0)


def download_qwen35():
    """Explicit setup only; inference never downloads or uploads anything."""
    from huggingface_hub import snapshot_download
    path = model_path(QWEN35)
    snapshot_download(QWEN35_REPO, revision=QWEN35_REVISION, local_dir=str(path), max_workers=2,
        allow_patterns=['*.json', '*.safetensors', '*.jinja', '*.txt', 'README.md', 'LICENSE*'])
    # A partial download must never be advertised as ready.
    required = ('config.json', 'tokenizer.json', 'chat_template.jinja', 'model.safetensors')
    if not all((path / name).is_file() for name in required) or (path / 'model.safetensors').stat().st_size != 3034300695:
        raise RuntimeError('Qwen3.5 download is incomplete. Run setup again to resume it.')
    from project_store import write
    write(path / '.ready', dict(repository=QWEN35_REPO, revision=QWEN35_REVISION))
    return path
