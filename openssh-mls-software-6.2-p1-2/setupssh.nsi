;This REQUIRES NSIS Modern User Interface Version 1.70 (NSIS 2.0-Final)

;OpenSSH for Windows 6.2p1-2, OpenSSL 0.9.8y/1.0.1.e
;Installer Script
;Written by Michael Johnson
;Updated and modified by Mark Saeger
;Based on script examples by Joost Verburg
;
;This script and related support files are licensed under the GPL

;Include ModernUI Components
!include "MUI.nsh"

;Extra Help Files - Path Addition and Deletion Functions
!include ".\InstallerSupport\Path.nsi"
!include ".\InstallerSupport\GetParent.nsi"

;General Variables (Installer Global ONLY)
Name "OpenSSH for Windows 6.2p1-2"                   ;The name of the product
SetCompressor bzip2                                  ;Use BZip2 Compression
OutFile "setupssh-6.2p1-2.exe"                       ;This is the name of the output file
!packhdr tmp.dat "c:\upx\upx.exe --best -q tmp.dat"  ;Compress the NSIS header with UPX

;Interface Customization
!define "MUI_ICON" "${NSISDIR}\Contrib\Graphics\Icons\orange-install.ico"
!define "MUI_UNICON" "${NSISDIR}\Contrib\Graphics\Icons\orange-uninstall.ico"
!define "MUI_HEADERIMAGE_RIGHT"
!define "MUI_HEADERIMAGE_BITMAP" "${NSISDIR}\Contrib\Graphics\Header\orange-r.bmp"
!define "MUI_HEADERIMAGE_UNBITMAP" "${NSISDIR}\Contrib\Graphics\Header\orange-uninstall-r.bmp"
!define "MUI_WELCOMEFINISHPAGE_BITMAP" "${NSISDIR}\Contrib\Graphics\Wizard\orange.bmp"
!define "MUI_UNWELCOMEFINISHPAGE_BITMAP" "${NSISDIR}\Contrib\Graphics\Wizard\orange-uninstall.bmp"


;Variables used by the script
Var MUI_TEMP
Var STARTMENU_FOLDER

Var PRIVSEP
Var SSHDSERVER
var SSHDPASS
var SSHDPORT
var SSHDDOMAIN

;The default install dir - The user can overwrite this later on
InstallDir "$PROGRAMFILES\OpenSSH"

;Check the Registry for an existing install directory choice (used in upgrades)
InstallDirRegKey HKLM "Software\OpenSSH for Windows" ""

;ModernUI Specific Interface Settings
!define MUI_ABORTWARNING                 ;Issue a warning if the user tries to reboot
;!define MUI_UI_COMPONENTSPAGE_SMALLDESC "${NSISDIR}\Contrib\UIs\modern-smalldesc.exe"  ;Show a smaller description area (under the components, instead of to the side

;StartMenu Configuration
!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKLM"
!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\OpenSSH for Windows"
!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"

;Page Specific Settings
!define MUI_STARTMENUPAGE_NODISABLE                               ;User cannot disable creation of StartMenu icons
!define MUI_LICENSEPAGE_RADIOBUTTONS                              ;Use radio buttons for license acceptance
!define MUI_FINISHPAGE_NOREBOOTSUPPORT                            ;Disable the reboot suport section for the finish page - we don't reboot anyway
!define MUI_STARTMENUPAGE_DEFAULTFOLDER "OpenSSH for Windows"     ;The default folder for the StartMenu
;!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\docs\quickstart.txt" ;The file linked as the readme

;Pages in the installer
!insertmacro MUI_PAGE_WELCOME                                 ;Welcome Page
!insertmacro MUI_PAGE_LICENSE "InstallerSupport\License.txt"  ;The license page, and the file to pull the text from
!insertmacro MUI_PAGE_COMPONENTS                              ;Software components page
!insertmacro MUI_PAGE_DIRECTORY                               ;Installation directory page
!insertmacro MUI_PAGE_STARTMENU Application $STARTMENU_FOLDER
Page custom SetupService LeaveService 			;Custom page for executing sshd as a different user
;privsep is ONLY relevant if they have chosen to run as a different user
;as the folder will be owned by sshd_server
Page custom SetupPrivSep LeavePrivSep 			;Custom page for executing priviledge seperation
Page custom SetupPort LeavePort					;Custom page for port setup
Page custom SetupPasswdGroup LeavePasswdGroup 			;Custom page for executing passwd/group setup
!insertmacro MUI_PAGE_INSTFILES                               ;Show installation progress
!insertmacro MUI_PAGE_FINISH                                  ;Display the finish page

;Pages in the uninstaller
!insertmacro MUI_UNPAGE_WELCOME    ;Show Uninstaller welcome page
!insertmacro MUI_UNPAGE_CONFIRM    ;Show uninstaller confirmation page - Does the user _really_ want to remove this awesome software?
!insertmacro MUI_UNPAGE_INSTFILES  ;Show uninstallation progress
!insertmacro MUI_UNPAGE_FINISH     ;Show uninstaller finish page

;Set the language we want the installer to be in (note this only applies for Installer-specific strings - everything else is in English)
!insertmacro MUI_LANGUAGE "English"

;Installer process sections - This is where the actual install takes place
!include ".\InstallerSupport\InstallerProcess.nsi"

;Descriptions - These are used when the component is moused-over and display in the description box
!include ".\InstallerSupport\Descriptions.nsi"

;Section for uninstaller process
!include ".\InstallerSupport\UnInstallerProcess.nsi"

;Handle silent parameters
!include "FileFunc.nsh"
!insertmacro GetParameters
!insertmacro GetOptions


Function SetupPasswdGroup
  SectionGetFlags ${Server} $R0 
  IntOp $R0 $R0 & ${SF_SELECTED} 
  IntCmp $R0 ${SF_SELECTED} show 
 
  Abort 
 
  show: 

!insertmacro MUI_HEADER_TEXT "Choose user type for SSHD" "Choose to execute SSHD for local or domain users"
	;Display custom dialog
	Push $R0

	IfFileExists $INSTDIR\etc\group processinput ;assume that if we have the group file created, then we don't want to whack the users stuff 
	InstallOptions::dialog $PLUGINSDIR\openssh_grppwd.ini
processinput:
	Pop $R0

FunctionEnd

Function LeavePasswdGroup
	;Process input (we are in usr/var at this point...)
	ReadINIStr $SSHDDOMAIN "$PLUGINSDIR\openssh_grppwd.ini" "Field 3" "State"
FunctionEnd


Function SetupPrivSep
  SectionGetFlags ${Server} $R0 
  IntOp $R0 $R0 & ${SF_SELECTED} 
  IntCmp $R0 ${SF_SELECTED} show 
 
  Abort 
 
  show: 
!insertmacro MUI_HEADER_TEXT "Choose SSHD priviledge seperation" "Choose to execute SSHD with or without priviledge seperation"
	;Display custom dialog
	Push $R0

	;only display the dialogue if the user has selected SSHDSERVER
	IntCmp $SSHDSERVER 0 +2
	InstallOptions::dialog $PLUGINSDIR\openssh_privsep.ini

	Pop $R0

FunctionEnd



Function WriteSshdConfig

;at this point, can re-write out the sshd_config file
  	SetOutPath $INSTDIR\etc
  	FileOpen $9 sshd_config w ;Opens a Empty File an fills it
	FileWrite $9 "#       $$OpenBSD: sshd_config,v 1.65 2003/08/28 12:54:34 markus Exp $$$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# This is the sshd server system-wide configuration file.  See$\r$\n"
	FileWrite $9 "# sshd_config(5) for more information.$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# The strategy used for options in the default sshd_config shipped with$\r$\n"
	FileWrite $9 "# OpenSSH is to specify options with their default value where$\r$\n"
	FileWrite $9 "# possible, but leave them commented.  Uncommented options change a$\r$\n"
	FileWrite $9 "# default value.$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "Port $SSHDPORT$\r$\n"
	FileWrite $9 "#Protocol 2,1$\r$\n"
	FileWrite $9 "Protocol 2$\r$\n"
	FileWrite $9 "#ListenAddress 0.0.0.0$\r$\n"
	FileWrite $9 "#ListenAddress ::$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# HostKey for protocol version 1$\r$\n"
	FileWrite $9 "#HostKey /etc/ssh/ssh_host_key$\r$\n"
	FileWrite $9 "# HostKeys for protocol version 2$\r$\n"
	FileWrite $9 "#HostKey /etc/ssh/ssh_host_rsa_key$\r$\n"
	FileWrite $9 "#HostKey /etc/ssh/ssh_host_dsa_key$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# Lifetime and size of ephemeral version 1 server key$\r$\n"
	FileWrite $9 "#KeyRegenerationInterval 1h$\r$\n"
	FileWrite $9 "#ServerKeyBits 768$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# Logging$\r$\n"
	FileWrite $9 "#obsoletes QuietMode and FascistLogging$\r$\n"
	FileWrite $9 "#SyslogFacility AUTH$\r$\n"
	FileWrite $9 "#LogLevel INFO$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# Authentication:$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "#LoginGraceTime 2m$\r$\n"
	FileWrite $9 "PermitRootLogin yes$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# The following setting overrides permission checks on host key files$\r$\n"
	FileWrite $9 "# and directories. For security reasons set this to $\"yes$\" when running$\r$\n"
	FileWrite $9 "# NT/W2K, NTFS and CYGWIN=ntsec.$\r$\n"
	FileWrite $9 "StrictModes yes$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "RSAAuthentication no$\r$\n"
	FileWrite $9 "#PubkeyAuthentication yes$\r$\n"
	FileWrite $9 "#AuthorizedKeysFile	.ssh/authorized_keys$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# For this to work you will also need host keys in /etc/ssh/ssh_known_hosts$\r$\n"
	FileWrite $9 "#RhostsRSAAuthentication no$\r$\n"
	FileWrite $9 "# similar for protocol version 2$\r$\n"
	FileWrite $9 "#HostbasedAuthentication no$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# Change to yes if you don't trust ~/.ssh/known_hosts for$\r$\n"
	FileWrite $9 "# RhostsRSAAuthentication and HostbasedAuthentication$\r$\n"
	FileWrite $9 "IgnoreUserKnownHosts yes$\r$\n"
	FileWrite $9 "# Don't read the user's ~/.rhosts and ~/.shosts files$\r$\n"
	FileWrite $9 "#IgnoreRhosts yes$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# To disable tunneled clear text passwords, change to no here!$\r$\n"
	FileWrite $9 "PasswordAuthentication yes$\r$\n"
	FileWrite $9 "#PermitEmptyPasswords no$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# Change to no to disable s/key passwords$\r$\n"
	FileWrite $9 "#ChallengeResponseAuthentication yes$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# Kerberos options$\r$\n"
	FileWrite $9 "#KerberosAuthentication no$\r$\n"
	FileWrite $9 "#KerberosOrLocalPasswd yes$\r$\n"
	FileWrite $9 "#KerberosTicketCleanup yes$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# GSSAPI options$\r$\n"
	FileWrite $9 "#GSSAPIAuthentication no$\r$\n"
	FileWrite $9 "#GSSAPICleanupCreds yes$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# Set this to 'yes' to enable PAM authentication (via challenge-response)$\r$\n"
	FileWrite $9 "# and session processing. Depending on your PAM configuration, this may$\r$\n"
	FileWrite $9 "# bypass the setting of 'PasswordAuthentication'$\r$\n"
	FileWrite $9 "#UsePAM yes$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "#AllowTcpForwarding yes$\r$\n"
	FileWrite $9 "#GatewayPorts no$\r$\n"
	FileWrite $9 "#X11Forwarding no$\r$\n"
	FileWrite $9 "#X11DisplayOffset 10$\r$\n"
	FileWrite $9 "#X11UseLocalhost yes$\r$\n"
	FileWrite $9 "#PrintMotd yes$\r$\n"
	FileWrite $9 "#PrintLastLog yes$\r$\n"
	FileWrite $9 "#KeepAlive yes$\r$\n"
	FileWrite $9 "#UseLogin no$\r$\n"
	StrCmp $PRIVSEP 1 +3				;if PRIVSEP==1, the set as yes, else as no
	FileWrite $9 "UsePrivilegeSeparation no$\r$\n"
	goto +2
	FileWrite $9 "UsePrivilegeSeparation yes$\r$\n"
	FileWrite $9 "#PermitUserEnvironment no$\r$\n"
	FileWrite $9 "#Compression yes$\r$\n"
	FileWrite $9 "#ClientAliveInterval 0$\r$\n"
	FileWrite $9 "#ClientAliveCountMax 3$\r$\n"
	FileWrite $9 "#UseDNS yes$\r$\n"
	FileWrite $9 "#PidFile /var/run/sshd.pid$\r$\n"
	FileWrite $9 "MaxStartups 10:30:60$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# default banner path$\r$\n"
	FileWrite $9 "Banner /etc/banner.txt$\r$\n"
	FileWrite $9 "$\r$\n"
	FileWrite $9 "# override default of no subsystems$\r$\n"
	FileWrite $9 "Subsystem	sftp	/usr/sbin/sftp-server$\r$\n"
	FileClose $9 ;Closes the filled file

FunctionEnd


Function LeavePrivSep
	Push $R0
	IntCmp $SSHDSERVER 0 +2
	ReadINIStr $PRIVSEP "$PLUGINSDIR\openssh_privsep.ini" "Field 2" "State"
	Pop $R0
FunctionEnd


Function SetupService
  SectionGetFlags ${Server} $R0 
  IntOp $R0 $R0 & ${SF_SELECTED} 
  IntCmp $R0 ${SF_SELECTED} show 
 
  Abort 
 
  show: 
!insertmacro MUI_HEADER_TEXT "Choose account under which to execute SSHD" "Choose to execute SSHD as either LOCAL_SYSTEM or SSHD_SERVER"
	;Display custom dialog
	Push $R0

	InstallOptions::dialog $PLUGINSDIR\openssh_service.ini

	Pop $R0

FunctionEnd

;to combine two dos commands, seperate w/ &&

Function LeaveService
	ReadINIStr $0 "$PLUGINSDIR\openssh_service.ini" "Settings" "State"
	StrCmp $0 0 nextbutton
	StrCmp $0 2 disablepwd
	StrCmp $0 3 enablepwd
	Abort
disablepwd:
	;MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "disable pwd"
	ReadINIStr $1 "$PLUGINSDIR\openssh_service.ini" "Field 4" "HWND"
	EnableWindow $1 0 ;disable the window
	ReadINIStr $1 "$PLUGINSDIR\openssh_service.ini" "Field 4" "HWND2"
	EnableWindow $1 0 ;disable the window
	Abort ;back to dialog		
enablepwd:
	;MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "enable pwd"
	ReadINIStr $1 "$PLUGINSDIR\openssh_service.ini" "Field 4" "HWND"
	EnableWindow $1 1 ;enable the window
	ReadINIStr $1 "$PLUGINSDIR\openssh_service.ini" "Field 4" "HWND2"
	EnableWindow $1 1 ;enable the window	
	Abort ;back to dialog	
nextbutton:
	StrCpy $SSHDSERVER 0
	;Process input (we are in usr/var at this point...)
	ReadINIStr $R0 "$PLUGINSDIR\openssh_service.ini" "Field 2" "State"
	IntCmp $R0 1 end
   	ReadINIStr $SSHDPASS "$PLUGINSDIR\openssh_service.ini" "Field 4" "State"	
	StrCpy $SSHDSERVER 1
end:

FunctionEnd

Function SetupPort
  SectionGetFlags ${Server} $R0 
  IntOp $R0 $R0 & ${SF_SELECTED} 
  IntCmp $R0 ${SF_SELECTED} show 
 
  Abort 
 
  show: 
!insertmacro MUI_HEADER_TEXT "Choose port for SSHD daemon" "Choose port for SSDH listener daemon"
	;Display custom dialog
	Push $R0

	InstallOptions::dialog $PLUGINSDIR\openssh_port.ini

	Pop $R0

FunctionEnd

;SSHDPORT is set by Silent
Function LeavePort
	Push $R0
  	ReadINIStr $SSHDPORT "$PLUGINSDIR\openssh_port.ini" "Field 2" "State"	
	Pop $R0
FunctionEnd

Function .onInit
	;defaults
	StrCpy $SSHDPORT 22
	StrCpy $SSHDSERVER 0
	StrCpy $PRIVSEP 0
	StrCpy $SSHDPASS ""
	StrCpy $SSHDDOMAIN 0

	;handle cmd line parameters
	;/port=XX    [valid port]
	;/password=serverpassword [overloaded, will run as sshd_server with serverpassword]
	;/privsep=X  [0|1] [only valid if have /server, else forced to 0]
	;/domain=X [0|1]
	${GetParameters} $R0
	ClearErrors
	${GetOptions} $R0 /port= $0
	${GetOptions} $R0 /password= $1
	${GetOptions} $R0 /privsep= $2
	${GetOptions} $R0 /domain= $3	
	;only if we have values passed in would we overwrite
	StrCmp $0 "" +2
	StrCpy $SSHDPORT $0
	StrCmp $1 "" +3
	StrCpy $SSHDPASS $1
	StrCpy $SSHDSERVER 1 ;force this to on
	StrCmp $2 "" +2
	StrCpy $PRIVSEP $2
	StrCmp $3 "" +2
	StrCpy $SSHDDOMAIN $3

	;force PRIVSEP to off if the user didn't set sshd_server
	IntCmp $SSHDSERVER 1 +2
	StrCpy $PRIVSEP 0  ;force to off
	
	;debug
	;MessageBox MB_OK|MB_ICONINFORMATION "port=$SSHDPORT password=$SSHDPASS server=$SSHDSERVER privsep=$PRIVSEP domain=$SSHDDOMAIN"

  ;dispaly splash screen

  # the plugins dir is automatically deleted when the installer exits
  InitPluginsDir
  File /oname=$PLUGINSDIR\splash.bmp ".\InstallerSupport\openssh.bmp"
  IfSilent +3
   splash::show 1800 $PLUGINSDIR\splash
   Pop $0 ; $0 has '1' if the user closed the splash screen early,
   ; '0' if everything closed normally, and '-1' if some error occurred.

	;these ARE NOT called if silent!
	;must code the stuff in here


	;read custom fields
	File /oname=$PLUGINSDIR\openssh_grppwd.ini ".\InstallerSupport\openssh_grppwd.ini"
	File /oname=$PLUGINSDIR\openssh_privsep.ini ".\InstallerSupport\openssh_privsep.ini"
	File /oname=$PLUGINSDIR\openssh_service.ini ".\InstallerSupport\openssh_service.ini"
	File /oname=$PLUGINSDIR\openssh_port.ini ".\InstallerSupport\openssh_port.ini"


	;uninstall old version if found
  	ReadRegStr $R0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenSSH" "UninstallString"
	StrCmp $R0 "" done
	;MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "OpenSSH is already installed. $\n$\nClick `OK` to remove the previous version or `Cancel` to cancel this upgrade." IDOK uninst
	IfSilent uninst
	MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "OpenSSH is already installed. $\n$\nClick `OK` to remove the previous version or `Cancel` to retain the previous version." IDOK uninst
  	;Abort
	goto done ;just allow the user to continue, without doing the remove...
  
	;Run the uninstaller
uninst:
	ClearErrors
 	ExecWait '$R0 _?=$INSTDIR' ;Do not copy the uninstaller to a temp file

 	IfErrors no_remove_uninstaller
	goto done
    	;You can either use Delete /REBOOTOK in the uninstaller or add some code
   	 ;here to remove the uninstaller. Use a registry key to check
    	;whether the user has chosen to uninstall. If you are using an uninstaller
    	;components page, make sure all sections are uninstalled.
no_remove_uninstaller:
	MessageBox MB_OK|MB_ICONSTOP "De-installation failed.  Aborting..."
	Abort
done:




  ;Check for other Cygwin apps that could break

;NOTE: update this to use a loop

  ;Look for old-style SSH install
  IfFileExists "c:\ssh" PriorCygwin
  IfFileExists "d:\ssh" PriorCygwin
  IfFileExists "e:\ssh" PriorCygwin
  IfFileExists "f:\ssh" PriorCygwin

  ;Look for Cygwin install
  IfFileExists "c:\cygwin" PriorCygwin
  IfFileExists "d:\cygwin" PriorCygwin
  IfFileExists "e:\cygwin" PriorCygwin
  IfFileExists "f:\cygwin" PriorCygwin

  ;Look for the Cygwin mounts registry structure
  ReadRegStr $7 HKLM "SOFTWARE\Cygnus Solutions\Cygwin\mounts v2\/" "native"

  ;Look and see if read failed (good thing)
  IfErrors ContinueInstall PriorCygwin

  ;Error messsage and question user
  PriorCygwin:
    ;Prompt. Ask if user wants to continue
    IfSilent ContinueInstall
    MessageBox MB_YESNO|MB_ICONINFORMATION "It appears that either cygwin or an earlier version of the OpenSSH for Windows package is installed, because setup is detecting Cygwin registry mounts (HKLM\SOFTWARE\Cygnus Solutions\...). If you're upgrading an OpenSSH for Windows package you can ignore this, but if not you should stop the installation.  Keep going?" IDYES ContinueInstall
    ;If user does not want to continue, quit
    Quit

  ;Continue Installation, called if no prior cygwin or user wants to continue
  ContinueInstall:
    ;Set output to the ssh subdirectory of the install path
    SetOutPath $TEMP\bin

    ;Add the cygwin service runner to the output directory
    File bin\cygrunsrv.exe
    File bin\cygwin1.dll

    ;Find out if the OpenSSHd Service is installed
    Push 'OpenSSHd'
    Services::IsServiceInstalled
    Pop $0
    ; $0 now contains either 'Yes', 'No' or an error description
    StrCmp $0 'Yes' RemoveServices SkipRemoval



    ;This will stop and remove the OpenSSHd service if it is running.
    RemoveServices:
      push 'OpenSSHd'
      push 'Stop'
      Services::SendServiceCommand

      push 'OpenSSHd'
      push 'Delete'
      Services::SendServiceCommand
      Pop $0
      StrCmp $0 'Ok' Success
      MessageBox MB_OK|MB_ICONSTOP 'The installer found the OpenSSH for Windows service, but was unable to remove it. Please stop it and manually remove it. Then try installing again.'
      Abort

      Success:
	ExpandEnvStrings $0 %COMSPEC%
	ExecWait `"$0" /C net user sshd_server /delete`		;delete account
	ExecWait `"$0" /C net localgroup Administrators sshd_server /delete`

    SkipRemoval:

FunctionEnd

Function .onInstSuccess

	; could also set user home dir here


    ;Find out if the OpenSSHd Service is installed
    Push 'OpenSSHd'
    Services::IsServiceInstalled
    Pop $0
    ; $0 now contains either 'Yes', 'No' or an error description
    StrCmp $0 'Yes' StartService SkipStart

    ;This will start OpenSSHd service if it is running.
StartService:
      push 'OpenSSHd'
      push 'Start'
      Services::SendServiceCommand
      Pop $0
SkipStart:
FunctionEnd

