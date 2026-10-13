import os

net_script = r'''@echo off
chcp 65001 >nul
title [백업시스템] 사무실 윈도우7 공유폴더 및 네트워크 설정 백업

echo ======================================================================
echo   [사무실 PC] 공유 폴더 및 네트워크 설정 원클릭 백업
echo ======================================================================
echo  - 공유 폴더 설정(LanmanServer Shares 레지스트리)
echo  - 저장된 네트워크 자격 증명 대상 목록(cmdkey)
echo  - 네트워크 드라이브 연결 목록(net use)
echo  - IP 및 네트워크 어댑터 구성(ipconfig)
echo ======================================================================
echo.

set "CUR_USB=%~dp0"
set "TARGET_USB=%CUR_USB%사무실_네트워크설정_백업"
set "TARGET_D=D:\사무실_네트워크설정_백업"

if not exist "%TARGET_USB%" mkdir "%TARGET_USB%" >nul 2>&1
if exist D:\ if not exist "%TARGET_D%" mkdir "%TARGET_D%" >nul 2>&1

echo [*] [1/4] LanmanServer 공유 폴더 레지스트리 추출 중...
reg export "HKLM\SYSTEM\CurrentControlSet\Services\LanmanServer\Shares" "%TARGET_USB%\1_공유폴더설정_복원용.reg" /y >nul 2>&1
if exist D:\ copy /y "%TARGET_USB%\1_공유폴더설정_복원용.reg" "%TARGET_D%\" >nul 2>&1

echo [*] [2/4] 저장된 네트워크 자격 증명(Vault/cmdkey) 목록 추출 중...
cmdkey /list > "%TARGET_USB%\2_네트워크_자격증명목록.txt" 2>&1
if exist D:\ copy /y "%TARGET_USB%\2_네트워크_자격증명목록.txt" "%TARGET_D%\" >nul 2>&1

echo [*] [3/4] 연결된 네트워크 드라이브(net use) 목록 추출 중...
net use > "%TARGET_USB%\3_네트워크드라이브_매핑목록.txt" 2>&1
if exist D:\ copy /y "%TARGET_USB%\3_네트워크드라이브_매핑목록.txt" "%TARGET_D%\" >nul 2>&1

echo [*] [4/4] IP 및 네트워크 어댑터 상세 설정(ipconfig) 추출 중...
ipconfig /all > "%TARGET_USB%\4_네트워크IP_상세구성.txt" 2>&1
if exist D:\ copy /y "%TARGET_USB%\4_네트워크IP_상세구성.txt" "%TARGET_D%\" >nul 2>&1

echo [사무실 PC 윈도우 11 업그레이드 후 복원 가이드] > "%TARGET_USB%\복원방법_안내.txt"
echo 1. 1_공유폴더설정_복원용.reg: 더블클릭하여 적용하면 기존 공유폴더가 복원됩니다. >> "%TARGET_USB%\복원방법_안내.txt"
echo 2. 2_네트워크_자격증명목록.txt: 기존 연결 NAS/서버 IP 및 계정 목록입니다. >> "%TARGET_USB%\복원방법_안내.txt"
echo 3. 3_네트워크드라이브_매핑목록.txt: 기존 연결 네트워크 드라이브 목록입니다. >> "%TARGET_USB%\복원방법_안내.txt"
if exist D:\ copy /y "%TARGET_USB%\복원방법_안내.txt" "%TARGET_D%\" >nul 2>&1

echo.
echo ======================================================================
echo   사무실 PC 네트워크 및 공유 설정 백업이 완료되었습니다!
echo   저장 위치: %TARGET_USB%
echo ======================================================================
echo.
pause
exit /b 0
'''

tec_script = r'''@echo off
chcp 65001 >nul
title [백업시스템] Tecnosoft SPD 프로그램 및 데이터베이스 전수 추출 백업

echo ======================================================================
echo   [사무실 PC] Tecnosoft SPD 데이터 로거 프로그램 및 DB 전수 백업
echo ======================================================================
echo  - 과거 살균/열분포 F0 측정 데이터베이스(.spd, .sdb 등)
echo  - 장비 캘리브레이션 프로필 및 프로그램 설정
echo  - Tecnosoft 관련 레지스트리 라이선스 키
echo ======================================================================
echo.

set "CUR_USB=%~dp0"
set "TARGET_USB=%CUR_USB%사무실_Tecnosoft_백업"
set "TARGET_D=D:\사무실_Tecnosoft_백업"

if not exist "%TARGET_USB%" mkdir "%TARGET_USB%" >nul 2>&1
if exist D:\ if not exist "%TARGET_D%" mkdir "%TARGET_D%" >nul 2>&1

echo [*] [1/3] Tecnosoft 레지스트리 설정 추출 중...
reg export "HKLM\SOFTWARE\Tecnosoft" "%TARGET_USB%\Tecnosoft_HKLM.reg" /y >nul 2>&1
reg export "HKLM\SOFTWARE\Wow6432Node\Tecnosoft" "%TARGET_USB%\Tecnosoft_HKLM_x64.reg" /y >nul 2>&1
reg export "HKCU\SOFTWARE\Tecnosoft" "%TARGET_USB%\Tecnosoft_HKCU.reg" /y >nul 2>&1

echo [*] [2/3] Program Files 설치 폴더 복사 중...
if exist "C:\Program Files (x86)\Tecnosoft" xcopy "C:\Program Files (x86)\Tecnosoft" "%TARGET_USB%\ProgramFiles_x86\" /E /I /H /Y /Q >nul 2>&1
if exist "C:\Program Files\Tecnosoft" xcopy "C:\Program Files\Tecnosoft" "%TARGET_USB%\ProgramFiles\" /E /I /H /Y /Q >nul 2>&1
if exist "C:\Tecnosoft" xcopy "C:\Tecnosoft" "%TARGET_USB%\Tecnosoft_Root\" /E /I /H /Y /Q >nul 2>&1

echo [*] [3/3] ProgramData 및 사용자 계정 데이터베이스 탐색 및 복사 중...
if exist "C:\ProgramData\Tecnosoft" xcopy "C:\ProgramData\Tecnosoft" "%TARGET_USB%\ProgramData\" /E /I /H /Y /Q >nul 2>&1
if exist "%USERPROFILE%\AppData\Local\Tecnosoft" xcopy "%USERPROFILE%\AppData\Local\Tecnosoft" "%TARGET_USB%\AppData_Local\" /E /I /H /Y /Q >nul 2>&1
if exist "%USERPROFILE%\Documents\Tecnosoft" xcopy "%USERPROFILE%\Documents\Tecnosoft" "%TARGET_USB%\Documents\" /E /I /H /Y /Q >nul 2>&1

if exist D:\ xcopy "%TARGET_USB%" "%TARGET_D%\" /E /I /H /Y /Q >nul 2>&1

echo.
echo ======================================================================
echo   Tecnosoft SPD 데이터 및 라이선스 정보 추출이 완료되었습니다!
echo   저장 위치: %TARGET_USB%
echo ======================================================================
echo.
pause
exit /b 0
'''

vhd_script = r'''@echo off
chcp 65001 >nul
title [백업시스템] 윈도우7 C드라이브 전체 무손실 가상화 백업 (Disk2vhd)

echo ======================================================================
echo   [사무실 PC] C드라이브 전체 무손실 가상화 백업 (Disk2vhd)
echo ======================================================================
echo  - C드라이브(Windows 7, MS Office, 한글, Tecnosoft SPD 등) 전체를
echo    가상 머신용 하드디스크(.vhdx) 단 1개 파일로 완벽 압축 복제합니다.
echo ======================================================================
echo.

set "TOOL_EXE=%~dp0Rescue_Tools\Disk2vhd\disk2vhd64.exe"
if not exist "%TOOL_EXE%" set "TOOL_EXE=%~dp0Rescue_Tools\Disk2vhd\disk2vhd.exe"

if not exist "%TOOL_EXE%" (
    echo [!] 오류: Disk2vhd 실행 파일을 찾을 수 없습니다: %TOOL_EXE%
    pause
    exit /b 1
)

echo [*] Microsoft Disk2vhd 가상화 도구를 실행합니다.
echo.
echo [사용 방법]
echo  1. 프로그램 창이 뜨면 상단의 'Use Vhdx' 에 체크합니다.
echo  2. 하단 볼륨 목록에서 [C:\] 만 체크합니다. (D드라이브 체크 해제)
echo  3. 저장 위치(VHD File name)를 D드라이브로 지정합니다:
echo     예: D:\사무실_Win7_가상백업.vhdx
echo  4. [Create] 버튼을 누르면 작업이 완료됩니다.
echo.
start "" "%TOOL_EXE%"
exit /b 0
'''

def write_crlf(path, content):
    crlf_content = content.strip().replace('\r\n', '\n').replace('\n', '\r\n') + '\r\n'
    with open(path, 'wb') as f:
        f.write(crlf_content.encode('utf-8'))
    print(f'Successfully wrote: {path}')

write_crlf(r'E:\0_사무실_공유폴더_및_네트워크_원클릭백업.bat', net_script)
write_crlf(r'E:\0_사무실_Tecnosoft_SPD_원클릭추출.bat', tec_script)
write_crlf(r'E:\0_사무실_C드라이브_가상화백업(Disk2vhd).bat', vhd_script)
