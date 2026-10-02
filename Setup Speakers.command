#!/bin/zsh
cd "${0:A:h}"
.venv-speech/bin/python setup_speech.py --speakers
echo "Press any key to close."
read -k 1
