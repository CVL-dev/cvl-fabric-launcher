del /Q dist\*.*

REM Is this path safe to assume?

copy /Y "C:\WINDOWS\WinSxS\x86_Microsoft.VC90.CRT_1fc8b3b9a1e18e3b_9.0.21022.8_x-ww_d08d0375\msvcp90.dll"

\Python27\python.exe create_windows_bundle.py py2exe

copy /Y MASSIVE.ico dist\
copy /Y C:\Python27\Lib\site-packages\wx-2.8-msw-unicode\wx\gdiplus.dll dist\
copy /Y sshwindows\*.* dist\
copy /Y GPL.txt dist\

REM Is the filename of the manifest file safe to assume?

cd dist\Microsoft.VC90.CRT
rename "x86_Microsoft.VC90.CRT_1fc8b3b9a1e18e3b_9.0.21022.8_x-ww_d08d0375.manifest" Microsoft.VC90.CRT.manifest
cd ..\..

"C:\Program Files\Inno Setup 5\Compil32.exe" /cc launcherWindowsSetupWizardScript.iss

