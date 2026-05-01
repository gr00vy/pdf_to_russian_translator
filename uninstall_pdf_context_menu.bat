@echo off
REM uninstall_pdf_context_menu.bat — Removes "Translate PDF to Russian" right-click menu from Windows Explorer.

python "%~dp0install_pdf_context_menu.py" --uninstall
pause
