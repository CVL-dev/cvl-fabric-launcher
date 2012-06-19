; -- Example1.iss --
; Demonstrates copying 3 files and creating an icon.

; SEE THE DOCUMENTATION FOR DETAILS ON CREATING .ISS SCRIPT FILES!

[Setup]
AppName=MASSIVE
AppVersion=0.0.2
DefaultDirName={pf}\MASSIVE
DefaultGroupName=MASSIVE
UninstallDisplayIcon={app}\MASSIVE.exe
Compression=lzma2
SolidCompression=yes
OutputDir=Z:\Desktop\cvl_svn\launcher\trunk\

[Files]
Source: "dist\*.*"; DestDir: "{app}"
; Source: "MyProg.chm"; DestDir: "{app}"
;Source: "Readme.txt"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{group}\MASSIVE"; Filename: "{app}\MASSIVE.exe"
