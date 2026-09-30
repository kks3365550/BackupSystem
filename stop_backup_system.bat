@echo off
cd /d "%~dp0"
echo Stopping Backup System background service...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Backup server stopped.
