import credentials
import os
import time
import utils
import subprocess

sys.path.append(r"c:\cvl-fabric-launcher-sikuli\sikuli-tests")
import utils

def set_private_pc():
    if exists("1375141803291.png"):
        click("1375141816540.png")

def first_time_help():
    if exists("1375142069627.png"):
        click("1375142076539.png")

        wait("1375142189042.png")
        click("1375142196251.png")
    
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

def kill_existing_desktop():
    if exists("1375148394073.png"):
        click("1375148401805.png")

def do_not_submit_error_log():
    if exists("1375148463755.png"):
        click("1375148470935.png")
        return True

def submit_error_log():
    if exists("1375148463755.png"):
        click("1375148511515.png")
        return True
        
def close_and_stop_massive_desktop():
    # Close the VNC window and stop the Massive desktop.

    # Click the red X in TurboVNC's toolbar.
    click("1375056232779.png")

    # Wait for the message "Would you like to leave your current session running..."
    wait("1375056254310.png", 15)

    # Click on "Stop the desktop"
    click("1375056261911.png")


#######################################

# Kill any running launcher processes.
utils.kill_launcher()

DELETE_LOCAL_CONFIG = True

if DELETE_LOCAL_CONFIG:
    # Nuke the user's launcher config
    # print utils.delete_launcher_config()
    print 'delete_launcher_config...'

    username = os.path.split(os.path.expanduser('~'))[-1]

    import glob
    for file in glob.glob(r"\Documents and Settings\%s\Local Settings\Application Data\Monash University\MASSIVE Launcher\*.*" % (username,)):
        print file
        os.unlink(file)

# Nuke charade/pageant
utils.kill_pageant_and_charade()

# Delete ~/.ssh on the server
# Can't for the life of me get trilead-ssh2 to work with Jython, so for the moment
# just using a hacky script that calls the normal CPython implementation:
os.popen(r'C:\Python27\python.exe "c:\cvl-fabric-launcher-sikuli\sikuli-tests\delete_dot_ssh.py" ' + credentials.massive_username + ' ' + credentials.massive_password)

# Start the Launcher
os.popen(r'"C:\Program Files\MASSIVE Launcher\launcher.exe"')
sleep(2)

# FIXME tidy up this kind of loop
for _ in range(4):
    set_private_pc()
    first_time_help()

# Now the launcher should be ready.
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
click("login_button.png")

# Try to enter various passphrases or credentials.
# TODO: tidy up this loop, make note of what happened, etc.
for _ in range(120*10):
    time.sleep(0.1)
    enter_new_passphrase()
    enter_massive_password()
    enter_passphrase()
    kill_existing_desktop()

    # Wait until we see "Waiting for the VNC server to start", then click cancel.
    if exists("waiting_for_the_vnc_server_to_start.png"):
        # Click Cancel
        click("progress_dialog_cancel_button.png")
        print 'Hit cancel on the progress dialog, should go check if the job is still running on Massive.'
    
    if do_not_submit_error_log():
        print 'clicking No on submit error log'
        break

print 'got here'
utils.kill_launcher()



