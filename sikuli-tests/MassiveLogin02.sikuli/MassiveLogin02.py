"""
This test basically replicates the following manual test on the wiki:

    Launcher kills visnode jobs if the user hits cancel

    ssh to m2, run

    watch -n 1 "qstat -u username"

    to watch your queue.

    Run the launcher, connect to m2, and as soon as a job appears in the queue, hit cancel.

    The job should be canceled in a few seconds, and the logs should say something like:

    2013-07-26 10:00:31,053 - launcher - Logger - debug - 65 - DEBUG - loginProcessEvent: caught EVT_LOGINPROCESS_CANCEL 
    2013-07-26 10:00:31,053 - launcher - Logger - debug - 65 - DEBUG - loginProcessEvent: cancel: trying to stop the job on MASSIVE/CVL but since we are already in a cancel state, we will not try to be to graceful about it 
    2013-07-26 10:00:31,054 - launcher - Logger - debug - 65 - DEBUG - loginProcessEvent: cancel: attempting to format the stop command <'qdel -a {jobid}'> using parameters: {'username': u'carlo', 'hours': '4', 'jobidNumber': '6285727', 'vnc': '/opt/TurboVNC/bin/vncviewer', 'configName': u'm2-login2.massive.org.au', 'wallseconds': 14400, 'launcher_version_number': '0.4.3', 'jobid': '6285727.m2-m', 'project': u'Desc002', 'sshBinary': '/usr/bin/ssh', 'cipher': u'arcfour128', 'loginHost': u'm2-login2.massive.org.au', 'vncOptionsString': '-encodings "tight copyrect"', 'group': 'Desc004', 'nodes': '1', 'resolution': u'1024x768', 'turboVncFlavour': 'X11'} 
    2013-07-26 10:00:31,054 - launcher - Logger - debug - 65 - DEBUG - loginProcessEvent: cancel: formatted stopCmd: 'qdel -a 6285727.m2-m'


NOTE THAT WE BEGIN FROM AN EMPTY LOCAL CONFIG: no .ssh and no Massive Launcher configuration.

"""

import credentials
import os
import time
import utils
import subprocess

sys.path.append(r"c:\cvl-fabric-launcher-sikuli\sikuli-tests")
import utils

def set_private_pc():
    wait("1375141803291.png")
    click("1375141816540.png")

def first_time_help():
    wait("1375142069627.png")
    click("1375142076539.png")

    # wait("1375142189042.png")
    # click("1375142196251.png")
    
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
    utils.delete_launcher_config()

# Nuke charade/pageant
utils.kill_pageant_and_charade()

# Delete ~/.ssh on the server
# Can't for the life of me get trilead-ssh2 to work with Jython, so for the moment
# just using a hacky script that calls the normal CPython implementation:
os.popen(r'C:\Python27\python.exe "c:\cvl-fabric-launcher-sikuli\sikuli-tests\delete_dot_ssh.py" ' + ' m2.massive.org.au ' + credentials.massive_username + ' ' + credentials.massive_password)

# Start the Launcher
os.popen(r'"C:\Program Files\MASSIVE Launcher\launcher.exe"') # have to run an installed binary, otherwise all kinds of files can't be found
sleep(2)

if DELETE_LOCAL_CONFIG:
    set_private_pc()
    first_time_help()

# Now the launcher should be ready.
wait("1375057960522.png")

# Enter the username:
click("1375053541177.png")
for _ in range(10):
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

# Finally, check that the visnode job was canceled.
time.sleep(5) # give Massive time to cancel the visnode job
stdout, stderr = subprocess.Popen(['C:\\Python27\\python.exe',  "c:\cvl-fabric-launcher-sikuli\sikuli-tests\check_massive_no_visnode_jobs_running.py", 'm2.massive.org.au', credentials.massive_username, credentials.massive_password], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
stdout = str(stdout)
stderr = str(stderr)

if stderr != '':
    print 'Error, found visnode job running:', stderr
else:
    print 'success? :-)'




