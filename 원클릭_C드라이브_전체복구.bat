@echo off
chcp 65001 > nul
title 긴급 비상 재해 복구 - 원클릭 C드라이브 전체 복구

:: 관리자 권한 확인 및 자동 승격
openfiles >nul 2>&1
if '%errorlevel%' NEQ '0' (
    echo [안내] C드라이브 시스템 및 사용자 폴더 복구를 위해 관리자 권한으로 승격합니다...
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

echo ======================================================================
echo   🛡️  원클릭 C드라이브 전체 자동 복구
echo ======================================================================
echo  - 백업 저장소의 가장 최신 스냅샷을 원본 C드라이브 경로로 복원합니다.
echo  - 프로그램, 소스코드, 드라이버, 레지스트리, 바탕화면 파일이 복구됩니다.
echo ======================================================================
echo.

"%PY_EXE%" "%EMERGENCY_DIR%\emergency_restore.py" --auto

echo.
echo 복구 작업이 종료되었습니다.
pause
