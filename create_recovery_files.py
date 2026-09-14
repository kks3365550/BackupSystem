import os

repo_dir = r"D:\MyBackup_Repository"
proj_dir = r"c:\Users\kksjmj\Desktop\ai\백업시스템"

bat_auto = """@echo off
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

set "PY_EXE="
if exist "%EMERGENCY_DIR%\\python\\python.exe" (
    set "PY_EXE=%EMERGENCY_DIR%\\python\\python.exe"
) else if exist "%REPO_DIR%.venv\\Scripts\\python.exe" (
    set "PY_EXE=%REPO_DIR%.venv\\Scripts\\python.exe"
) else (
    where python >nul 2>&1
    if '%errorlevel%' EQU '0' (
        set "PY_EXE=python"
    ) else (
        echo [오류] 파이썬 실행기를 찾을 수 없습니다.
        pause
        exit /b 1
    )
)

set "PY_SCRIPT=%EMERGENCY_DIR%\\emergency_restore.py"
if not exist "%PY_SCRIPT%" (
    if exist "%REPO_DIR%emergency_restore.py" (
        set "PY_SCRIPT=%REPO_DIR%emergency_restore.py"
    )
)

echo ======================================================================
echo   🛡️  원클릭 C드라이브 전체 자동 복구
echo ======================================================================
echo  - 백업 저장소의 가장 최신 스냅샷을 원본 C드라이브 경로로 복원합니다.
echo  - 프로그램, 소스코드, 드라이버, 레지스트리, 바탕화면 파일이 복구됩니다.
echo ======================================================================
echo.

"%PY_EXE%" "%PY_SCRIPT%" --auto

echo.
echo 복구 작업이 종료되었습니다.
pause
"""

bat_interactive = """@echo off
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

set "PY_EXE="
if exist "%EMERGENCY_DIR%\\python\\python.exe" (
    set "PY_EXE=%EMERGENCY_DIR%\\python\\python.exe"
) else if exist "%REPO_DIR%.venv\\Scripts\\python.exe" (
    set "PY_EXE=%REPO_DIR%.venv\\Scripts\\python.exe"
) else (
    where python >nul 2>&1
    if '%errorlevel%' EQU '0' (
        set "PY_EXE=python"
    ) else (
        echo [오류] 파이썬 실행기를 찾을 수 없습니다.
        pause
        exit /b 1
    )
)

set "PY_SCRIPT=%EMERGENCY_DIR%\\emergency_restore.py"
if not exist "%PY_SCRIPT%" (
    if exist "%REPO_DIR%emergency_restore.py" (
        set "PY_SCRIPT=%REPO_DIR%emergency_restore.py"
    )
)

"%PY_EXE%" "%PY_SCRIPT%"

echo.
echo 복구 작업이 종료되었습니다.
pause
"""

readme_text = """======================================================================
  🛡️ D드라이브 비상 재해 복구(Disaster Recovery) 가이드
======================================================================

C드라이브 포맷 및 윈도우 재설치 시 다음과 같이 복구하시면 됩니다:

■ 상황:
  - C드라이브가 포맷되어 Python, 백업시스템 프로그램 등이 없는 상태
  - D드라이브의 백업 저장소(D:\\MyBackup_Repository)는 온전히 보존된 상태

■ 복구 방법 (파이썬 사전 설치 불필요!):
  1. 윈도우 탐색기에서 'D:\\MyBackup_Repository' 폴더를 엽니다.
  2. 다음 배치 파일 중 원하는 것을 더블 클릭하여 실행합니다:

     [방법 1] '원클릭_C드라이브_전체복구.bat'
       - 가장 최신 백업 시점의 모든 파일(바탕화면, 소스코드, 프로그램, 드라이버 등)을
         C드라이브의 원래 위치로 즉시 자동 복구합니다.

     [방법 2] '선택복구_대화형.bat'
       - 원하는 백업 시점(스냅샷)을 직접 번호로 고르거나,
       - 특정 폴더/특정 파일만 골라서 복구하고 싶을 때 사용합니다.
       - 원하는 복원 대상 폴더(예: C:\\Restored)를 지정할 수도 있습니다.

■ 기술적 원리:
  - 본 저장소의 'emergency_restore\\python' 폴더 내에 완전한 독립형 무설치 런타임이
    함께 내장되어 있어, C드라이브 포맷 직후 순정 윈도우 상태에서도 외부 인터넷/패키지
    다운로드 없이 100% 오프라인 복구가 가능합니다.
======================================================================
"""

for target_dir in [repo_dir, proj_dir]:
    if os.path.exists(target_dir):
        with open(os.path.join(target_dir, "원클릭_C드라이브_전체복구.bat"), "w", encoding="utf-8") as f:
            f.write(bat_auto)
        with open(os.path.join(target_dir, "선택복구_대화형.bat"), "w", encoding="utf-8") as f:
            f.write(bat_interactive)
        with open(os.path.join(target_dir, "README_재해복구_가이드.txt"), "w", encoding="utf-8") as f:
            f.write(readme_text)

print("Emergency restore bat files and guides generated successfully!")
