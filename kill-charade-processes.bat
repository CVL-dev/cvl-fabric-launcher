FOR /F "usebackq tokens=2" %i IN (`tasklist ^| find str /r /b "charade.exe"`) DO taskkill /F /pid %i
