@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PY_EXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PY_EXE=%~dp0.venv\Scripts\python.exe"
if "!PY_EXE!"=="" (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY_EXE=python"
)
if "!PY_EXE!"=="" (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PY_EXE=py -3"
)

if "!PY_EXE!"=="" (
    echo [오류] 파이썬을 찾을 수 없습니다. 1_원클릭_환경설치(최초1회).bat 을 먼저 실행해주세요.
    pause
    exit /b 1
)

!PY_EXE! create_desktop_shortcut.py
echo.
pause
