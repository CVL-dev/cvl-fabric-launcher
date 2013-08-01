"""
This test basically replicates the following manual test on the wiki:

    Persistent Mode
    A user should be able to start a session in persistent mode and reconnect to the same session. When a user closes the session the should see a message about how much time they have remaining.
    
    start session with persistent mode checked
    open a terminal on the desktop (or any other program)
    close TurboVNC window and the time remaining is reported
    complete closure by acknowledging the message
    start a new session and verify that the user gets the same session (with the same programs open)
    Hit the exit button on the desktop and verify that the session shuts down (i.e. the TurboVNC session is terminated without needing to hit the exit button on the TurboVNC window)
    Example of message:
    
    ---------------------------
    MASSIVE/CVL Launcher
    ---------------------------
    MASSIVE job will not be deleted because persistent mode is active.
    Remaining walltime 4 hours 59 minutes.
    ---------------------------
    OK 
    ---------------------------

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

def reconnect_to_existing_desktop():
    if exists("1375231721279.png"):
        click("1375231730392.png")
        
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
    wait("1375231529101.png", 15)

    # Click on "Stop the desktop"
    click("1375056261911.png")

def close_and_leave_running_massive_desktop():
    # Close the VNC window and stop the Massive desktop.

    # Click the red X in TurboVNC's toolbar.
    click("1375056232779.png")

    # Wait for the message "Would you like to leave your current session running..."
    wait("1375231529101.png", 15)
    
    # Click on "Leave it running"
    click("1375231574147.png")
    
   

#######################################

for login_attempt in [0, 1]:
    # Kill any running launcher processes.
    utils.kill_launcher()
    
    # Nuke charade/pageant
    utils.kill_pageant_and_charade()
    
    # Start the Launcher
    os.popen(r'"C:\Program Files\MASSIVE Launcher\launcher.exe"') # have to run an installed binary, otherwise all kinds of files can't be found
    sleep(2)
    
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
    success = False
    for _ in range(120*10):
        time.sleep(0.1)
        enter_new_passphrase()
        enter_massive_password()
        enter_passphrase()
        if login_attempt == 0:
            kill_existing_desktop()
        else:
            reconnect_to_existing_desktop()
        if got_massive_desktop():
            success = True
            
            if login_attempt == 0:
                click("1375233743527.png")
                time.sleep(1) # wait for the terminal to appear; should use a wait() on the prompt?
                type('echo "hey there"\n')
                time.sleep(1) # necessary?
                click("1375234005964.png") # minimise the terminal
                close_and_leave_running_massive_desktop()
            else:
                click("1375234066102.png")
                wait("1375234127330.png")
                click("1375234140259.png")
                close_and_stop_massive_desktop()
            break

    assert success
            
