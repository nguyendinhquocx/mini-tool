; File Rename Tool - Professional NSIS Installer
; Vietnamese File Normalization Utility
; Copyright 2025 File Rename Tool Team

!define APPNAME "File Rename Tool"
!define COMPANYNAME "File Rename Tool Team"
!define DESCRIPTION "Vietnamese File Normalization Utility"
!define APPKEY "FileRenameTool"
!define VERSIONMAJOR 1
!define VERSIONMINOR 0
!define VERSIONBUILD 0

; Calculated variables
!define HELPURL "https://github.com/file-rename-tool/help"
!define UPDATEURL "https://github.com/file-rename-tool/updates"
!define ABOUTURL "https://github.com/file-rename-tool"
!define INSTALLSIZE 25000 ; KB estimate - will be updated during build

; Include modern UI
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"
!include "x64.nsh"

; General settings
Name "${APPNAME}"
OutFile "FileRenameToolSetup.exe"
Unicode True
RequestExecutionLevel admin ; Request admin privileges for proper integration
InstallDir "$PROGRAMFILES\${APPNAME}"
InstallDirRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "InstallLocation"

; Version information
VIProductVersion "${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}.0"
VIAddVersionKey "ProductName" "${APPNAME}"
VIAddVersionKey "Comments" "${DESCRIPTION}"
VIAddVersionKey "CompanyName" "${COMPANYNAME}"
VIAddVersionKey "LegalCopyright" "© 2025 ${COMPANYNAME}"
VIAddVersionKey "FileDescription" "${APPNAME} Installer"
VIAddVersionKey "FileVersion" "${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}.0"

; Interface settings
!define MUI_ABORTWARNING
!define MUI_ICON "app.ico"
!define MUI_UNICON "app.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "header.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP "welcome.bmp"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "license.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

; Finish page settings
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APPKEY}.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APPNAME}"
!define MUI_FINISHPAGE_LINK "Visit our website for help and updates"
!define MUI_FINISHPAGE_LINK_LOCATION "${ABOUTURL}"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; Languages
!insertmacro MUI_LANGUAGE "English"

; Version check function
Function .onInit
  ; Check if Windows 7 or later
  ${IfNot} ${AtLeastWin7}
    MessageBox MB_OK|MB_ICONSTOP "This application requires Windows 7 or later."
    Abort
  ${EndIf}
  
  ; Check if already running
  System::Call 'kernel32::CreateMutexA(i 0, i 0, t "FileRenameToolInstaller") i .r1 ?e'
  Pop $R0
  StrCmp $R0 0 +3
    MessageBox MB_OK|MB_ICONEXCLAMATION "The installer is already running."
    Abort
    
  ; Check if application is running
  FindProcDLL::FindProc "${APPKEY}.exe"
  StrCmp $R0 1 0 continueInstall
    MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION "${APPNAME} is currently running. Please close it before continuing." IDOK continueInstall
    Abort
  continueInstall:
FunctionEnd

; Main installation section
Section "Core Application" SecCore
  SectionIn RO ; Required section
  
  SetOutPath "$INSTDIR"
  
  ; Main executable
  File "..\dist\${APPKEY}.exe"
  
  ; Additional files if they exist
  IfFileExists "..\dist\*.dll" 0 +2
    File "..\dist\*.dll"
  
  ; Resources directory if exists
  IfFileExists "..\dist\resources\*.*" 0 +4
    CreateDirectory "$INSTDIR\resources"
    SetOutPath "$INSTDIR\resources"
    File /r "..\dist\resources\*.*"
  
  SetOutPath "$INSTDIR"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  ; Registry entries for Add/Remove Programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "DisplayName" "${APPNAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "QuietUninstallString" "$INSTDIR\uninstall.exe /S"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "DisplayIcon" "$INSTDIR\${APPKEY}.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "Publisher" "${COMPANYNAME}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "HelpLink" "${HELPURL}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "URLUpdateInfo" "${UPDATEURL}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "URLInfoAbout" "${ABOUTURL}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "DisplayVersion" "${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "VersionMajor" ${VERSIONMAJOR}
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "VersionMinor" ${VERSIONMINOR}
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "NoRepair" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}" "EstimatedSize" ${INSTALLSIZE}
  
  ; Register application path
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\${APPKEY}.exe" "" "$INSTDIR\${APPKEY}.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\${APPKEY}.exe" "Path" "$INSTDIR"
SectionEnd

; Desktop shortcut section
Section "Desktop Shortcut" SecDesktop
  CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${APPKEY}.exe" "" "$INSTDIR\${APPKEY}.exe" 0
SectionEnd

; Start Menu shortcuts section  
Section "Start Menu Shortcuts" SecStartMenu
  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\${APPKEY}.exe" "" "$INSTDIR\${APPKEY}.exe" 0
  CreateShortCut "$SMPROGRAMS\${APPNAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
  
  ; Create help shortcut if help file exists
  IfFileExists "$INSTDIR\help.pdf" 0 +2
    CreateShortCut "$SMPROGRAMS\${APPNAME}\User Guide.lnk" "$INSTDIR\help.pdf"
SectionEnd

; Quick Launch shortcut (for older Windows versions)
Section /o "Quick Launch Shortcut" SecQuickLaunch
  StrCmp $QUICKLAUNCH $TEMP +2
    CreateShortCut "$QUICKLAUNCH\${APPNAME}.lnk" "$INSTDIR\${APPKEY}.exe" "" "$INSTDIR\${APPKEY}.exe" 0
SectionEnd

; File associations section (optional, disabled by default)
Section /o "File Associations" SecFileAssoc
  ; This would register file type associations
  ; Currently disabled as the app doesn't have specific file types
  
  ; Example for .txt files (commented out)
  ; WriteRegStr HKCR ".txt" "backup_val" ""
  ; WriteRegStr HKCR ".txt" "" "${APPKEY}"
  ; WriteRegStr HKCR "${APPKEY}" "" "${APPNAME} Text File"
  ; WriteRegStr HKCR "${APPKEY}\DefaultIcon" "" "$INSTDIR\${APPKEY}.exe,0"
  ; WriteRegStr HKCR "${APPKEY}\shell" "" "open"
  ; WriteRegStr HKCR "${APPKEY}\shell\open" "" "Open with ${APPNAME}"
  ; WriteRegStr HKCR "${APPKEY}\shell\open\command" "" '"$INSTDIR\${APPKEY}.exe" "%1"'
SectionEnd

; Component descriptions
LangString DESC_SecCore ${LANG_ENGLISH} "Core application files (required)"
LangString DESC_SecDesktop ${LANG_ENGLISH} "Create a desktop shortcut for easy access"
LangString DESC_SecStartMenu ${LANG_ENGLISH} "Create Start Menu shortcuts"
LangString DESC_SecQuickLaunch ${LANG_ENGLISH} "Create Quick Launch shortcut (Windows 7 and earlier)"
LangString DESC_SecFileAssoc ${LANG_ENGLISH} "Associate file types with ${APPNAME}"

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} $(DESC_SecCore)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(DESC_SecDesktop)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecStartMenu} $(DESC_SecStartMenu)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecQuickLaunch} $(DESC_SecQuickLaunch)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecFileAssoc} $(DESC_SecFileAssoc)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Uninstaller section
Section "Uninstall"
  ; Kill application if running
  FindProcDLL::FindProc "${APPKEY}.exe"
  StrCmp $R0 1 0 +3
    MessageBox MB_YESNO|MB_ICONQUESTION "${APPNAME} is currently running. Close it now?" IDYES +2 IDNO uninstAbort
    Exec "taskkill /f /im ${APPKEY}.exe"
  
  ; Remove files
  Delete "$INSTDIR\${APPKEY}.exe"
  Delete "$INSTDIR\uninstall.exe"
  
  ; Remove additional files
  Delete "$INSTDIR\*.dll"
  
  ; Remove resources directory
  RMDir /r "$INSTDIR\resources"
  
  ; Remove shortcuts
  Delete "$DESKTOP\${APPNAME}.lnk"
  Delete "$QUICKLAUNCH\${APPNAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APPNAME}"
  
  ; Remove registry entries
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPKEY}"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\App Paths\${APPKEY}.exe"
  
  ; Remove file associations if they exist
  DeleteRegKey HKCR "${APPKEY}"
  
  ; Remove installation directory if empty
  RMDir "$INSTDIR"
  
  ; Remove any remaining registry entries for the application
  DeleteRegKey /ifempty HKLM "Software\${COMPANYNAME}"
  DeleteRegKey /ifempty HKCU "Software\${COMPANYNAME}"
  
  Goto uninstDone
  
  uninstAbort:
    MessageBox MB_OK "Uninstallation was cancelled."
    Abort
    
  uninstDone:
    MessageBox MB_OK "${APPNAME} has been successfully removed from your computer."
SectionEnd

; Functions
Function .onInstSuccess
  ; Launch application if user chooses to
  ; This is handled by the finish page
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove ${APPNAME} and all of its components?" IDYES +2
  Abort
FunctionEnd

Function un.onUninstSuccess
  ; Cleanup completed in the uninstaller section
FunctionEnd