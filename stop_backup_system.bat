@echo off
chcp 65001 >nul
setlocal EnableExtensions

:: 설치 디렉터리 경로 정규화 (끝의 백슬래시 제거)
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

:: 1. 8765 포트를 점유하고 있는 PID가 있다면, 해당 PID가 APP_DIR 프로세스인지 확인 후 안전 종료
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr :8765 ^| findstr LISTENING') do (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
      "$targetDir = $env:APP_DIR; if ($targetDir -and $targetDir.Length -ge 3) { $p = Get-CimInstance Win32_Process -Filter \"ProcessId = %%a\" -ErrorAction SilentlyContinue; if ($p -and (($p.CommandLine -and $p.CommandLine.IndexOf($targetDir, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) -or ($p.ExecutablePath -and $p.ExecutablePath.IndexOf($targetDir, [System.StringComparison]::OrdinalIgnoreCase) -ge 0))) { Stop-Process -Id %%a -Force -ErrorAction SilentlyContinue } }" >nul 2>&1
)

:: 2. APP_DIR을 실행 경로 또는 명령줄 인자로 포함하고 있는 백업시스템 전용 프로세스 선별 종료 (타 Python/wscript 100%% 보호)
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$targetDir = $env:APP_DIR; if ($targetDir -and $targetDir.Length -ge 3) { Get-CimInstance Win32_Process | Where-Object { $name = $_.Name; $cmd = $_.CommandLine; $path = $_.ExecutablePath; if (-not $cmd) { return $false }; if ($name -notmatch '^(python|pythonw|wscript)\.exe$') { return $false }; $isBackupScript = ($cmd -match '(run\.py|tray_app\.py|cli_backup\.py|start_tray\.vbs|start_silent\.vbs|launch_dashboard\.vbs)'); $isUnderTargetDir = ($cmd.IndexOf($targetDir, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) -or ($path -and ($path.IndexOf($targetDir, [System.StringComparison]::OrdinalIgnoreCase) -ge 0)); return ($isBackupScript -and $isUnderTargetDir) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }" >nul 2>&1

:: 3. Windows 작업 스케줄러 태스크 중지 (존재할 경우)
schtasks.exe /End /TN "BackupSystem_AutoBackup" >nul 2>&1
schtasks.exe /End /TN "BackupSystem_WebServer" >nul 2>&1
schtasks.exe /End /TN "BackupSystem_Server_Daemon" >nul 2>&1

:: 4. 프로세스 핸들 완전 해제 대기 (1.5초)
ping 127.0.0.1 -n 2 >nul

exit /b 0
