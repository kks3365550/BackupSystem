@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 백업시스템 매니저

set "PY="
if exist "%~dp0.venv\Scripts\python.exe" set "PY=%~dp0.venv\Scripts\python.exe"
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" set "PY=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
if exist "%LOCALAPPDATA%\Python\bin\python.exe" set "PY=%LOCALAPPDATA%\Python\bin\python.exe"
if "%PY%"=="" set "PY=python"

"%PY%" run.py

if errorlevel 1 (
    echo.
    echo [!] 오류가 발생했습니다. 키를 누르면 창이 닫힙니다.
    pause
)
