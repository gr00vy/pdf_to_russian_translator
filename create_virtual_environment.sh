#!/usr/bin/env bash
# create_virtual_environment.sh — Creates .venv and installs dependencies.
python3 -m venv .venv && source .venv/bin/activate && pip install PyMuPDF googletrans==4.0.0rc1
