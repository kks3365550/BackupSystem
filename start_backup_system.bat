@echo off
setlocal
cd /d "%~dp0"

set "PY_EXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PY_EXE=%~dp0.venv\Scripts\python.exe"
if "%PY_EXE%"=="" if exist "%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe" set "PY_EXE=%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe"
if "%PY_EXE%"=="" set "PY_EXE=python"

powershell -ExecutionPolicy Bypass -Command "if (-not (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)) { Start-Process -FilePath '%PY_EXE%' -ArgumentList 'run.py' -WorkingDirectory '%~dp0' -WindowStyle Hidden } else { Start-Process 'http://127.0.0.1:8765' }"

exit /b 0
