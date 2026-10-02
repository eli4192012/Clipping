#!/bin/zsh
cd "${0:A:h}"
.venv/bin/python download_models.py
echo "Press any key to close."
read -k 1
