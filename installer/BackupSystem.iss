; =========================================================================
; Kova (Local Backup & Disaster Recovery) Inno Setup 6+ 인스톨러 빌드 스크립트
; =========================================================================

#define MyAppName "Kova"
#define MyAppVersion "2.14.10"
#define MyAppPublisher "kks3365550"
#define MyAppURL "http://127.0.0.1:8765"
#define MyAppExeName "Kova.exe"

[Setup]
AppId={{E8A42F38-9B7C-4C2E-8E1A-98C32B7D501F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename=Kova_Setup_v{#MyAppVersion}
OutputDir=..\dist
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\docs\EULA.txt
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
RestartApplications=no

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Windows 부팅 시 백그라운드 자동 시작"; GroupDescription: "시작 옵션:"

[Dirs]
; v2.10.4: 일반 사용자 권한 런타임 쓰기 보장 (바이너리는 관리자 읽기전용 유지)
Name: "{app}\data"; Permissions: users-modify
Name: "{app}\logs"; Permissions: users-modify

[Files]
; 1. Embedded Python 3.11 Runtime (Self-Contained)
Source: "runtime\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; 2. Application Core Source Tree (v2.9.21 Production Source)
Source: "..\core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,*.pyo"
Source: "..\web\*"; DestDir: "{app}\web"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,*.pyo"
Source: "..\run.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\VERSION"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\keys\*.pub"; DestDir: "{app}\keys"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; 3. VBScript 래퍼 및 운영 스크립트
Source: "start_silent.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "start_tray.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "launch_dashboard.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\tray_app.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\stop_backup_system.bat"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName} 웹 대시보드"; Filename: "wscript.exe"; Parameters: """{app}\launch_dashboard.vbs"""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 14
Name: "{group}\{#MyAppName} 트레이 에이전트 실행"; Filename: "wscript.exe"; Parameters: """{app}\start_tray.vbs"""; WorkingDir: "{app}"
Name: "{group}\{#MyAppName} 서비스 종료"; Filename: "{app}\stop_backup_system.bat"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} 대시보드"; Filename: "wscript.exe"; Parameters: """{app}\launch_dashboard.vbs"""; WorkingDir: "{app}"; IconFilename: "{sys}\shell32.dll"; IconIndex: 14; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BackupSystemService"; ValueData: "wscript.exe ""{app}\start_silent.vbs"""; Flags: uninsdeletevalue; Tasks: startupicon
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BackupSystemTray"; ValueData: "wscript.exe ""{app}\start_tray.vbs"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; DEF-02: 기존 구버전 작업 스케줄러 자동 정리 (중복 자동실행 방지)
Filename: "schtasks.exe"; Parameters: "/delete /tn ""BackupSystem_WebServer"" /f"; Flags: runhidden
Filename: "schtasks.exe"; Parameters: "/delete /tn ""BackupSystem_Server_Daemon"" /f"; Flags: runhidden
Filename: "netsh.exe"; Parameters: "advfirewall firewall add rule name=""BackupSystem"" dir=in action=allow protocol=TCP localport=8765"; Flags: runhidden; Check: IsAdminInstallMode
; v2.10.4: 기존 data/logs 내부 파일의 ACL 상속 갭 방지 (재귀적 users-modify 부여)
Filename: "icacls.exe"; Parameters: """{app}\data"" /grant Users:(OI)(CI)M /T /C /Q"; Flags: runhidden; Check: IsAdminInstallMode
Filename: "icacls.exe"; Parameters: """{app}\logs"" /grant Users:(OI)(CI)M /T /C /Q"; Flags: runhidden; Check: IsAdminInstallMode

[UninstallRun]
Filename: "{app}\stop_backup_system.bat"; Flags: runhidden waituntilterminated
Filename: "schtasks.exe"; Parameters: "/delete /tn ""BackupSystem_AutoBackup"" /f"; Flags: runhidden
Filename: "schtasks.exe"; Parameters: "/delete /tn ""BackupSystem_WebServer"" /f"; Flags: runhidden
Filename: "schtasks.exe"; Parameters: "/delete /tn ""BackupSystem_Server_Daemon"" /f"; Flags: runhidden
Filename: "netsh.exe"; Parameters: "advfirewall firewall delete rule name=""BackupSystem"""; Flags: runhidden; Check: IsAdminInstallMode

[Code]
// v2.14.1+: 설치 시작 시 기존 실행 중인 백업시스템 프로세스(트레이, 서버, 포트 8765) 선제 강제 종료 및 파일 잠금 해제 대기 루프
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  AppDir, StopBat, KillPsCmd: String;
begin
  Result := True;

  // 1. 기존 설치 경로별 stop_backup_system.bat 실행
  AppDir := ExpandConstant('{localappdata}\Programs\백업시스템');
  StopBat := AppDir + '\stop_backup_system.bat';
  if FileExists(StopBat) then
    Exec(StopBat, '', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  AppDir := ExpandConstant('{autopf}\{#MyAppName}');
  StopBat := AppDir + '\stop_backup_system.bat';
  if FileExists(StopBat) then
    Exec(StopBat, '', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  AppDir := ExpandConstant('{localappdata}\Programs\{#MyAppName}');
  StopBat := AppDir + '\stop_backup_system.bat';
  if FileExists(StopBat) then
    Exec(StopBat, '', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // 2. PowerShell 원라이너로 8765 포트 점유 프로세스 및 run.py / tray_app.py 프로세스 전수 강제 종료 및 파일 락 해제 대기
  KillPsCmd := 
    '-NoProfile -ExecutionPolicy Bypass -Command "' +
    '$ports = @(8765); ' +
    'Get-NetTCPConnection -LocalPort $ports -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; ' +
    'Get-CimInstance Win32_Process | Where-Object { ' +
    '  ($_.Name -in ''python.exe'',''pythonw.exe'') -and ($_.CommandLine -match ''(run\.py|tray_app\.py|백업시스템|Kova)'') ' +
    '} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; ' +
    'for ($i=0; $i -lt 10; $i++) { ' +
    '  $left = Get-CimInstance Win32_Process | Where-Object { ($_.Name -in ''python.exe'',''pythonw.exe'') -and ($_.CommandLine -match ''(run\.py|tray_app\.py|백업시스템|Kova)'') }; ' +
    '  if (-not $left) { break }; ' +
    '  Start-Sleep -Milliseconds 500; ' +
    '}"';

  Exec('powershell.exe', KillPsCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1000);
end;

// v2.14.1+: 설치 완료 즉시 최신 새 버전으로 무창 백그라운드 자동 재구동 (일반/무인 설치 무관)
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  AppDir, SilentVbs, TrayVbs: String;
begin
  if CurStep = ssPostInstall then
  begin
    AppDir := ExpandConstant('{app}');
    SilentVbs := AppDir + '\start_silent.vbs';
    TrayVbs := AppDir + '\start_tray.vbs';

    if FileExists(SilentVbs) then
    begin
      Exec('wscript.exe', '"' + SilentVbs + '"', AppDir, SW_HIDE, ewNoWait, ResultCode);
    end;
    if FileExists(TrayVbs) then
    begin
      Exec('wscript.exe', '"' + TrayVbs + '"', AppDir, SW_HIDE, ewNoWait, ResultCode);
    end;
  end;
end;

// v2.10.4: 언인스톨 시작 즉시 백업시스템 프로세스(트레이, 서버) 안전 종료 및 파일 잠금 선제 해제
function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
  StopBat: String;
begin
  Result := True;
  StopBat := ExpandConstant('{app}\stop_backup_system.bat');
  if FileExists(StopBat) then
  begin
    Exec(StopBat, '', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(1000);
  end;
end;


