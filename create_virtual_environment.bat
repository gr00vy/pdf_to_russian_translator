@echo off
REM create_virtual_environment.bat — Creates .venv and installs dependencies.
python -m venv .venv && call .venv\Scripts\activate.bat && pip install PyMuPDF googletrans==4.0.0rc1
