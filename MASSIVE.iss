;MASSIVE Launcher InnoSetup script

[Setup]
AppName=MASSIVE Launcher
AppVersion=0.1.2
DefaultDirName={pf}\MASSIVE Launcher
DefaultGroupName=MASSIVE Launcher
UninstallDisplayIcon={app}\MASSIVE Launcher.exe
Compression=lzma2
SolidCompression=yes
OutputDir=Z:\Desktop\cvl_svn\launcher\trunk\

[Files]
Source: "dist\*.*"; DestDir: "{app}"
; Source: "MyProg.chm"; DestDir: "{app}"
;Source: "Readme.txt"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{group}\MASSIVE Launcher"; Filename: "{app}\MASSIVE Launcher.exe"
