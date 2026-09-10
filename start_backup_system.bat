@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   백업시스템 대시보드 (Backup System Dashboard)
echo ============================================================
echo [*] 서버 상태 및 구동 환경을 점검하고 있습니다...

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
    echo [!] 오류: 시스템에 Python이 설치되어 있지 않습니다.
    pause
    exit /b 1
)

netstat -ano | findstr 8765 | findstr LISTENING >nul 2>&1
if errorlevel 1 (
    echo [*] 백업 서버를 백그라운드에서 구동합니다...
    if exist "%~dp0start_silent.vbs" (
        wscript.exe "%~dp0start_silent.vbs"
    ) else (
        start /b "" "!PY_EXE!" run.py
    )
    ping 127.0.0.1 -n 3 >nul 2>&1
) else (
    echo [*] 백업 서버가 이미 백그라운드에서 정상 동작 중입니다.
)

echo [*] 기본 웹 브라우저에서 대시보드를 엽니다: http://127.0.0.1:8765
start http://127.0.0.1:8765

echo [V] 완료되었습니다. 이 창은 3초 후 자동으로 닫힙니다.
ping 127.0.0.1 -n 4 >nul 2>&1
exit /b 0

