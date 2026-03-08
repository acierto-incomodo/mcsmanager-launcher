[Setup]
AppName=MCSManager by StormGamesStudios
AppVersion=1.0.4
DefaultDirName={userappdata}\StormGamesStudios\Programs\MCSManager
DefaultGroupName=StormGamesStudios
OutputDir=C:\Users\melio\Documents\GitHub\mcsmanager-launcher\output
OutputBaseFilename=MCSManager_Launcher_Installer
Compression=lzma
SolidCompression=yes
AppCopyright=Copyright © 2025 StormGamesStudios. All rights reserved.
VersionInfoCompany=StormGamesStudios
AppPublisher=StormGamesStudios
SetupIconFile=mcsmanager-launcher.ico
VersionInfoVersion=1.0.4.0
DisableProgramGroupPage=yes
; Habilitar selección de carpeta
DisableDirPage=no

[Files]
Source: "C:\Users\melio\Documents\GitHub\mcsmanager-launcher\dist\installer_updater.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\melio\Documents\GitHub\mcsmanager-launcher\mcsmanager-launcher.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\Users\melio\Documents\GitHub\mcsmanager-launcher\mcsmanager-launcher.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{commonprograms}\StormGamesStudios\MCSManager"; Filename: "{app}\installer_updater.exe"; IconFilename: "{app}\mcsmanager-launcher.ico"; Comment: "Lanzador de MCSManager"; WorkingDir: "{app}"
Name: "{commonprograms}\StormGamesStudios\Desinstalar MCSManager"; Filename: "{uninstallexe}"; IconFilename: "{app}\mcsmanager-launcher.ico"; Comment: "Desinstalar MCSManager"

[Registry]
Root: HKCU; Subkey: "Software\MCSManager"; ValueType: string; ValueName: "Install_Dir"; ValueData: "{app}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Run]
Filename: "{app}\installer_updater.exe"; Description: "Ejecutar MCSManager"; Flags: nowait postinstall skipifsilent

[Code]
procedure CloseApp();
var
  ResultCode: Integer;
begin
  // Cierra el actualizador y el launcher si están abiertos
  Exec('taskkill', '/F /IM installer_updater.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/F /IM win_launcher.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill', '/F /IM "start.bat"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  // Durante la instalación, cierra cualquier instancia abierta
  if CurStep = ssInstall then
  begin
    CloseApp();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // Durante la desinstalación, cierra cualquier instancia abierta
  if CurUninstallStep = usUninstall then
  begin
    CloseApp();
  end;
end;