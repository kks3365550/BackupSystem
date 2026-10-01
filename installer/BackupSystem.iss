; =========================================================================
; 백업시스템 (BackupSystem) Inno Setup 6+ 인스톨러 빌드 스크립트 (v2.9.11)
; =========================================================================

#define MyAppName "백업시스템"
#define MyAppVersion "2.10.1"
#define MyAppPublisher "삼영데리카후레쉬"
#define MyAppURL "http://127.0.0.1:8765"
#define MyAppExeName "BackupSystem.exe"

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
OutputBaseFilename=BackupSystem_Setup_v{#MyAppVersion}
OutputDir=..\dist
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Windows 부팅 시 백그라운드 자동 시작"; GroupDescription: "시작 옵션:"

[Files]
; 1. Embedded Python 3.11 Runtime (Self-Contained)
Source: "runtime\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

; 2. Application Core Source Tree (v2.9.21 Production Source)
Source: "..\core\*"; DestDir: "{app}\core"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,*.pyo"
Source: "..\web\*"; DestDir: "{app}\web"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__,*.pyc,*.pyo"
Source: "..\run.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\VERSION"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\keys\release_ed25519.pub"; DestDir: "{app}\keys"; Flags: ignoreversion
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
Filename: "wscript.exe"; Parameters: """{app}\start_silent.vbs"""; Flags: nowait postinstall skipifsilent; Description: "백업 서비스 백그라운드 시작"
Filename: "wscript.exe"; Parameters: """{app}\start_tray.vbs"""; Flags: nowait postinstall skipifsilent; Description: "시스템 트레이 에이전트 시작"

[UninstallRun]
Filename: "{app}\stop_backup_system.bat"; Flags: runhidden
Filename: "schtasks.exe"; Parameters: "/delete /tn ""BackupSystem_WebServer"" /f"; Flags: runhidden
Filename: "schtasks.exe"; Parameters: "/delete /tn ""BackupSystem_Server_Daemon"" /f"; Flags: runhidden
Filename: "netsh.exe"; Parameters: "advfirewall firewall delete rule name=""BackupSystem"""; Flags: runhidden; Check: IsAdminInstallMode
