#!/bin/zsh
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  echo "Missing Python environment. See README.md for setup instructions."
  read -k 1
  exit 1
fi
exec .venv/bin/python launch.py
