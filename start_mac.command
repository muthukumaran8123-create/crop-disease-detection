#!/bin/bash
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "Run install_mac.command first, or follow the setup instructions in README.md."
  read -r -p "Press Return to close..." _
  exit 1
fi
.venv/bin/python app.py
