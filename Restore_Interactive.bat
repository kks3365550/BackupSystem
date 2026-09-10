@echo off
chcp 65001 > nul
title 긴급 비상 재해 복구 - 선택형 복구 매니저

:: 관리자 권한 확인 및 자동 승격
openfiles >nul 2>&1
if '%errorlevel%' NEQ '0' (
    echo [안내] C드라이브 폴더 복구를 위해 관리자 권한으로 승격합니다...
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

"%PY_EXE%" "%PY_SCRIPT%"

