import os
import sys
import glob

if len(sys.argv) < 3:
    print "Usage: package_windows_version.py <certificate.pfx> <password>"
    sys.exit(1)

code_signing_certificate = sys.argv[1]
code_signing_certificate_password = sys.argv[2]

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
os.system('C:\\Python27\\python.exe  .\\pyinstaller-2.0\\pyinstaller.py --icon MASSIVE.ico --windowed launcher.py')

#os.system('copy /Y MASSIVE.ico dist\\')
os.system('copy /Y MASSIVE.ico dist\\launcher\\')
#os.system('copy /Y C:\\Python27\\Lib\\site-packages\\wx-2.8-msw-unicode\\wx\\gdiplus.dll dist\\')
os.system('copy /Y C:\\Python27\\Lib\\site-packages\\wx-2.8-msw-unicode\\wx\\gdiplus.dll dist\\launcher\\')
#os.system('copy /Y sshwindows\\*.* dist\\')
os.system('copy /Y openssh-mls-software-6.2-p1-2\\*.* dist\\launcher\\')
#os.system('copy /Y GPL.txt dist\\')
os.system('copy /Y GPL.txt dist\\launcher\\')

import requests
cacert = requests.certs.where()
os.system('copy /Y ' + cacert + ' dist\\launcher\\')

os.system("signtool sign -f " + code_signing_certificate + " -p " + code_signing_certificate_password + " dist\launcher\*.exe")
os.system("signtool sign -f " + code_signing_certificate + " -p " + code_signing_certificate_password + " dist\launcher\*.dll")

# REM Is the filename of the manifest file safe to assume?

#os.system('copy /Y *.manifest dist\\Microsoft.VC90.CRT')
#os.chdir('dist\\Microsoft.VC90.CRT')
#os.system('rename ' + glob.glob('*manifest*')[0] + ' Microsoft.VC90.CRT.manifest')
#os.chdir('..\\..')

# Only one of these will work...
os.system(r""""C:\Program Files (x86)\Inno Setup 5\Compil32.exe" /cc .\\launcherWindowsSetupWizardScript.iss""")
os.system(r""""C:\Program Files\Inno Setup 5\Compil32.exe" /cc .\\launcherWindowsSetupWizardScript.iss""")
os.system("signtool sign -f " + code_signing_certificate + " -p " + code_signing_certificate_password + " C:\launcher_build\setup.exe")

