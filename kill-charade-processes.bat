@ECHO OFF
REM FOR /F "usebackq tokens=2" %i IN (`tasklist ^| find str /r /b "charade.exe"`) DO taskkill /F /pid %i
tasklist /FI "IMAGENAME eq charade.exe" 2>NUL | find /I /N "charade.exe">NUL
if "%ERRORLEVEL%"=="0" taskkill /f /im charade.exe
