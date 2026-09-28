chcp 65001 >$null
$ErrorActionPreference = "SilentlyContinue"

Write-Output "=== 1. Backup Processes on Port 8765 ==="
$conn = Get-NetTCPConnection -LocalPort 8765
if ($conn) {
    foreach ($c in $conn) {
        $p = Get-Process -Id $c.OwningProcess
        $w = Get-CimInstance Win32_Process -Filter "ProcessId = $($c.OwningProcess)"
        Write-Output "PID: $($p.Id), Name: $($p.ProcessName)"
        Write-Output "Path: $($p.Path)"
        Write-Output "CommandLine: $($w.CommandLine)"
    }
} else {
    Write-Output "No process listening on port 8765"
}

Write-Output "`n=== 2. BackupSystem Directories ==="
$candidates = @(
    "C:\Program Files\백업시스템",
    "F:\백업시스템_설치용",
    "D:\백업시스템_설치용",
    "C:\Users\kksjmj\Desktop\ai\백업시스템"
)
foreach ($dir in $candidates) {
    if (Test-Path $dir) {
        $ver = if (Test-Path "$dir\VERSION") { Get-Content "$dir\VERSION" -Raw } else { "No VERSION" }
        Write-Output "Found: $dir (VERSION: $($ver.Trim()))"
    }
}

Write-Output "`n=== 3. Recent Logs ==="
$logCandidates = @(
    "C:\Program Files\백업시스템\*.log",
    "F:\백업시스템_설치용\*.log",
    "D:\백업시스템_설치용\*.log",
    "$env:TEMP\backup_update*.log",
    "$env:TEMP\run_updater*.bat"
)
foreach ($pat in $logCandidates) {
    $files = Get-ChildItem -Path $pat -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        Write-Output "Log file: $($f.FullName) (Size: $($f.Length), Modified: $($f.LastWriteTime))"
        Get-Content $f.FullName -Tail 20 | ForEach-Object { Write-Output "  $_" }
    }
}
