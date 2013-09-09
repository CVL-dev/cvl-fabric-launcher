import os
import sys
import tempfile
import commands
import subprocess

# James builds the DMG manually, by copying
# and pasting one block of commands at a time
# from the Launcher's Mac build page on the 
# CVL's public wiki:
# https://confluence-vre.its.monash.edu.au/display/CVL/MASSIVE-CVL+Launcher+Mac+OS+X+build+instructions

# This script is for automated builds, which
# currently do not support the nice-looking
# DMG background image and icon layout.
# When run in a script, some of the AppleScript
# commands seem to fail, so they are disabled
# by default.  When the DMG is built manually,
# these AppleScript commands are used to set
# the DMG's background image, and include a symbolic
# link to the Applications folder, making it easy
# to drag and drop the application icon into the 
# Applications folder.

# James's code-signing certificate:
APPLE_CODE_SIGNING_CERTIFICATE = "Developer ID Application: James Wettenhall"
# is hard-coded into the script for now. It is
# assumed that the certificate has already been
# installed in your Mac OS X Key Chain.  If you
# want to obtain your own Apple code-signing 
# certificate, you will probably need to pay
# $99 per year to join the Apple Developer Program.
# So far, I haven't had any luck with using a 
# generic (non-Apple) code-signing certificate.

INCLUDE_APPLICATIONS_SYMBOLIC_LINK = False
ATTEMPT_TO_SET_ICON_SIZE_IN_DMG = True
ATTEMPT_TO_LAY_OUT_ICONS_ON_DMG = False
ATTEMPT_TO_SET_BACKGROUND_IMAGE = False

if len(sys.argv) < 2:
    print "Usage: package_windows_version.py <version>"
    sys.exit(1)

version = sys.argv[1]

os.system('rm -fr build/*')
os.system('rm -fr dist/*')

# Build "MASSIVE Launcher.app"
os.system('python create_mac_bundle.py py2app')

# Digitally sign application:
os.environ['CODESIGN_ALLOCATE'] = '/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/usr/bin/codesign_allocate'
# The bundle identifier (au.edu.monash.MASSIVE) referenced below is set in create_mac_bundle.py:
os.system('codesign --force -i "au.edu.monash.MASSIVE" --sign "%s" --verbose=4 dist/MASSIVE\ Launcher.app' % (APPLE_CODE_SIGNING_CERTIFICATE))
os.system('codesign -vvvv dist/MASSIVE\ Launcher.app/')
os.system('spctl --assess --raw --type execute --verbose=4 dist/MASSIVE\ Launcher.app/')

# Build DMG (disk image) :

source = os.path.join(os.getcwd(),'dist')
applicationName = "MASSIVE Launcher"
title = applicationName + " " + version
size="80000"
finalDmgName = applicationName + " " + version

tempDmgFile=tempfile.NamedTemporaryFile(prefix=finalDmgName+"_",suffix=".dmg",delete=True)
tempDmgFileName=tempDmgFile.name
tempDmgFile.close()

backgroundPictureFileName = "dmgBackgroundMacOSX.png"

cmd = 'hdiutil create -srcfolder "%s" -volname "%s" -fs HFS+ -fsargs "-c c=64,a=16,e=16" -format UDRW -size %sk "%s"' % (source,title,size,tempDmgFileName)
print cmd
os.system(cmd)

cmd = "hdiutil attach -readwrite -noverify -noautoopen \"%s\" | egrep '^/dev/' | sed 1q | awk '{print $1}'" % (tempDmgFileName)
print cmd
device = commands.getoutput(cmd)

cmd = 'mkdir "/Volumes/%s/.background/"' % (title)
print cmd
os.system(cmd)

cmd = 'cp %s "/Volumes/%s/.background/"' % (backgroundPictureFileName,title)
print cmd
os.system(cmd)

if INCLUDE_APPLICATIONS_SYMBOLIC_LINK:
    cmd = 'ln -s /Applications/ "/Volumes/' + title + '/Applications"'
    print cmd
    os.system(cmd)

applescript = """
tell application "Finder"
     tell disk "%s"
           open
           set current view of container window to icon view
           set toolbar visible of container window to false
           set statusbar visible of container window to false
           set theViewOptions to the icon view options of container window
""" % (title)
if ATTEMPT_TO_SET_ICON_SIZE_IN_DMG:
    applescript = applescript + """
           set icon size of theViewOptions to 96
"""
if ATTEMPT_TO_LAY_OUT_ICONS_ON_DMG:
    applescript = applescript + """
           set the bounds of container window to {400, 100, 885, 430}
           set arrangement of theViewOptions to not arranged
           set file_list to every file
           repeat with file_object in file_list
               if the name of file_object ends with ".app" then
                   set the position of file_object to {120, 163}
               else if the name of file_object is "Applications" then
                   set the position of file_object to {375, 163}
               end if
           end repeat
"""
if ATTEMPT_TO_SET_BACKGROUND_IMAGE:
    applescript = applescript + """
           set background picture of theViewOptions to file ".background:'%s'"
""" % (backgroundPictureFileName)
applescript = applescript + """
           close
           open
           update without registering applications
     end tell
   end tell
"""
print applescript
tempAppleScriptFile=tempfile.NamedTemporaryFile(prefix=finalDmgName+"_",delete=False)
tempAppleScriptFileName=tempAppleScriptFile.name
tempAppleScriptFile.write(applescript.strip() + "\r\n")
tempAppleScriptFile.close()
proc = subprocess.Popen(['/usr/bin/osascript',tempAppleScriptFileName], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
stdout, stderr = proc.communicate()
print stderr
print stdout
os.unlink(tempAppleScriptFileName)

cmd = 'sleep 2'
print cmd
os.system(cmd)

cmd = 'chmod -Rf go-w /Volumes/"' + title + '"'
print cmd
os.system(cmd)

cmd = 'sync'
print cmd
os.system(cmd)

cmd = 'sync'
print cmd
os.system(cmd)

cmd = 'hdiutil detach ' + device
print cmd
os.system(cmd)

cmd = 'sleep 2'
print cmd
os.system(cmd)

cmd = 'rm -f "' + finalDmgName + '.dmg"'
print cmd
os.system(cmd)

cmd = 'hdiutil convert "%s" -format UDZO -imagekey zlib-level=9 -o "%s.dmg"' % (tempDmgFileName,finalDmgName)
print cmd
os.system(cmd)

cmd = 'rm -f ' + tempDmgFileName
print cmd
os.system(cmd)

cmd = 'ls -lh "%s.dmg"' % (finalDmgName)
print cmd
os.system(cmd)

