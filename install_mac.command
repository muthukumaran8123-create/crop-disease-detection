#!/bin/bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11 is required. Install it from https://www.python.org/downloads/ and retry."
  read -r -p "Press Return to close..." _
  exit 1
fi
PY_MINOR=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
case "$PY_MINOR" in
  3.10|3.11|3.12) ;;
  *) echo "Detected Python $PY_MINOR. This project recommends Python 3.11 (supported range 3.10–3.12 for this TensorFlow pin)."; read -r -p "Press Return to close..." _; exit 1;;
esac
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
echo "\nInstall complete. Download/extract the PlantVillage dataset and train the model as described in README.md."
read -r -p "Press Return to close..." _
