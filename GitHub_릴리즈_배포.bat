@echo off
chcp 65001 >nul
title BackupSystem GitHub Release Deployer
cls
echo ============================================================
echo   백업시스템 v2.9.20 GitHub 공식 릴리즈 자동 배포
echo   대상: https://github.com/kks3365550/BackupSystem
echo ============================================================
echo.

set "GH_EXE=C:\Program Files\GitHub CLI\gh.exe"
if not exist "%GH_EXE%" (
    echo [ERROR] GitHub CLI(gh.exe)를 찾을 수 없습니다.
    pause
    exit /b 1
)

"%GH_EXE%" auth status >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] GitHub CLI 인증이 필요합니다.
    echo [*] 잠시 후 브라우저가 열리면 일회성 승인을 완료해 주세요...
    echo.
    "%GH_EXE%" auth login -h github.com -p https -w
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] GitHub 인증에 실패했습니다.
        pause
        exit /b 1
    )
)

echo.
echo [*] GitHub v2.9.20 릴리즈 생성 및 바이너리 Asset 4종 업로드 중...
echo.

"%GH_EXE%" release create v2.9.20 ^
  --repo kks3365550/BackupSystem ^
  --title "BackupSystem v2.9.20 Official Release" ^
  --notes-file "D:\백업시스템_설치용\github_release_body.md" ^
  "D:\백업시스템_설치용\BackupSystem_Setup_v2.9.20.exe" ^
  "D:\백업시스템_설치용\release_v2.9.20.zip" ^
  "D:\백업시스템_설치용\release_v2.9.20.zip.sig" ^
  "D:\백업시스템_설치용\SHA256SUMS.txt"

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo [SUCCESS] 백업시스템 v2.9.20 공식 릴리즈가 성공적으로 발행되었습니다!
    echo ============================================================
    start "" "https://github.com/kks3365550/BackupSystem/releases"
) else (
    echo.
    echo [ERROR] 릴리즈 배포 중 오류가 발생했습니다. 위 메시지를 확인해 주세요.
)

echo.
pause
exit /b %ERRORLEVEL%
