; Circle — Inno Setup 6 installer script
; Build with:  iscc /DAppVersion=<version> /DAppArch=x64compatible installer\Circle.iss
; Produces:    installer\output\Circle-<version>-setup.exe
;
; Per-user install by default (no admin prompt). The architecture is a build
; parameter so the same script produces the x64 and the native ARM64 installer:
;   /DAppArch=x64compatible            -> Windows 10/11 x64 (and ARM64 emulation)
;   /DAppArch=arm64 /DArchSuffix=-arm64 -> Windows 11 on ARM, native

#define AppName "Circle"
; The version comes from version.py via /DAppVersion=<version>. Refusing to
; guess means a build can never quietly ship the wrong number.
#ifndef AppVersion
  #error AppVersion is not defined. Pass /DAppVersion=<version> (build_windows.ps1 does this).
#endif
#ifndef AppArch
  #define AppArch "x64compatible"
#endif
; Empty for x64, "-arm64" for the native ARM build.
#ifndef ArchSuffix
  #define ArchSuffix ""
#endif
#define AppPublisher "Circle"
#define AppExeName "Circle.exe"
#define AppId "{{8C2B4F1A-4A6B-4E2F-9C1D-2B7E5A3F6D10}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=output
OutputBaseFilename=Circle-{#AppVersion}{#ArchSuffix}-setup
SetupIconFile=..\circle.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Windows 10 (10.0.10240) and newer.
MinVersion=10.0.10240
ArchitecturesAllowed={#AppArch}
ArchitecturesInstallIn64BitMode={#AppArch}
; Install per-user when the user is not an admin, per-machine when they are.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
RestartApplications=no
AllowNoIcons=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "startup"; Description: "Start Circle when I sign in"; GroupDescription: "Startup:"; Flags: checkedonce

[Files]
Source: "..\dist\Circle\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; \
    ValueName: "Circle"; ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Start {#AppName} now"; \
    Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /f /im {#AppExeName}"; Flags: runhidden; RunOnceId: "StopCircle"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
{ Refuse to install over a running copy instead of half-copying files. }
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if Exec(ExpandConstant('{cmd}'), '/c tasklist /fi "imagename eq Circle.exe" | find /i "Circle.exe"',
          '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      if MsgBox('Circle is running. Setup will close it so the files can be replaced. Continue?',
                mbConfirmation, MB_YESNO) = IDYES then
        Exec(ExpandConstant('{cmd}'), '/c taskkill /f /im Circle.exe', '', SW_HIDE,
             ewWaitUntilTerminated, ResultCode)
      else
        Result := False;
    end;
  end;
end;
