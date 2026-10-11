"""Explicit one-time installation of the isolated, offline YAMNet worker."""
import hashlib
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent

if __name__=='__main__':
    from sound_analysis import WEIGHTS_SHA
    python=ROOT/'.venv-audio/bin/python'
    if not python.exists():subprocess.run([sys.executable,'-m','venv',str(python.parent.parent)],check=True)
    subprocess.run([str(python),'-m','pip','install','-r',str(ROOT/'requirements-sound.lock.txt')],check=True)
    folder=ROOT/'models/sound-yamnet';folder.mkdir(parents=True,exist_ok=True)
    weights=folder/'yamnet.h5'
    if not weights.exists() or hashlib.file_digest(weights.open('rb'),'sha256').hexdigest()!=WEIGHTS_SHA:
        data=urlopen('https://storage.googleapis.com/audioset/yamnet.h5',timeout=60).read()
        if hashlib.sha256(data).hexdigest()!=WEIGHTS_SHA:raise RuntimeError('The YAMNet download did not match its pinned checksum.')
        pending=weights.with_suffix('.pending');pending.write_bytes(data);pending.replace(weights)
    subprocess.run([str(python),str(ROOT/'sound_worker.py'),'--check'],check=True)
    from project_store import write
    write(folder/'.ready',dict(sha256=WEIGHTS_SHA,size=weights.stat().st_size,mtime_ns=weights.stat().st_mtime_ns))
    print('Sound analysis is ready. Processing runs offline.')
