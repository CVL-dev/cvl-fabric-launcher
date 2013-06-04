
Section "Uninstall"

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
    MessageBox MB_OK|MB_ICONSTOP 'The installer found the OpenSSH on Windows service, but was unable to remove it. Please stop it and manually remove it. Then try the Uninstall again. Reason: $0'
    Abort

  Success:

  SkipRemoval:

	;now delete the users home directory for sshd_server
	nsExec::Exec `$INSTDIR\bin\junction.exe /accepteula -d "$INSTDIR\home"`

    ;Remove the directory from the path
    Push ";$INSTDIR\bin"
    Call un.RemoveFromPath

    ;Remove the installed directory - note that this does NOT backup any config or keys in /etc/
    Delete "$INSTDIR\uninstall.exe"
    ;DANGEROUS! WHACKED MY APPDATA ONE TIME! RMDir /r "$INSTDIR"

    RMDIR /r "$INSTDIR\bin"
    RMDIR /r "$INSTDIR\docs"
    RMDIR /r "$INSTDIR\etc"
    RMDIR /r "$INSTDIR\tmp"
    RMDIR /r "$INSTDIR\usr"
    RMDIR /r "$INSTDIR\var"
    RMDIR "$INSTDIR"

    ;Get the Start Menu Folder that the icons were installed in
    !insertmacro MUI_STARTMENU_GETFOLDER Application $MUI_TEMP

    ;Set the context to all users
    SetShellVarContext all

    ;Delete empty start menu parent diretories
    ;StrCpy $MUI_TEMP "$SMPROGRAMS\$MUI_TEMP"
    RMDIR /r "$SMPROGRAMS\OpenSSH for Windows"
    ;RMDir /r $MUI_TEMP

    ;Delete registry entries specific to the product
    DeleteRegKey HKLM "Software\OpenSSH for Windows"  ;Product Registry Entries - Holds Start Menu Info
    DeleteRegKey HKLM "SOFTWARE\Cygnus Solutions"  ;Holds mounts
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenSSH"  ;The Add/Remove Programs Entry

    ExpandEnvStrings $0 %COMSPEC%
    ;the && isn't deleting both, so break into two commands for now 
    ;ExecWait `"$0" /C "net user sshd /delete && net user sshd_server /delete"` ;remote created users
    ExecWait `"$0" /C "net user sshd /delete"` ;remote created users
    ExecWait `"$0" /C "net user sshd_server /delete"` ;remote created users


SectionEnd
