; Inno Setup Script for Omni Downloader v1.0.1
; High-performance, portable-ready installer with zero-admin requirements

#define MyAppName "Omni Downloader"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Omni Downloader"
#define MyAppURL "https://github.com/hexvish/omni-downloader"
#define MyAppExeName "OmniDownloader.exe"

[Setup]
; Unique GUID identifying Omni Downloader for seamless updates
AppId={{E581D1A9-B58C-4D2A-949B-501A79B19C91}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Install to User's Local AppData (requires NO administrator/UAC elevation)
DefaultDirName={localappdata}\Programs\OmniDownloader
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=OmniDownloader-Setup-v{#MyAppVersion}
SetupIconFile=app.ico
UninstallDisplayIcon={app}\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
CloseApplications=force
CloseApplicationsFilter=*.exe
RestartApplications=no
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copy all packaged files from dist\OmniDownloader into the user's installation directory
Source: "dist\OmniDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "app.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up temporary staging downloads and cache upon full uninstall if user chooses
Type: filesandordirs; Name: "{app}\downloads"
Type: files; Name: "{localappdata}\OmniDownloader\crash.log"
