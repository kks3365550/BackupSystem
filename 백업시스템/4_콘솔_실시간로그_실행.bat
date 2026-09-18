@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title 백업시스템 - 콘솔 실시간 로그 모드

echo ============================================================
echo   백업 매니저 시스템 (실시간 콘솔 로그 모드)
echo ============================================================
echo [*] 백그라운드 숨김이 아닌 이 터미널 창에서 직접 서버 로그를 표시합니다.
echo [*] 서버를 중단하려면 이 창에서 Ctrl + C 를 누르거나 창을 닫으세요.
echo ============================================================
echo.

set "PY_EXE="
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_EXE=%LOCALAPPDATA%\Python\bin\python.exe"
)

if "!PY_EXE!"=="" (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PY_EXE=py -3"
)
if "!PY_EXE!"=="" (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY_EXE=python"
)

if "!PY_EXE!"=="" (
    echo [!] 오류: Python 실행기를 찾을 수 없습니다.
    pause
    exit /b 1
)

"!PY_EXE!" -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [*] 필수 패키지 [uvicorn 등] 를 자동으로 설치합니다...
    "!PY_EXE!" -m pip install -r "%~dp0requirements.txt" --quiet --no-warn-script-location
)

echo [*] 기존 백그라운드 서버가 있다면 먼저 정리합니다...
call "%~dp0stop_backup_system.bat" >nul 2>&1
timeout /t 1 /nobreak >nul

echo [*] 대시보드 서버를 직접 실행합니다: http://127.0.0.1:8765
"!PY_EXE!" run.py
pause
