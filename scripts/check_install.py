"""Catch missing direct pins and native import failures without downloading models."""
import importlib
import importlib.metadata
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]
CORE_IMPORTS = ('streamlit', 'av', 'imageio_ffmpeg', 'faster_whisper', 'mlx_lm',
                'mlx_vlm', 'mlx_whisper', 'scenedetect', 'keyring', 'yt_dlp', 'requests')


def validate_pins(requirements, lock):
    def entries(path):
        return [Requirement(line) for line in Path(path).read_text().splitlines()
                if line.strip() and not line.startswith('#')]
    pins = {canonicalize_name(item.name): item for item in entries(lock)}
    for required in entries(requirements):
        if required.marker and not required.marker.evaluate():
            continue
        pin = pins.get(canonicalize_name(required.name))
        if pin is None:
            raise ValueError(f'Missing direct dependency in lock: {required.name}')
        versions = list(pin.specifier)
        if len(versions) != 1 or versions[0].operator != '==' or '*' in versions[0].version:
            raise ValueError(f'Dependency is not exactly pinned: {required.name}')
        version = versions[0].version
        if version not in required.specifier:
            raise ValueError(f'Pin is outside the direct constraint: {required.name}')
        if importlib.metadata.version(required.name) != version:
            raise ValueError(f'Installed version differs from lock: {required.name}')


def main():
    validate_pins(ROOT / 'requirements.txt', ROOT / 'requirements.lock.txt')
    for name in CORE_IMPORTS:
        importlib.import_module(name)
        print(f'Imported {name}', flush=True)
    print('Pinned dependency and core import checks passed.', flush=True)


if __name__ == '__main__':
    main()
