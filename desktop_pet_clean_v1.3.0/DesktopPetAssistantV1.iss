#ifndef MyAppId
  #define MyAppId "{{6E4A77B5-0BC2-4A8C-BE8A-9D0CF4D5C7B1}}"
#endif
#ifndef MyAppName
  #define MyAppName "桌宠助手"
#endif
#ifndef MyAppVersion
  #define MyAppVersion "1.3.0"
#endif
#ifndef MyAppPublisher
  #define MyAppPublisher "liangxing3"
#endif
#ifndef MyAppURL
  #define MyAppURL "https://github.com/liangxing3/deskpot"
#endif
#ifndef MyAppInternalName
  #define MyAppInternalName "DesktopPetAssistantV1"
#endif
#ifndef MyAppExeName
  #define MyAppExeName MyAppInternalName + ".exe"
#endif
#ifndef MySetupBasename
  #define MySetupBasename MyAppInternalName + "-Setup"
#endif
#define ProjectDir AddBackslash(SourcePath)
#define DistDir ProjectDir + "dist\\" + MyAppInternalName
#define AssetsDir ProjectDir + "assets\\"
#define OutputDir ProjectDir + "installer"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVerName={#MyAppName} {#MyAppVersion}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\{#MyAppInternalName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
UsePreviousGroup=yes
SetupIconFile={#AssetsDir}app_icon.ico
OutputDir={#OutputDir}
OutputBaseFilename={#MySetupBasename}-v{#MyAppVersion}
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription=桌宠助手安装程序

[Languages]
Name: "default"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务"; Flags: unchecked

[InstallDelete]
Type: files; Name: "{app}\{#MyAppExeName}"
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\assets\app_icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\assets\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
