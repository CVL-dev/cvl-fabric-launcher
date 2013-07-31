"""
This test replicates the following manual test on the wiki. Note: run this after MassiveLogin02.sikuli

    Existing User
    An existing user should be able to see the desktop session start without issue 

    start desktop session with Launcher

and also:


"""

import credentials
import os
import time
import utils
import subprocess

def enter_passphrase():
    # The launcher is asking for the user's passphrase for their set up.
    
    if exists("1375054491467.png"):
        type(credentials.key_passphrase)
        click("1375055269866.png")
    
def enter_new_passphrase():
    # The user does not have a keypair set up, so enter a new
    # passphrase twice.
    
    if not exists("1375053099237.png"): return

    # first passphrase box
    click("1375053146098.png")
    type(credentials.key_passphrase)

    # second passphrase box
    click("1375053158238.png")
    type(credentials.key_passphrase)

    # click OK
    click("1375057516840.png")
 
def enter_massive_password():
    # The launcher is asking for the user's Massive password.
    if not exists("1375053312016.png"): return
    click("1375053324786.png")
    type(credentials.massive_password)
    click("1375055371442.png")
    
def got_massive_desktop():
    # Returns True if we can see the normal background image
    # for the Massive desktop.
    return exists("1375056072857.png")

def close_and_stop_massive_desktop():
    # Close the VNC window and stop the Massive desktop.

    # Click the red X in TurboVNC's toolbar.
    click("1375056232779.png")

    # Wait for the message "Would you like to leave your current session running..."
    wait("1375056254310.png", 15)

    # Click on "Stop the desktop"
    click("1375056261911.png")


#######################################

# Nuke charade/pageant
utils.kill_pageant_and_charade()

# Delete ~/.ssh on the server
# Can't for the life of me get trilead-ssh2 to work with Jython, so for the moment
# just using a hacky script that calls the normal CPython implementation:
os.popen(r'"C:\Python27\python.exe delete_dot_ssh.py" ' + credentials.massive_username + ' ' + credentials.massive_password)

# Start the Launcher
os.popen(r'"C:\Program Files\MASSIVE Launcher\launcher.exe"')
sleep(2)
wait("1375057960522.png")

# Enter the username:
click("1375053541177.png")
for _ in range(20):
    type(Key.BACKSPACE)
    type(Key.DELETE)
type(credentials.massive_username)

# Set the resolution:
click("1375056373131.png")
type("640x480")

# Click the Login button:
click("1375052919246.png")

# Try to enter various passphrases or credentials.
# TODO: tidy up this loop, make note of what happened, etc.
for _ in range(5):
    time.sleep(1)
    enter_new_passphrase()
    enter_massive_password()
    enter_passphrase()

# Wait for the Massive desktop.
found = False
for i in range(30):
    time.sleep(1)
    print "waiting for massive desktop...", i
    if got_massive_desktop():
        found = True
        break

print 'result:', found
    
if found:
    close_and_stop_massive_desktop()    
 
utils.kill_launcher()

# Finally, check that a valid keypair exists on Massive.
stdout, stderr = subprocess.Popen(['C:\\Python27\\python.exe',  "c:\cvl-fabric-launcher-sikuli\sikuli-tests\check_massive_keypair.py", 'm2.massive.org.au', credentials.massive_username, credentials.massive_password], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
stdout = str(stdout)
stderr = str(stderr)

if stderr != '':
    print 'Error with massive key:', stderr
else:
    print 'success? :-)'




