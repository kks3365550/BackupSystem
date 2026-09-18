@echo off
chcp 65001 >nul
title 윈도우 베어메탈 시스템 이미지 백업 [OS + 오피스 뼈대 백업]

:: 관리자 권한 확인 및 자동 승격
openfiles >nul 2>&1
if '%errorlevel%' NEQ '0' (
    echo [안내] 윈도우 시스템 이미지 캡처를 위해 관리자 권한으로 승격합니다...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

echo ======================================================================
echo   💻 윈도우 베어메탈 시스템 이미지 백업 [2-Track 하이브리드]
echo ======================================================================
echo  - Windows OS, 부팅 [EFI] 파티션, C드라이브, MS Office, 필수 프로그램 전체를
echo    VHDX 기반 시스템 이미지 [D:\WindowsImageBackup] 로 캡처합니다.
echo  - 재해 발생 시 오피스 재설치나 윈도우 재인증 없이 5분 만에 복원 가능합니다.
echo  - 이 작업은 최초 1회 또는 대규모 프로그램 설치 시에만 수행하시면 됩니다.
echo ======================================================================
echo.

set "TARGET_DRIVE=D:"
echo [*] 백업 대상 저장소 드라이브: %TARGET_DRIVE%
echo [*] 백업을 시작합니다. 약 5~15분 정도 소요될 수 있습니다...
echo.

wbadmin start backup -backupTarget:%TARGET_DRIVE% -include:C: -allCritical -quiet

if '%errorlevel%' EQU '0' (
    echo.
    echo ======================================================================
    echo   🎉 베어메탈 시스템 이미지 백업이 성공적으로 완료되었습니다!
    echo   저장 위치: %TARGET_DRIVE%\WindowsImageBackup
    echo ======================================================================
) else (
    echo.
    echo [!] 백업 도중 오류 또는 경고가 발생했습니다. 종료 코드: %errorlevel%
)

echo.
pause
