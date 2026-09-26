; =========================================================================
; 백업시스템 (BackupSystem) Inno Setup 6+ 인스톨러 빌드 스크립트
; =========================================================================

#define MyAppName "백업시스템"
#define MyAppVersion "2.9.8"
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
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Windows 부팅 시 백그라운드 자동 시작"; GroupDescription: "시작 옵션:"

[Files]
; 배포 번들 전체 복사 (tools/build_exe.py 빌드 결과물)
Source: "..\dist\BackupSystem\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; VBScript 래퍼 및 환경 설정 파일
Source: "..\start_silent.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\start_tray.vbs"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\stop_backup_system.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\VERSION"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName} 웹 대시보드"; Filename: "{#MyAppURL}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} 트레이 에이전트 실행"; Filename: "wscript.exe"; Parameters: """{app}\start_tray.vbs"""; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} 서비스 종료"; Filename: "{app}\stop_backup_system.bat"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName} 대시보드"; Filename: "{#MyAppURL}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Windows 시작프로그램 자동 등록
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BackupSystemService"; ValueData: "wscript.exe ""{app}\start_silent.vbs"""; Flags: uninsdeletevalue; Tasks: startupicon
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BackupSystemTray"; ValueData: "wscript.exe ""{app}\start_tray.vbs"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; 방화벽 포트 8765 허용 등록
Filename: "netsh.exe"; Parameters: "advfirewall firewall add rule name=""BackupSystem"" dir=in action=allow protocol=TCP localport=8765"; Flags: runhidden
; 설치 완료 후 트레이 및 백업 서비스 백그라운드 구동
Filename: "wscript.exe"; Parameters: """{app}\start_silent.vbs"""; Flags: nowait postinstall skipifsilent; Description: "백업 서비스 백그라운드 시작"
Filename: "wscript.exe"; Parameters: """{app}\start_tray.vbs"""; Flags: nowait postinstall skipifsilent; Description: "시스템 트레이 에이전트 시작"

[UninstallRun]
; 서비스 종료 및 방화벽 규칙 제거
Filename: "{app}\stop_backup_system.bat"; Flags: runhidden
Filename: "netsh.exe"; Parameters: "advfirewall firewall delete rule name=""BackupSystem"""; Flags: runhidden
