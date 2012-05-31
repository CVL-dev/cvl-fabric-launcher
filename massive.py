# massive.py

import wx
import pexpect
import getpass
import time
import sys
import traceback
from threading import *
import os

defaulthost = "m2.massive.org.au"

host = ""
project = ""
hours = ""
username = ""
password = ""

class MyFrame(wx.Frame):

    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title, size=(305, 310))

        self.menu_bar  = wx.MenuBar()
        self.help_menu = wx.Menu()
        self.help_menu.Append(wx.ID_ABOUT,   "&About MASSIVE")
        #self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.menu_bar.Append(self.help_menu, "&Help")

        self.SetMenuBar(self.menu_bar)

        # Let's implement the About menu using py2app instead,
        # so that we can easily insert the version number.

        panel = wx.Panel(self)

        wx.StaticText(panel, -1, 'MASSIVE host', (10, 20))
        wx.StaticText(panel, -1, 'MASSIVE project', (10, 60))
        wx.StaticText(panel, -1, 'Hours requested', (10, 100))
        wx.StaticText(panel, -1, 'Username', (10, 140))
        wx.StaticText(panel, -1, 'Password', (10, 180))

        self.massiveHost = wx.TextCtrl(panel, -1, defaulthost,  (125, 15), size=(145, -1))
        projects = ['', 'Monash016', 'Desc002']
        self.massiveProject = wx.ComboBox(panel, -1, value='', pos=(125, 55), size=(160, -1),choices=projects, style=wx.CB_DROPDOWN)
        self.massiveHours = wx.SpinCtrl(panel, -1, value='4', pos=(123, 95), size=(160, -1),min=1,max=24)
        self.massiveUsername = wx.TextCtrl(panel, -1, '',  (125, 135), (145, -1))
        self.massivePassword = wx.TextCtrl(panel, -1, '',  (125, 175), (145, -1), style=wx.TE_PASSWORD)

        self.massiveHours.MoveAfterInTabOrder(self.massiveProject)
        self.massiveUsername.MoveAfterInTabOrder(self.massiveHours)
        self.massivePassword.MoveAfterInTabOrder(self.massiveUsername)

        cancelButton = wx.Button(panel, 1, 'Cancel', (35, 225))
        loginButton = wx.Button(panel, 2, 'Login', (145, 225))
        loginButton.SetDefault()

        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=1)
        self.Bind(wx.EVT_BUTTON, self.OnLogin, id=2)

        self.statusbar = MyStatusBar(self)
        self.SetStatusBar(self.statusbar)
        self.Centre()

    def OnAbout(self, event):
        dlg = wx.MessageDialog(self, "Version 0.0.1\n",
                                "MASSIVE Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCancel(self, event):
        sys.exit()

    def OnLogin(self, event):
        class LoginThread(Thread):
            """Login Thread Class."""
            def __init__(self, notify_window):
                """Init Worker Thread Class."""
                Thread.__init__(self)
                self._notify_window = notify_window
                self._want_abort = 0
                # This starts the thread running on creation, but you could
                # also make the GUI thread responsible for calling this
                self.start()

            def run(self):
                """Run Worker Thread."""
                # This is the time-consuming code executing in the new thread. 

                qsubcmd = "qsub -A " + project + " -I -q vis -l walltime=" + hours + ":0:0,nodes=1:ppn=12:gpus=2,pmem=16000MB"
                vnc = "/opt/TurboVNC/bin/vncviewer"

                try:
                    wx.CallAfter(sys.stdout.write, " Attempting to log in to " + host + "...\n")

                    child1 = pexpect.spawn("ssh "+username+"@"+host, timeout=20)
                    ssh_newkey = "Are you sure you want to continue connecting"
                    count = 0
                    shouldWaitForLoginAcknowledgement = True
                    while shouldWaitForLoginAcknowledgement:
                        i = child1.expect ([ssh_newkey,'password:',pexpect.EOF,pexpect.TIMEOUT],1)
                        if i==0:
                            child1.sendline("yes")        
                            i=child1.expect([ssh_newkey,'password:',pexpect.EOF])
                            shouldWaitForLoginAcknowledgement = True
                        elif i==1:
                            child1.sendline (password)
                            shouldWaitForLoginAcknowledgement = False
                        elif i==2:
                            wx.CallAfter(sys.stdout.write, " EOF encountered while trying to log in.\n")
                            shouldWaitForLoginAcknowledgement = False
                        elif i==3:
                            if count<5:
                                count +=1
                                time.sleep(1)
                            else:
                                wx.CallAfter(sys.stdout.write, " Login timed out.\n")
                                shouldWaitForLoginAcknowledgement = False

                    wx.CallAfter(sys.stdout.write, " First login done.\n")

                    child1.sendline("mybalance --hours")
                    child1.expect("Project")
                    wx.CallAfter(sys.stdout.write, "\n mybalance --hours\n Project ")
                    wx.CallAfter(sys.stdout.write, child1.readline().strip() + "\n")
                    wx.CallAfter(sys.stdout.write, " " + child1.readline().strip() + "\n")
                    wx.CallAfter(sys.stdout.write, " " + child1.readline().strip() + "\n")

                    #time.sleep(10)
                    wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(sys.stdout.write, " " + qsubcmd + "\n")
                    wx.CallAfter(sys.stdout.write, "\n")
                    child1.sendline(qsubcmd)

                    shouldWaitForQsubAcknowledgement = True
                    while shouldWaitForQsubAcknowledgement:
                        i = child1.expect (["qsub: waiting for job ",pexpect.EOF,pexpect.TIMEOUT],1)
                        if i==0:
                            shouldWaitForQsubAcknowledgement = False
                            restOfLine = child1.readline()
                            restOfLineStringSplit = restOfLine.split(" ")
                            jobNumberAndNode = restOfLineStringSplit[0]
                            jobNumberAndNodeStringSplit = jobNumberAndNode.split(".")
                            jobNumber = jobNumberAndNodeStringSplit[0]
                            wx.CallAfter(sys.stdout.write, " qsub: waiting for job " + restOfLine)

                    #wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(sys.stdout.write, " *")
                    for i in range(1,9):
                        time.sleep(1)
                        wx.CallAfter(sys.stdout.write, "*")

                    shouldWaitForNode = True
                    while shouldWaitForNode:
                        i = child1.expect ([" Starting XServer on the following nodes...",pexpect.EOF,pexpect.TIMEOUT],timeout=1)
                        #wx.CallAfter(sys.stdout.write, child1.before)
                        if i==0:
                            shouldWaitForNode = False
                            child1.readline()
                            # grab the visnode and strip the white space at the start and at the end
                            visnode = child1.readline().strip()
                            break
                        elif i==1:
                            break
                        elif i==2:
                            time.sleep(1)
                            wx.CallAfter(sys.stdout.write, "*")

                    wx.CallAfter(sys.stdout.write, "\n\n")

                    wx.CallAfter(sys.stdout.write, " Massive Desktop visnode: " + visnode + "\n\n")

                    ###print child1.before
                    ###print child1.after

                    # Note that the use of system calls to "ps" etc. below is not portable to the Windows platform.
                    # An alternative could be to use the psutil module - see http://stackoverflow.com/questions/6780035/python-how-to-run-ps-cax-grep-something-in-python and http://code.google.com/p/psutil/, however it is difficult to install on my Mac (because I use a 32-bit Python for wxPython), due to this bug: http://bugs.python.org/issue13590.  A work around could be to install my 32-bit version Python from source to ensure that my local gcc version is used to build it.
                    # Probably a better way to check for use of port 5901 on Mac is to use: "lsof -i tcp:5901"
                    # On Unix systems with fuser installed, you can use: "fuser -v -n tcp 5901"
                    wx.CallAfter(sys.stdout.write, " Checking for and removing any existing ssh tunnel(s) using local port 5901...\n\n")
                    os.system("ps ax | grep \"5901\\:\" | grep ssh | awk '{print $1}' | xargs kill")

                    wx.CallAfter(sys.stdout.write, " Starting tunnelled ssh session...\n")
                    wx.CallAfter(sys.stdout.write, " ssh -N -L 5901:"+visnode+":5901 "+username+"@"+host+"\n\n")
                    ssh_tunnel = pexpect.spawn("ssh -N -L 5901:"+visnode+":5901 "+username+"@"+host, timeout=1)

                    ssh_newkey = "Are you sure you want to continue connecting"
                    shouldWaitForTunnelToBeSetup = True
                    count = 0
                    while shouldWaitForTunnelToBeSetup:
                        i = ssh_tunnel.expect ([ssh_newkey,'password:',"Could not request local forwarding.",pexpect.EOF,pexpect.TIMEOUT],1)
                        if i==0:
                            ssh_tunnel.sendline("yes")        
                            i=ssh_tunnel.expect([ssh_newkey,'password:',pexpect.EOF,pexpect.TIMEOUT])
                        elif i==1:
                            ssh_tunnel.sendline (password)
                            # Wait to see if any errors are returned from the SSH tunnel:
                            if count<5:
                                count += 1
                                time.sleep(1)
                            else:
                                shouldWaitForTunnelToBeSetup = False
                                break
                        elif i==2:
                            raise Exception(" " + ssh_tunnel.before + "\n" + 
                                                " " + ssh_tunnel.readline())
                        elif i==3:
                            break
                        elif i==4:
                            break

                    wx.CallAfter(sys.stdout.write, "\n Checking for TurboVNC...\n")
                    if os.path.exists(vnc):
                        wx.CallAfter(sys.stdout.write, " TurboVNC was found in " + vnc + "\n")
                    else:
                        wx.CallAfter(sys.stdout.write, " Error: TurboVNC was not found in " + vnc + "\n")

                    wx.CallAfter(sys.stdout.write, "\n Starting MASSIVE VNC...\n")

                    wx.CallAfter(sys.stdout.write, " " + vnc + " -user " + username + " localhost:1")
                    child2 = pexpect.spawn(vnc + " -user " + username + " localhost:1")
                    time.sleep(1)
                    child2.expect("Password:")
                    child2.sendline(password)

                    shouldWaitForMassiveDesktopVNCSessionToFinish = True
                    while shouldWaitForMassiveDesktopVNCSessionToFinish:
                        i = child2.expect ([pexpect.EOF,pexpect.TIMEOUT])
                        if i==0:
                            shouldWaitForMassiveDesktopVNCSessionToFinish = False
                        else:
                            time.sleep(1)

                    #child1.logout()
                    #self.statusbar.SetStatusText('User connected')
                    #self.statusbar.SetStatusText('')

                #except AttributeError:
                    #self.statusbar.SetForegroundColour(wx.RED)
                    #self.statusbar.SetStatusText('Incorrect params')

                #except all_errors, err:
                    #self.statusbar.SetStatusText(str(err))

                except:
                    #traceback.print_exc()
                    #print "Unexpected error:", sys.exc_info()[0]
                    sys.exc_info()

                # Example of using wx.PostEvent to post an event from a thread:
                #wx.PostEvent(self._notify_window, ResultEvent(10))

            def abort(self):
                """abort worker thread."""
                # Method for use by main thread to signal an abort
                self._want_abort = 1

        host = self.massiveHost.GetValue()
        project = self.massiveProject.GetValue()
        hours = str(self.massiveHours.GetValue())
        username = self.massiveUsername.GetValue()
        password = self.massivePassword.GetValue()

        logWindow = wx.Frame(self, title="MASSIVE Login", name="MASSIVE Login",pos=(200,150),size=(700,450))
        logWindow.Show(True)

        logTextCtrl = wx.TextCtrl(logWindow, style=wx.TE_MULTILINE|wx.TE_READONLY,size=(700,450))
        font1 = wx.Font(13, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        logTextCtrl.SetFont(font1)

        sys.stdout = logTextCtrl
        sys.stderr = logTextCtrl
        #print "Redirected STDOUT and STDERR to logTextCtrl"

        LoginThread(self)

class MyStatusBar(wx.StatusBar):
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent)

        self.SetFieldsCount(2)
        self.SetStatusText('Welcome to MASSIVE', 0)
        self.SetStatusWidths([-5, -2])
        #self.Bind(wx.EVT_SIZE, self.OnSize)

    #def PlaceIcon(self):
        #rect = self.GetFieldRect(1)
        #self.icon.SetPosition((rect.x+3, rect.y+3))

    #def OnSize(self, event):
        #self.PlaceIcon()

class MyApp(wx.App):
    def OnInit(self):
        frame = MyFrame(None, -1, 'MASSIVE')
        frame.Show(True)
        return True

app = MyApp(0)
app.MainLoop()

