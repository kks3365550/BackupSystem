@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   [백업 매니저] 원클릭 자동 설치 및 환경 설정
echo ============================================================
echo.

:: 1. 파이썬 감지
set "PY_CMD="

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
)

if "!PY_CMD!"=="" (
    python --version >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
    )
)

if "!PY_CMD!"=="" (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        if "!PY_CMD!"=="" set "PY_CMD=%%i"
    )
)

if "!PY_CMD!"=="" (
    echo [오류] 파이썬(Python 3.9 이상)이 시스템에 설치되어 있지 않습니다.
    echo 파이썬 공식 다운로드 페이지를 엽니다...
    start https://www.python.org/downloads/
    echo.
    echo [중요!] 파이썬 설치 파일 실행 시 첫 화면 하단의
    echo "Add python.exe to PATH" 를 반드시 체크하고 설치해주세요!
    echo 설치가 완료되면 이 창을 닫고 다시 실행해 주시면 됩니다.
    echo.
    pause
    exit /b 1
)

echo [1/3] 파이썬 감지 완료: !PY_CMD!
echo.

:: 2. 가상환경 (.venv) 확인 및 생성 시도
set "TARGET_PY="
if exist ".venv\Scripts\python.exe" (
    echo [2/3] 가상환경(.venv)이 이미 준비되어 있습니다.
    set "TARGET_PY=%~dp0.venv\Scripts\python.exe"
) else (
    echo [2/3] 독립 가상환경(.venv) 생성 시도 중...
    !PY_CMD! -m venv .venv >nul 2>&1
    if exist ".venv\Scripts\python.exe" (
        echo     가상환경(.venv) 생성 성공!
        set "TARGET_PY=%~dp0.venv\Scripts\python.exe"
    ) else (
        echo     [알림] 가상환경 생성을 건너뛰고 시스템 파이썬을 직접 사용합니다.
        set "TARGET_PY=!PY_CMD!"
    )
)
echo.

:: 3. 패키지 설치
echo [3/3] 필수 라이브러리 자동 설치 중...
!TARGET_PY! -m pip install -r requirements.txt --quiet --no-warn-script-location
echo.

:: 4. 바탕화면 바로가기 생성
echo [*] 바탕화면에 바로가기 아이콘 생성 중...
!TARGET_PY! create_desktop_shortcut.py
echo.

echo ============================================================
echo   모든 설치 및 환경 설정이 완료되었습니다!
echo.
echo   - 바탕화면 [백업시스템 대시보드] 를 더블클릭하거나,
echo   - 폴더 내 [2_백업시스템_실행.bat] 을 실행하시면 시작됩니다!
echo ============================================================
echo.
pause
exit /b 0
