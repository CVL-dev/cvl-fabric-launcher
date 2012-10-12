;  MASSIVE/CVL Launcher - easy secure login for the MASSIVE Desktop and the CVL
;  Copyright (C) 2012  James Wettenhall, Monash University
;
;  This program is free software; you can redistribute it and/or modify
;  it under the terms of the GNU General Public License as published by
;  the Free Software Foundation; either version 2 of the License, or
;  (at your option) any later version.
;  
;  This program is distributed in the hope that it will be useful,
;  but WITHOUT ANY WARRANTY; without even the implied warranty of
;  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;  GNU General Public License for more details.
;  
;  You should have received a copy of the GNU General Public License
;  along with this program; if not, write to the Free Software
;  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
;
;  Enquires: James.Wettenhall@monash.edu or help@massive.org.a

;MASSIVE Launcher InnoSetup script
;Change OutputDir to suit your build environment

#define LauncherAppName "MASSIVE Launcher"
#define LauncherAppExeName "MASSIVE Launcher.exe"

[Setup]
AppName={#LauncherAppName}
AppVersion=0.3.0
DefaultDirName={pf}\{#LauncherAppName}
DefaultGroupName={#LauncherAppName}
UninstallDisplayIcon={app}\{#LauncherAppExeName}
Compression=lzma2
SolidCompression=yes
OutputDir=Z:\Desktop\cvl_svn\launcher\trunk\

[Files]
Source: "dist\*.*"; DestDir: "{app}"
; Source: "{#LauncherAppName}.chm"; DestDir: "{app}"
;Source: "Readme.txt"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{group}\{#LauncherAppName}"; Filename: "{app}\{#LauncherAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#LauncherAppName}}"; Filename: "{uninstallexe}"
