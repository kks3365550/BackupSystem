; =========================================================================
; Kova (Local Backup & Disaster Recovery) Inno Setup 6+ 인스톨러 빌드 스크립트
; =========================================================================

#define MyAppName "Kova"
#define MyAppVersion "2.15.4"
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
// v2.15.1+: 파일 복사 직전(ssInstall) 또는 언인스톨 시 기존 백업 프로세스(pythonw.exe, 8765 포트) 무조건 강제 사살 및 DLL 잠금 해제 대기
procedure KillExistingProcesses();
var
  ResultCode: Integer;
  TaskkillExe, CmdExe, PsExe, KillPsCmd: String;
begin
  TaskkillExe := ExpandConstant('{sys}\taskkill.exe');
  CmdExe := ExpandConstant('{cmd}');
  PsExe := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');

  // 1. Windows taskkill.exe 직접 호출로 백그라운드 서버/트레이(pythonw.exe) 무조건 강제 사살
  // 주의: 설치 프로그램 자신(Setup, Kova_Setup_*.exe)은 절대로 죽이지 않도록 오직 pythonw.exe만 정확히 타겟
  if FileExists(TaskkillExe) then
  begin
    Exec(TaskkillExe, '/F /T /IM pythonw.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end
  else
  begin
    Exec('taskkill.exe', '/F /T /IM pythonw.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;

  // 2. 8765 포트 점유 PID 전수 강제 사살 (netstat -> taskkill /PID)
  Exec(CmdExe, '/c "for /f ""tokens=5"" %a in (''netstat -aon ^| findstr :8765 ^| findstr LISTENING'') do if not ""%a""==""0"" taskkill /F /PID %a"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // 3. 백업시스템 관련 예약 작업(Task Scheduler) 중단
  Exec('schtasks.exe', '/End /TN "BackupSystem_AutoBackup"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('schtasks.exe', '/End /TN "BackupSystem_WebServer"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('schtasks.exe', '/End /TN "BackupSystem_Server"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('schtasks.exe', '/End /TN "BackupSystem_Server_Daemon"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // 4. PowerShell 2차 안전망: 인스톨러 자신(setup, is-*.tmp) 및 PID는 절대 제외하고 8765 포트 및 pythonw 잔여 프로세스 사살
  KillPsCmd :=
    '-NoProfile -ExecutionPolicy Bypass -Command "' +
    'Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | ForEach-Object { if ($_.OwningProcess -ne 0) { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }; ' +
    'Get-Process -ErrorAction SilentlyContinue | Where-Object { ($_.Name -eq ''pythonw'') -and ($_.Name -notmatch ''(?i)(setup|is-)'') } | ForEach-Object { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue }"';

  if FileExists(PsExe) then
    Exec(PsExe, KillPsCmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // 5. Windows 파일 핸들 / DLL 락(libcrypto-3.dll 등) 완전 해제 보장 대기 (1.5초)
  Sleep(1500);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// v2.15.1+: 설치 시작 및 완료 시점 백업시스템 프로세스 라이프사이클 관리
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  AppDir, SilentVbs, TrayVbs: String;
begin
  if CurStep = ssInstall then
  begin
    // 파일 복사(추출) 직전 최종적으로 기존 프로세스 확실하게 종료하여 DLL 잠금 원천 방지
    KillExistingProcesses();
  end
  else if CurStep = ssPostInstall then
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

// v2.15.1+: 언인스톨 시작 즉시 백업시스템 프로세스 전수 사살 및 파일 잠금 선제 해제
function InitializeUninstall(): Boolean;
begin
  Result := True;
  KillExistingProcesses();
end;


