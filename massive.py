# massive.py
"""
A wxPython GUI to provide easy login to the MASSIVE Desktop, 
initially on Mac OS X.  It can be run using "python massive.py",
assuming that you have a 32-bit version of Python installed,
wxPython, and the pexpect module.

The py2app module is required to build the MASSIVE.app 
application bundle, which can be built as follows:

   python create_massive_bundle.py py2app
  
ACKNOWLEDGEMENT

Thanks to Michael Eager for a concise, non-GUI Python script
which demonstrated the use of the Python pexpect module to 
automate SSH logins and to automate calling TurboVNC.  This
wxPython version aims to be more user-friendly, particularly on 
Mac OS X and Windows, and aims to be develop a sophisticated
knowledge of things which can wrong when attempting to launch
the MASSIVE Desktop, e.g. an SSH Tunnel is already open on 
Port 5901, and to provide an appropriate balance between
resolving problems automatically for the user and reporting
them to the user as clearly as possible.
 
"""

import sys
if sys.platform.startswith("win"):
    import _winreg
    #import winpexpect
    import subprocess
else:
    import pexpect
import wx
#import getpass
import time
import traceback
import threading
#from threading import *
import os
import ssh
import HTMLParser
import urllib
import massive_launcher_version_number
import StringIO
import forward
#import logging

#logger = ssh.util.logging.getLogger()
#logger.setLevel(logging.WARN)

defaulthost = "m2.massive.org.au"

host = ""
project = ""
hours = ""
username = ""
password = ""

class MyHtmlParser(HTMLParser.HTMLParser):
  def __init__(self):
    HTMLParser.HTMLParser.__init__(self)
    self.recording = 0
    self.data = []

  def handle_starttag(self, tag, attributes):
    if tag != 'span':
      return
    if self.recording:
      self.recording += 1
      return
    for name, value in attributes:
      if name == 'id' and value == 'MassiveLauncherLatestVersionNumber':
        break
    else:
      return
    self.recording = 1

  def handle_endtag(self, tag):
    if tag == 'span' and self.recording:
      self.recording -= 1

  def handle_data(self, data):
    if self.recording:
      self.data.append(data)

class MyFrame(wx.Frame):

    def __init__(self, parent, id, title):

        global logTextCtrl

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

        myHtmlParser = MyHtmlParser()
        feed = urllib.urlopen("https://mnhs-massive-dev.med.monash.edu/index.php?option=com_content&view=article&id=121")
        html = feed.read()
        myHtmlParser.feed(html)
        myHtmlParser.close()

        latestVersion = myHtmlParser.data[0].strip()

        if latestVersion!=massive_launcher_version_number.version_number:
            dlg = wx.MessageDialog(self, 
                "You are running version " + massive_launcher_version_number.version_number + "\n\n" +
                "The latest version is " + myHtmlParser.data[0] + "\n\n" +
                "Please download a new version from:\n\nhttps://mnhs-massive-dev.med.monash.edu/index.php?option=com_content&view=article&id=121\n\n" +
                "For queries, please contact:\n\nhelp@massive.org.au\njames.wettenhall@monash.edu\n",
                "MASSIVE Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            sys.exit(1)
 
    def OnAbout(self, event):
        dlg = wx.MessageDialog(self, "Version " + massive_launcher_version_number.version_number + "\n",
                                "MASSIVE Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCancel(self, event):
        sys.exit()

    def OnLogin(self, event):
        class LoginThread(threading.Thread):
            """Login Thread Class."""
            def __init__(self, notify_window):
                """Init Worker Thread Class."""
                threading.Thread.__init__(self)
                self._notify_window = notify_window
                self._want_abort = 0
                # This starts the thread running on creation, but you could
                # also make the GUI thread responsible for calling this
                self.start()

            def run(self):
                """Run Worker Thread."""
                # This is the time-consuming code executing in the new thread. 

                global logTextCtrl

                try:
                    wx.CallAfter(sys.stdout.write, "Attempting to log in to " + host + "...\n")
                    
                    sshClient = ssh.SSHClient()
                    sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())
                    sshClient.connect(host,username=username,password=password)

                    stdin,stdout,stderr = sshClient.exec_command("uptime")
                    wx.CallAfter(sys.stdout.write, stderr.read())
                    wx.CallAfter(sys.stdout.write, "uptime: " + stdout.read())

                    wx.CallAfter(sys.stdout.write, "First login done.\n")

                    wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(sys.stdout.write, "mybalance --hours\n")
                    stdin,stdout,stderr = sshClient.exec_command("mybalance --hours")
                    wx.CallAfter(sys.stdout.write, stderr.read())
                    wx.CallAfter(sys.stdout.write, stdout.read())

                    wx.CallAfter(sys.stdout.write, "\n")

                    qsubcmd = "qsub -A " + project + " -I -q vis -l walltime=" + hours + ":0:0,nodes=1:ppn=12:gpus=2,pmem=16000MB"

                    wx.CallAfter(sys.stdout.write, qsubcmd + "\n")
                    wx.CallAfter(sys.stdout.write, "\n")
                  
                    # An ssh channel can be used to execute a command, 
                    # and you can use it in a select statement to find out when data can be read.
                    # The channel object can be read from and written to, connecting with 
                    # stdout and stdin of the remote command. You can get at stderr by calling 
                    # channel.makefile_stderr(...).

                    transport = sshClient.get_transport()
                    channel = transport.open_session()
                    channel.get_pty()
                    channel.setblocking(0)
                    channel.invoke_shell()
                    out = ""
                    channel.send(qsubcmd + "\n")

                    # From: http://www.lag.net/paramiko/docs/paramiko.Channel-class.html#recv_stderr_ready
                    # "Only channels using exec_command or invoke_shell without a pty 
                    #  will ever have data on the stderr stream."

                    lineNumber = 0
                    startingXServerLineNumber = -1
                    breakOutOfMainLoop = False
                    lineFragment = ""

                    while True:
                        tCheck = 0
                        while not channel.recv_ready() and not channel.recv_stderr_ready():
                            #wx.CallAfter(sys.stdout.write, "*")
                            time.sleep(1)
                            tCheck+=1
                            if tCheck >= 10:
                                #wx.CallAfter(sys.stdout.write, "Read time out?\n") # TODO: add exception here
                                # return False
                                break
                        if (channel.recv_stderr_ready()):
                            out = channel.recv_stderr(1024)
                            buff = StringIO.StringIO(out)
                            line = lineFragment + buff.readline()
                            while line != "":
                                wx.CallAfter(sys.stdout.write, "ERROR: " + line)
                        if (channel.recv_ready()):
                            out = channel.recv(1024)
                            buff = StringIO.StringIO(out)
                            line = lineFragment + buff.readline()
                            while line != "":
                                lineNumber += 1
                                if not line.endswith("\n") and not line.endswith("\r"):
                                    lineFragment = line
                                    break
                                else:
                                    lineFragment = ""
                                if "waiting for job" in line:
                                    wx.CallAfter(sys.stdout.write, line)
                                if "Starting XServer on the following nodes" in line:
                                    startingXServerLineNumber = lineNumber
                                if lineNumber == (startingXServerLineNumber + 1): # vis node
                                    visnode = line.strip()
                                    breakOutOfMainLoop = True
                                line = buff.readline()
                        if breakOutOfMainLoop:
                            break

                    wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(sys.stdout.write, "Massive Desktop visnode: " + visnode + "\n\n")

                    # Note that the use of system calls to "ps" etc. below is not portable to the Windows platform.
                    # An alternative could be to use the psutil module - see http://stackoverflow.com/questions/6780035/python-how-to-run-ps-cax-grep-something-in-python and http://code.google.com/p/psutil/.
                    # Probably a better way to check for use of port 5901 on Mac is to use: "lsof -i tcp:5901"
                    # On Unix systems with fuser installed, you can use: "fuser -v -n tcp 5901"

                    # We can use sys.platform to check the OS.  
                    # Typical return values include 'darwin' (Mac OS X), 'win32', 'linux2', ...

                    if not sys.platform.startswith("win"):
                        wx.CallAfter(sys.stdout.write, "Checking for and removing any existing ssh tunnel(s) using local port 5901...\n\n")
                        os.system("ps ax | grep \"5901\\:\" | grep ssh | awk '{print $1}' | xargs kill")

                    def createTunnel():
                        wx.CallAfter(sys.stdout.write, "Starting tunnelled ssh session...\n")
                        wx.CallAfter(sys.stdout.write, "ssh -N -L 5901:"+visnode+":5901 "+username+"@"+host+"\n\n")

                        try:
                            forward.forward_tunnel(5901, visnode, 5901, sshClient.get_transport())
                            wx.CallAfter(sys.stdout.write, "Now forwarding port %d to %s:%d ...\n" % (5901, visnode, 5901))
                        except KeyboardInterrupt:
                            wx.CallAfter(sys.stdout.write, "C-c: Port forwarding stopped.")
                            ###sys.exit(0)

                    tunnelThread = threading.Thread(target=createTunnel)
                    tunnelThread.start()
                    time.sleep(2)

                    vnc = "/opt/TurboVNC/bin/vncviewer"
                    if sys.platform.startswith("win"):
                        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_ALL_ACCESS)
                        queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                        vnc = os.path.join(queryResult[0], "vncviewer.exe")
                    #wx.CallAfter(sys.stdout.write, "\nChecking for TurboVNC...\n")
                    if os.path.exists(vnc):
                        wx.CallAfter(sys.stdout.write, "TurboVNC was found in " + vnc + "\n")
                    else:
                        wx.CallAfter(sys.stdout.write, "Error: TurboVNC was not found in " + vnc + "\n")

                    wx.CallAfter(sys.stdout.write, "\nStarting MASSIVE VNC...\n")

                    #####wx.CallAfter(sys.stdout.write, vnc + " -user " + username + " localhost:1")
                    #####proc = subprocess.Popen(vnc+" -user "+username+" localhost:1", 
                        #####stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                        #####close_fds=True,universal_newlines=True)
                    #####output = proc.communicate()[0]
                    #####wx.CallAfter(sys.stdout.write, output)
                    #####time.sleep(1)
                    #####output = proc.communicate(input=password + "\n")[0]
                    #####wx.CallAfter(sys.stdout.write, output)
                    #####time.sleep(1)

                    try:
                        if sys.platform.startswith("win"):
                            #child = winpexpect.winspawn("\"" + vnc + "\" -user " + username + " localhost:1")
                            wx.CallAfter(sys.stdout.write, "\"" + vnc + "\" /user " + username + " /password " + password + " localhost:1")
                            subprocess.call("\"" + vnc + "\" /user " + username + " /password " + password + " localhost:1",shell=True)
                        else:
                            wx.CallAfter(sys.stdout.write, "Spawing TurboVNC process, using pexpect...\n")
                            child = pexpect.spawn(vnc + " -user " + username + " localhost:1")
                            wx.CallAfter(sys.stdout.write, "Spawned TurboVNC process: " + vnc + " -user " + username + " localhost:1\n")
                        time.sleep(1)
                        child.expect("Password:")
                        child.sendline(password)
                    except BaseException, err:
                        wx.CallAfter(sys.stdout.write,str(err))

                    #wx.CallAfter(sys.stdout.write, child1.before)
                    #wx.CallAfter(sys.stdout.write, child1.after)

                    shouldWaitForMassiveDesktopVNCSessionToFinish = True
                    while shouldWaitForMassiveDesktopVNCSessionToFinish:
                        i = child.expect ([pexpect.EOF,pexpect.TIMEOUT])
                        if i==0:
                            shouldWaitForMassiveDesktopVNCSessionToFinish = False
                        else:
                            time.sleep(1)

                    sshClient.close()

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

