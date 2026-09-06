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
set "REPO_DIR=%~dp0"
set "EMERGENCY_DIR=%REPO_DIR%emergency_restore"
set "PY_EXE=%EMERGENCY_DIR%\python\python.exe"

if not exist "%PY_EXE%" (
    where python >nul 2>&1
    if '%errorlevel%' EQU '0' (
        set "PY_EXE=python"
    ) else (
        echo [오류] 독립 파이썬 환경을 찾을 수 없습니다: %PY_EXE%
        pause
        exit /b 1
    )
)

"%PY_EXE%" "%EMERGENCY_DIR%\emergency_restore.py"

