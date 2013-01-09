import os
import sys
import glob

os.system('del /Q dist\\*.*')

# PyInstaller should take care of the Manifests stuff.

#original_dir = os.getcwd()

#os.chdir('C:\\WINDOWS\\WinSxS')

#vc90_dirs = glob.glob('x86_Microsoft.VC90.CRT_*21022*')

#assert len(vc90_dirs) == 1

#os.chdir(original_dir)

#os.system('copy /Y C:\\WINDOWS\\WinSxS\\' + vc90_dirs[0] + '\\msvcp90.dll')
#os.system('copy /Y C:\\WINDOWS\\WinSxS\\Manifests\\' + vc90_dirs[0] + '.manifest')

#os.system('\\Python27\\python.exe create_windows_bundle.py py2exe')
os.system('C:\\Python27\\python.exe  .\\pyinstaller-2.0\\pyinstaller.py launcher.py')

#os.system('copy /Y MASSIVE.ico dist\\')
os.system('copy /Y MASSIVE.ico dist\\launcher\\')
#os.system('copy /Y C:\\Python27\\Lib\\site-packages\\wx-2.8-msw-unicode\\wx\\gdiplus.dll dist\\')
os.system('copy /Y C:\\Python27\\Lib\\site-packages\\wx-2.8-msw-unicode\\wx\\gdiplus.dll dist\\launcher\\')
#os.system('copy /Y sshwindows\\*.* dist\\')
os.system('copy /Y sshwindows\\*.* dist\\launcher\\')
#os.system('copy /Y GPL.txt dist\\')
os.system('copy /Y GPL.txt dist\\launcher\\')

import requests
cacert = requests.certs.where()
os.system('copy /Y ' + cacert + ' dist\\launcher\\')

# REM Is the filename of the manifest file safe to assume?

#os.system('copy /Y *.manifest dist\\Microsoft.VC90.CRT')
#os.chdir('dist\\Microsoft.VC90.CRT')
#os.system('rename ' + glob.glob('*manifest*')[0] + ' Microsoft.VC90.CRT.manifest')
#os.chdir('..\\..')

# Only one of these will work...
os.system(r""""C:\Program Files (x86)\Inno Setup 5\Compil32.exe" /cc .\\launcherWindowsSetupWizardScript.iss""")
os.system(r""""C:\Program Files\Inno Setup 5\Compil32.exe" /cc .\\launcherWindowsSetupWizardScript.iss""")

