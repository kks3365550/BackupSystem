@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   [백업 매니저] 다른 PC 원클릭 자동 설치 및 환경 설정
echo ============================================================
echo.

:: 1. Check Python
set "SYSTEM_PY="
for /f "delims=" %%i in ('where python 2^>nul') do (
    if not defined SYSTEM_PY set "SYSTEM_PY=%%i"
)

if not defined SYSTEM_PY (
    echo [ERROR] 파이썬(Python 3.9 이상)이 설치되어 있지 않습니다.
    echo https://www.python.org/downloads/ 에서 Python을 먼저 설치해 주세요.
    echo (설치 시 'Add python.exe to PATH' 체크 필수)
    echo.
    pause
    exit /b 1
)

echo [1/3] 파이썬 감지 완료: %SYSTEM_PY%

:: 2. Create Virtual Environment (.venv)
if not exist ".venv\Scripts\python.exe" (
    echo [2/3] 독립 가상환경(.venv) 생성 중...
    "%SYSTEM_PY%" -m venv .venv
    if errorlevel 1 (
        echo [ERROR] 가상환경 생성 실패
        pause
        exit /b 1
    )
) else (
    echo [2/3] 가상환경(.venv)이 이미 준비되어 있습니다.
)

:: 3. Install Requirements
echo [3/3] 필수 패키지 자동 설치 중 (FastAPI, Uvicorn, Psutil)...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\pip.exe" install -r requirements.txt --quiet
if errorlevel 1 (
    echo [WARNING] 일부 패키지 설치 중 경고가 발생했으나 계속 진행합니다.
)

echo.
echo ============================================================
echo   설치 및 환경 설정이 100%% 완료되었습니다!
echo   이제 start_backup_system.bat 을 실행하시면 바로 시작됩니다.
echo ============================================================
echo.
pause
exit /b 0
