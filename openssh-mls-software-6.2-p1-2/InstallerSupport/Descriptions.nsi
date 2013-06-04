;Language strings
LangString DESC_Shared ${LANG_ENGLISH} "Shared Tools for both Server and Client Utilities."
LangString DESC_Client ${LANG_ENGLISH} "Client tools for connection to remote SSH servers."
LangString DESC_Server ${LANG_ENGLISH} "SSH and SFTP server to allow remote connections."
LangString DESC_Shortcuts ${LANG_ENGLISH} "Shortcuts to documentation and website."

;Assign language strings to sections
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${Shared} $(DESC_Shared)
  !insertmacro MUI_DESCRIPTION_TEXT ${Client} $(DESC_Client)
  !insertmacro MUI_DESCRIPTION_TEXT ${Server} $(DESC_Server)
  !insertmacro MUI_DESCRIPTION_TEXT ${Shortcuts} $(DESC_Shortcuts)
!insertmacro MUI_FUNCTION_DESCRIPTION_END
