#!/bin/zsh
cd "${0:A:h}"
.venv/bin/python -m venv .venv-speech
.venv-speech/bin/pip install -r requirements-speech.txt && .venv-speech/bin/python setup_speech.py
echo "Press any key to close."
read -k 1
