; Inno Setup Script for TTS_Lite Application v1.0.0

[Setup]
AppId={{B1E3A4F2-5C6D-4E7F-8A9B-0C1D2E3F4A5B}
AppName=TTS_Lite
AppVersion=1.0.0
AppPublisher=TTS Lite Application
AppPublisherURL=https://github.com/ttsapp
AppSupportURL=cryptomonstrik@gmail.com
AppContact=cryptomonstrik@gmail.com
DefaultDirName={autopf}\TTS_Lite
DefaultGroupName=TTS_Lite
OutputDir=installer
OutputBaseFilename=setup_TTS_Lite_1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=LICENSE.txt

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\TTS_Lite\TTS_Lite.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\TTS_Lite\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\TTS_Lite"; Filename: "{app}\TTS_Lite.exe"
Name: "{group}\{cm:Program,TTS_Lite}\{cm:License}"; Filename: "{app}\LICENSE.txt"
Name: "{group}\{cm:Program,TTS_Lite}\{cm:Readme}"; Filename: "{app}\README.md"
Name: "{autodesktop}\TTS_Lite"; Filename: "{app}\TTS_Lite.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TTS_Lite.exe"; Description: "{cm:LaunchProgram}"; Flags: nowait postinstall skipifsilent

[CustomMessages]
russian.License=Лицензия
russian.Readme=Описание
russian.Program=Программа
english.License=License
english.Readme=Readme
english.Program=Program
