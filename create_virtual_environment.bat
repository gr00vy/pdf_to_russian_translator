@echo off
setlocal enabledelayedexpansion
echo Checking Python version...

REM Get major and minor version directly
for /f "tokens=1,2 delims=." %%a in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do (
    set MAJOR=%%a
    set MINOR=%%b
)

echo Detected Python version: %MAJOR%.%MINOR%

REM Create virtual environment
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate the environment
call .venv\Scripts\activate.bat

echo Installing base dependencies...
pip install PyMuPDF googletrans==4.0.0rc1

REM Check if version is 3.13 or higher to apply the legacy-cgi fix
set INSTALL_CGI=0
if %MAJOR% GEQ 3 (
    if %MINOR% GEQ 13 (
        set INSTALL_CGI=1
    )
)

REM Use !VAR! because of setlocal enabledelayedexpansion
if !INSTALL_CGI!==1 (
    echo [!] Python 3.13+ detected. Installing legacy-cgi to fix 'ModuleNotFoundError: No module named cgi'
    pip install legacy-cgi
) else (
    echo [i] Python version is compatible with standard cgi module.
)

echo Upgrading httpx and googletrans...
pip install --upgrade httpx googletrans==4.0.0rc1

echo.
echo Setup complete!
pause
