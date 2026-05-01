@echo off
REM pdf_translate.bat — Activate venv and run PDF translator.
REM Usage: pdf_translate.bat input.pdf [output_ru.pdf]

set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%.venv\Scripts\activate.bat"
python "%SCRIPT_DIR%pdf_translate.py" %*
