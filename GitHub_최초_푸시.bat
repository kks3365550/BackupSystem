@echo off
chcp 65001 >nul
title BackupSystem GitHub Public Release Push
cls
echo ============================================================
echo   백업시스템 v2.9.20 클린 공개 저장소 GitHub 최초 푸시
echo   대상: https://github.com/kks3365550/BackupSystem.git
echo ============================================================
echo.

cd /d "%TEMP%\BackupSystem_Public_Release"
if not exist ".git" (
    echo [ERROR] 클린 저장소가 준비되지 않았습니다.
    pause
    exit /b 1
)

echo [*] GitHub로 소스코드(main) 및 태그(v2.9.20) 푸시를 시작합니다...
echo [*] 브라우저 인증(GitHub 로그인) 창이 뜨면 로그인을 승인해 주세요.
echo.

git push -u origin main --tags

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================================
    echo [SUCCESS] GitHub 푸시가 완벽하게 성공했습니다!
    echo 저장소 주소: https://github.com/kks3365550/BackupSystem
    echo ============================================================
) else (
    echo.
    echo [ERROR] 푸시 중 오류가 발생했습니다. 위 메시지를 확인해 주세요.
)

echo.
pause
exit /b %ERRORLEVEL%
