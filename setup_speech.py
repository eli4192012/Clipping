"""Run with .venv-speech/bin/python. Downloads only; inference remains offline."""
import os
os.environ['PYANNOTE_METRICS_ENABLED']='0'
import sys
from pathlib import Path
root=Path(__file__).resolve().parent
if '--speakers' in sys.argv:
    from getpass import getpass
    from huggingface_hub import snapshot_download
    print('First accept the conditions at https://huggingface.co/pyannote/speaker-diarization-community-1')
    token=getpass('Hugging Face read token (hidden; not saved): ')
    target=root/'models/speakers'
    snapshot_download('pyannote/speaker-diarization-community-1',local_dir=str(target),token=token)
    from pyannote.audio import Pipeline
    Pipeline.from_pretrained(str(target))
    (target/'.ready').write_text('Community-1 loaded locally')
else:
    import whisperx
    target=root/'models/alignment';target.mkdir(exist_ok=True)
    whisperx.load_align_model(language_code='en',device='cpu',model_dir=str(target))
    (target/'.ready').write_text('English alignment model ready')
print('Setup complete.')
