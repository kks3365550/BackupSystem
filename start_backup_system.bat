@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"
title 백업시스템 매니저 v2.1

echo ============================================================
echo   백업 매니저 시스템 (Backup System Manager)
echo ============================================================
echo [*] 구동 환경 및 Python 경로를 점검하고 있습니다...

set "PY_EXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PY_EXE=%~dp0.venv\Scripts\python.exe"
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" set "PY_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if exist "%LOCALAPPDATA%\Python\bin\python.exe" set "PY_EXE=%LOCALAPPDATA%\Python\bin\python.exe"

if "!PY_EXE!"=="" (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PY_EXE=py -3"
)
if "!PY_EXE!"=="" (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY_EXE=python"
)

if "!PY_EXE!"=="" (
    echo [!] 오류: 시스템에 Python이 설치되어 있지 않습니다.
    echo [*] 1_원클릭_환경설치(최초1회).bat 를 먼저 실행해 주세요.
    pause
    exit /b 1
)

:CHECK_SERVER
set "IS_RUNNING=0"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING 2^>nul') do (
    set "IS_RUNNING=1"
    set "SERVER_PID=%%p"
)

if "!IS_RUNNING!"=="0" (
    echo [*] 백업 서버 서비스를 백그라운드에서 구동합니다...
    if exist "%~dp0start_silent.vbs" (
        wscript.exe "%~dp0start_silent.vbs"
    ) else (
        start /b "" "!PY_EXE!" run.py
    )
    
    echo [*] 서버 응답을 대기 중입니다...
    set "READY=0"
    for /l %%i in (1,1,10) do (
        if "!READY!"=="0" (
            timeout /t 1 /nobreak >nul
            for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING 2^>nul') do (
                set "READY=1"
                set "SERVER_PID=%%a"
            )
        )
    )
)

cls
echo ============================================================
echo   백업 매니저 시스템 (Backup System Manager)
echo ============================================================
echo  [ 서버 상태 ] 정상 동작 중 (PID: !SERVER_PID!, Port: 8765)
echo  [ 접속 주소 ] http://127.0.0.1:8765
echo                http://localhost:8765
echo ============================================================
echo.
echo [*] 기본 웹 브라우저에서 대시보드를 엽니다...
start "" "http://127.0.0.1:8765"

echo.
echo  ----------------------------------------------------------
echo  만약 브라우저에서 '연결 거부' 또는 로딩 실패가 뜰 경우:
echo    [E] Microsoft Edge로 즉시 열기
echo    [R] 백업 서비스 완전 재시작
echo    [C] 실시간 콘솔 로그 모드로 전환 실행
echo    [Q] 창 닫기 (백업 서버는 백그라운드에서 계속 유지됩니다)
echo  ----------------------------------------------------------
echo.

set /p "USER_CHOICE=선택 (엔터 또는 Q 입력 시 창 닫기): "

if /i "!USER_CHOICE!"=="E" (
    echo [*] Microsoft Edge로 대시보드를 엽니다...
    start msedge "http://127.0.0.1:8765"
    timeout /t 2 /nobreak >nul
    exit /b 0
)

if /i "!USER_CHOICE!"=="R" (
    echo [*] 기존 백업 서버를 종료하고 재시작합니다...
    call "%~dp0stop_backup_system.bat"
    timeout /t 1 /nobreak >nul
    goto CHECK_SERVER
)

if /i "!USER_CHOICE!"=="C" (
    echo [*] 실시간 콘솔 로그 모드를 새 창으로 구동합니다...
    start cmd /k "chcp 65001 >nul && cd /d %~dp0 && "!PY_EXE!" run.py"
    exit /b 0
)

exit /b 0
