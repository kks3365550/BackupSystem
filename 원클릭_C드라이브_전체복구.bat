@echo off
setlocal
title [긴급 비상 재해 복구] 원클릭 C드라이브 전체 자동 복구

:: 관리자 권한 확인 및 자동 승격
openfiles >nul 2>&1
if '%errorlevel%' NEQ '0' (
    echo [안내] C드라이브 시스템 및 사용자 폴더 복구를 위해 관리자 권한으로 승격합니다...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
set "PY_EXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PY_EXE=%~dp0.venv\Scripts\python.exe"
if exist "%~dp0emergency_restore\python\python.exe" set "PY_EXE=%~dp0emergency_restore\python\python.exe"
if "%PY_EXE%"=="" (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PY_EXE=python"
    ) else (
        echo [오류] 파이썬 환경을 찾을 수 없습니다. 파이썬이 설치되어 있는지 확인하세요.
        pause
        exit /b 1
    )
)

set "PY_SCRIPT=%~dp0emergency_restore.py"
if not exist "%PY_SCRIPT%" (
    if exist "%~dp0emergency_restore\emergency_restore.py" (
        set "PY_SCRIPT=%~dp0emergency_restore\emergency_restore.py"
    )
)

echo ======================================================================
echo   [*] 원클릭 C드라이브 전체 자동 복구
echo ======================================================================
echo  - 백업 저장소의 가장 최신 스냅샷을 원본 C드라이브 경로로 복원합니다.
echo  - 프로그램, 소스코드, 드라이버, 레지스트리, 바탕화면 파일이 복구됩니다.
echo ======================================================================
echo.

"%PY_EXE%" "%PY_SCRIPT%" --auto

echo.
echo 복구 작업이 종료되었습니다.
pause

