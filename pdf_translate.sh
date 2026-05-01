#!/usr/bin/env bash
# pdf_translate.sh — Activate venv and run PDF translator.
# Usage: ./pdf_translate.sh input.pdf [output_ru.pdf]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
python3 "$SCRIPT_DIR/pdf_translate.py" "$@"
