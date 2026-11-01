@echo off
rem Prefer workspace .venv (Python 3.13), then py -3.13, then plain python from PATH.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set "VENVPY=%~dp0..\.venv\Scripts\python.exe"
if exist "%VENVPY%" (
    "%VENVPY%" "%~dp0ask.py" %*
    exit /b %errorlevel%
)
py -3.13 --version >nul 2>&1
if not errorlevel 1 (
    py -3.13 "%~dp0ask.py" %*
    exit /b %errorlevel%
)
python "%~dp0ask.py" %*
