del /Q dist\*.*

copy ..\msvcp90.dll

\Python27\python.exe create_windows_bundle.py py2exe

copy ..\MASSIVE.ico dist\
copy ..\msvcp90.dll dist\
copy C:\Python27\Lib\site-packages\wx-2.8-msw-unicode\wx\gdiplus.dll dist\
copy sshwindows\*.* dist\
copy GPL.txt dist\

