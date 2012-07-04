# massive.py
"""
A wxPython GUI to provide easy login to the MASSIVE Desktop, 
initially on Mac OS X.  It can be run using "python massive.py",
assuming that you have a 32-bit version of Python installed,
wxPython, and the dependent Python modules imported below.

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
import subprocess
import wx
import time
import traceback
import threading
import os
import ssh
import HTMLParser
import urllib
import massive_launcher_version_number
import StringIO
import forward
import xmlrpclib
import appdirs
import ConfigParser
#import logging

#logger = ssh.util.logging.getLogger()
#logger.setLevel(logging.WARN)

#defaultHost = "m2.massive.org.au"
defaultHost = "m2-login2.massive.org.au"

host = ""
project = ""
hours = ""
global username
global loginDialogFrame
loginDialogFrame = None
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

        # The default window style is wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX | wx.RESIZE_BORDER | wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX | wx.CLIP_CHILDREN
        # If you remove wx.RESIZE_BORDER from it, you'll get a frame which cannot be resized.
        # wx.Frame(parent, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        if sys.platform.startswith("darwin"):
            wx.Frame.__init__(self, parent, id, title, size=(350, 310), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        else:
            wx.Frame.__init__(self, parent, id, title, size=(350, 350), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        self.menu_bar  = wx.MenuBar()

        if sys.platform.startswith("win") or sys.platform.startswith("linux"):
            self.file_menu = wx.Menu()
            self.file_menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Close window and exit program.")
            self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
            self.menu_bar.Append(self.file_menu, "&File")

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.help_menu = wx.Menu()
        self.help_menu.Append(wx.ID_ABOUT,   "&About MASSIVE Launcher")
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.menu_bar.Append(self.help_menu, "&Help")

        self.SetTitle("MASSIVE Launcher")

        self.SetMenuBar(self.menu_bar)

        # Let's implement the About menu using py2app instead,
        # so that we can easily insert the version number.
        # We may need to treat different OS's differently.

        global loginDialogPanel
        loginDialogPanel = wx.Panel(self)

        global massiveHostLabel
        massiveHostLabel = wx.StaticText(loginDialogPanel, -1, 'MASSIVE host', (10, 20))
        global massiveProjectLabel
        massiveProjectLabel = wx.StaticText(loginDialogPanel, -1, 'MASSIVE project', (10, 60))
        global massiveHoursLabel
        massiveHoursLabel = wx.StaticText(loginDialogPanel, -1, 'Hours requested', (10, 100))
        global massiveUsernameLabel
        massiveUsernameLabel = wx.StaticText(loginDialogPanel, -1, 'Username', (10, 140))
        global massivePasswordLabel
        massivePasswordLabel = wx.StaticText(loginDialogPanel, -1, 'Password', (10, 180))

        widgetWidth1 = 180
        widgetWidth2 = 180
        if not sys.platform.startswith("win"):
            widgetWidth2 = widgetWidth2 + 25

        massiveHosts = ["m1-login1.massive.org.au", "m1-login2.massive.org.au",
            "m2-login1.massive.org.au", "m2-login2.massive.org.au"]
        global massiveHostComboBox
        massiveHostComboBox = wx.ComboBox(loginDialogPanel, -1, value=defaultHost, pos=(125, 15), size=(widgetWidth2, -1),choices=massiveHosts, style=wx.CB_DROPDOWN)

        global defaultProjectPlaceholder
        defaultProjectPlaceholder = '[Use my default project]';
        projects = [
            defaultProjectPlaceholder,
            'ASync001','ASync002','ASync003','ASync004','ASync005','ASync006',
            'ASync007','ASync008','ASync009','ASync010','ASync011','CSIRO001',
            'CSIRO002','CSIRO003','CSIRO004','CSIRO005','CSIRO006','CSIRO007',
            'Desc001','Desc002','Desc003','Monash001','Monash002','Monash003',
            'Monash004','Monash005','Monash006','Monash007','Monash008',
            'Monash009','Monash010','Monash011','Monash012','Monash013',
            'Monash014','Monash015','Monash016','Monash017','Monash018',
            'Monash019','Monash020','Monash021','Monash022','Monash023',
            'Monash024','Monash025','Monash026','Monash027','Monash028',
            'Monash029','Monash030','Monash031','Monash032','Monash033',
            'Monash034','NCId75','NCIdb5','NCIdc0','NCIdd2','NCIg61','NCIg75',
            'NCIq97','NCIr14','NCIw25','NCIw27','NCIw67','NCIw81','NCIw91',
            'NCIy40','NCIy95','NCIy96','pDeak0023','pDeak0024','pDeak0026',
            'pLaTr0011','pMelb0095','pMelb0100','pMelb0103','pMelb0104',
            'pMOSP','pRMIT0074','pRMIT0078','pVPAC0005','Training'
            ]
        global massiveProjectComboBox
        massiveProjectComboBox = wx.ComboBox(loginDialogPanel, -1, value='', pos=(125, 55), size=(widgetWidth2, -1),choices=projects, style=wx.CB_DROPDOWN)
        global project
        if config.has_section("MASSIVE Launcher Preferences"):
            if config.has_option("MASSIVE Launcher Preferences", "project"):
                project = config.get("MASSIVE Launcher Preferences", "project")
            else:
                config.set("MASSIVE Launcher Preferences","project","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    config.write(massiveLauncherPreferencesFileObject)
        else:
            config.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                config.write(massiveLauncherPreferencesFileObject)
        if project.strip()!="":
            massiveProjectComboBox.SetValue(project)
        else:
            massiveProjectComboBox.SetValue(defaultProjectPlaceholder)

        global massiveHoursField
        massiveHoursField = wx.SpinCtrl(loginDialogPanel, -1, value='4', pos=(123, 95), size=(widgetWidth2, -1),min=1,max=24)

        global username
        if config.has_section("MASSIVE Launcher Preferences"):
            if config.has_option("MASSIVE Launcher Preferences", "username"):
                username = config.get("MASSIVE Launcher Preferences", "username")
            else:
                config.set("MASSIVE Launcher Preferences","username","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    config.write(massiveLauncherPreferencesFileObject)
        else:
            config.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                config.write(massiveLauncherPreferencesFileObject)
        global massiveUsernameTextField
        massiveUsernameTextField = wx.TextCtrl(loginDialogPanel, -1, username,  (125, 135), (widgetWidth1, -1))
        massiveUsernameTextField = massiveUsernameTextField
        if username.strip()!="":
            massiveUsernameTextField.SelectAll()

        global massivePasswordField
        massivePasswordField = wx.TextCtrl(loginDialogPanel, -1, '',  (125, 175), (widgetWidth1, -1), style=wx.TE_PASSWORD)

        massiveUsernameTextField.SetFocus()

        massiveHoursField.MoveAfterInTabOrder(massiveProjectComboBox)
        massiveUsernameTextField.MoveAfterInTabOrder(massiveHoursField)
        massivePasswordField.MoveAfterInTabOrder(massiveUsernameTextField)

        global cancelButton
        cancelButton = wx.Button(loginDialogPanel, 1, 'Cancel', (130, 225))
        global loginButton
        loginButton = wx.Button(loginDialogPanel, 2, 'Login', (230, 225))
        loginButton.SetDefault()

        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=1)
        self.Bind(wx.EVT_BUTTON, self.OnLogin, id=2)

        self.statusbar = MyStatusBar(self)
        global loginDialogStatusBar
        loginDialogStatusBar = self.statusbar
        self.SetStatusBar(self.statusbar)
        self.Centre()

        #massiveLauncherURL = "https://mnhs-massive-dev.med.monash.edu/index.php?option=com_content&view=article&id=121"
        massiveLauncherURL = "https://mnhs-web14-v02.med.monash.edu/index.php?option=com_content&view=article&id=121"

        try:
            myHtmlParser = MyHtmlParser()
            feed = urllib.urlopen(massiveLauncherURL)
            html = feed.read()
            myHtmlParser.feed(html)
            myHtmlParser.close()
        except:
            dlg = wx.MessageDialog(self, "Error: Unable to contact MASSIVE website to check version number.\n\n" +
                                        "The launcher cannot continue.\n",
                                "MASSIVE Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            sys.exit(1)


        latestVersion = myHtmlParser.data[0].strip()

        if latestVersion!=massive_launcher_version_number.version_number:
            newVersionAlertDialog = wx.Dialog(loginDialogFrame, title="MASSIVE Launcher", name="MASSIVE Launcher",pos=(200,150),size=(680,290))

            if sys.platform.startswith("win"):
                _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
                newVersionAlertDialog.SetIcon(_icon)

            if sys.platform.startswith("linux"):
                import MASSIVE_icon
                newVersionAlertDialog.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

            newVersionAlertDialogPanel = wx.Panel(newVersionAlertDialog)

            import MASSIVE_icon
            massiveIconAsBitmap = MASSIVE_icon.getMASSIVElogoTransparent128x128Bitmap()
            wx.StaticBitmap(newVersionAlertDialogPanel, -1, 
                massiveIconAsBitmap,
                (0, 50),
                (massiveIconAsBitmap.GetWidth(), massiveIconAsBitmap.GetHeight())) 

            newVersionAlertTitleLabel = wx.StaticText(newVersionAlertDialogPanel,
                label = "MASSIVE Launcher", pos=(125,30))
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetPointSize(14)
            font.SetWeight(wx.BOLD)
            newVersionAlertTitleLabel.SetFont(font)

            newVersionAlertTextLabel1 = wx.StaticText(newVersionAlertDialogPanel, 
                label = 
                "You are running version " + massive_launcher_version_number.version_number + "\n\n" +
                "The latest version is " + myHtmlParser.data[0] + "\n\n" +
                "Please download a new version from:\n\n",
                pos = (125,60))
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(9)
            newVersionAlertTextLabel1.SetFont(font)

            if sys.platform.startswith("darwin"):
                hyperlinkPos = (78,135)
            else:
                hyperlinkPos = (125,138)

            newVersionAlertHyperlink = wx.HyperlinkCtrl(newVersionAlertDialogPanel, 
                id = wx.ID_ANY,
                label = massiveLauncherURL,
                url = massiveLauncherURL,
                pos = hyperlinkPos)
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(8)
            newVersionAlertHyperlink.SetFont(font)

            newVersionAlertTextLabel2 = wx.StaticText(newVersionAlertDialogPanel, 
                label = 
                "For queries, please contact:\n\nhelp@massive.org.au\njames.wettenhall@monash.edu\n",
                pos = (125,160))
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(9)
            newVersionAlertTextLabel2.SetFont(font)

            def OnOK(event):
                sys.exit(1)

            okButton = wx.Button(newVersionAlertDialogPanel, 1, ' OK ', (570, 230))
            okButton.SetDefault()

            newVersionAlertDialog.Bind(wx.EVT_BUTTON, OnOK, id=1)

            # http://wxpython-users.1045709.n5.nabble.com/wx-Dialog-comes-up-blank-in-Windows-if-panel-is-not-sized-td2371532.html
            # A Panel doesn't automatically size to its parent Dialog on
            # Windows, and so ends up clipping all its contents.  On the Mac and in a
            # Frame, it either auto-resizes, or doesn't clip.

            # Robin Dunn:
            # The root of the problem is that dialogs on Windows do not get an initial
            # size event when they are shown (frames do) and since all the layout
            # magic happens in the EVT_SIZE handler then it doesn't happen by default
            # for the dialog.  You can work around this by doing something that will
            # change the size of the dialog after it has been created and populated
            # with child widgets (explicitly call SetSize, or do something like
            # sizer.Fit(), etc.) or calling SendSizeEvent will probably do it too. 
            newVersionAlertDialog.SetSize((680,290))
            newVersionAlertDialogPanel.SetSize((680,290))

            newVersionAlertDialog.ShowModal()
            newVersionAlertDialog.Destroy()

            #dlg = wx.MessageDialog(self, 
                #"You are running version " + massive_launcher_version_number.version_number + "\n\n" +
                #"The latest version is " + myHtmlParser.data[0] + "\n\n" +
                #"Please download a new version from:\n\n" +
                #massiveLauncherURL + "\n\n" +
                #"For queries, please contact:\n\nhelp@massive.org.au\njames.wettenhall@monash.edu\n",
                #"MASSIVE Launcher", wx.OK | wx.ICON_INFORMATION)
            #dlg.ShowModal()
            #dlg.Destroy()

            sys.exit(1)
 
    def OnAbout(self, event):
        dlg = wx.MessageDialog(self, "Version " + massive_launcher_version_number.version_number + "\n",
                                "MASSIVE Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def OnExit(self, event):
        os._exit(0)

    def OnCancel(self, event):
        os._exit(0)

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

                waitCursor = wx.StockCursor(wx.CURSOR_WAIT)
                loginDialogFrame.SetCursor(waitCursor)
                loginDialogPanel.SetCursor(waitCursor)
                massiveHostLabel.SetCursor(waitCursor)
                massiveProjectLabel.SetCursor(waitCursor)
                massiveHoursLabel.SetCursor(waitCursor)
                massiveUsernameLabel.SetCursor(waitCursor)
                massivePasswordLabel.SetCursor(waitCursor)
                massiveHostComboBox.SetCursor(waitCursor)
                massiveProjectComboBox.SetCursor(waitCursor)
                massiveHoursField.SetCursor(waitCursor)
                massiveUsernameTextField.SetCursor(waitCursor)
                massivePasswordField.SetCursor(waitCursor)
                cancelButton.SetCursor(waitCursor)
                loginButton.SetCursor(waitCursor)

                global logTextCtrl
                global loginDialogStatusBar

                try:
                    displaySize = wx.DisplaySize()
                    desiredWidth = displaySize[0] * 0.99
                    desiredHeight = displaySize[1] * 0.85

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Logging in to " + host)
                    wx.CallAfter(sys.stdout.write, "Attempting to log in to " + host + "...\n")
                    
                    sshClient = ssh.SSHClient()
                    sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())
                    sshClient.connect(host,username=username,password=password)

                    wx.CallAfter(sys.stdout.write, "First login done.\n")

                    wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Setting display resolution...")
                    stdin,stdout,stderr = sshClient.exec_command("if ! [ -f ~/.vnc/turbovncserver.conf ]; then cp /etc/turbovncserver.conf  ~/.vnc/; fi")
                    stderrRead = stderr.read()
                    if len(stderrRead) > 0:
                        wx.CallAfter(sys.stdout.write, stderrRead)
                    stdin,stdout,stderr = sshClient.exec_command("grep \"^\w*\$geometry\" ~/.vnc/turbovncserver.conf")
                    stderrRead = stderr.read()
                    stdoutRead = stdout.read()
                    if len(stdoutRead)>0 and stdoutRead.strip().startswith("$"):
                        sed_cmd = "sed -i -e 's/^\\w*\\$geometry.*/$geometry = \"%dx%d\";/g' ~/.vnc/turbovncserver.conf" % (desiredWidth,desiredHeight)
                        wx.CallAfter(sys.stdout.write, sed_cmd + "\n")
                        stdin,stdout,stderr = sshClient.exec_command(sed_cmd)
                        stderrRead = stderr.read()
                        if len(stderrRead) > 0:
                            wx.CallAfter(sys.stdout.write, stderrRead)
                    else:
                        wx.CallAfter(sys.stdout.write, "$geometry = ... was not found in ~/.vnc/turbovncserver.conf")
                        stdin,stdout,stderr = sshClient.exec_command(
                            "echo '$geometry = \"%dx%d\"' >> ~/.vnc/turbovncserver.conf" % (desiredWidth,desiredHeight))
                        stderrRead = stderr.read()
                        if len(stderrRead) > 0:
                            wx.CallAfter(sys.stdout.write, stderrRead)
                    
                    wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Checking quota...")

                    #wx.CallAfter(sys.stdout.write, "mybalance --hours\n")
                    stdin,stdout,stderr = sshClient.exec_command("mybalance --hours")
                    wx.CallAfter(sys.stdout.write, stderr.read())
                    wx.CallAfter(sys.stdout.write, stdout.read())

                    wx.CallAfter(sys.stdout.write, "\n")

                    #wx.CallAfter(sys.stdout.write, "echo `showq -w class:vis | grep \"processors in use by local jobs\" | awk '{print $1}'` of 10 nodes in use\n")
                    stdin,stdout,stderr = sshClient.exec_command("echo `showq -w class:vis | grep \"processors in use by local jobs\" | awk '{print $1}'` of 10 nodes in use")
                    wx.CallAfter(sys.stdout.write, stderr.read())
                    wx.CallAfter(sys.stdout.write, stdout.read())

                    wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Requesting remote desktop...")

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
                    checkedShowStart = False
                    jobNumber = "0.m2-m"

                    while True:
                        tCheck = 0
                        while not channel.recv_ready() and not channel.recv_stderr_ready():
                            #Use asterisks to simulate progress bar:
                            #wx.CallAfter(sys.stdout.write, "*")
                            time.sleep(1)
                            tCheck+=1
                            if tCheck >= 10:
                                # wx.CallAfter(sys.stdout.write, "Read time out?\n") # Throw exception here?
                                # return False
                                if (not checkedShowStart) and jobNumber!="0.m2-m":
                                    checkedShowStart = True
                                    def showStart():
                                        sshClient2 = ssh.SSHClient()
                                        sshClient2.set_missing_host_key_policy(ssh.AutoAddPolicy())
                                        sshClient2.connect(host,username=username,password=password)
                                        stdin,stdout,stderr = sshClient2.exec_command("showstart " + jobNumber)
                                        stderrRead = stderr.read()
                                        stdoutRead = stdout.read()
                                        if not "00:00:00" in stdoutRead:
                                            wx.CallAfter(sys.stdout.write, "showstart " + jobNumber + "...\n")
                                            wx.CallAfter(sys.stdout.write, stderrRead)
                                            wx.CallAfter(sys.stdout.write, stdoutRead)
                                        sshClient2.close()

                                    showStartThread = threading.Thread(target=showStart)
                                    showStartThread.start()
                                break
                        if (channel.recv_stderr_ready()):
                            out = channel.recv_stderr(1024)
                            buff = StringIO.StringIO(out)
                            line = lineFragment + buff.readline()
                            while line != "":
                                wx.CallAfter(sys.stdout.write, "ERROR: " + line + "\n")
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
                                    lineSplit = line.split(" ")
                                    jobNumber = lineSplit[4] # e.g. 3050965.m2-m
                                    jobNumberSplit = jobNumber.split(".")
                                    jobNumber = jobNumberSplit[0]
                                if "Starting XServer on the following nodes" in line:
                                    startingXServerLineNumber = lineNumber
                                if lineNumber == (startingXServerLineNumber + 1): # vis node
                                    visnode = line.strip()
                                    breakOutOfMainLoop = True
                                line = buff.readline()
                        if breakOutOfMainLoop:
                            break

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Acquired desktop node:" + visnode)

                    wx.CallAfter(sys.stdout.write, "Massive Desktop visnode: " + visnode + "\n\n")

                    # Note that the use of system calls to "ps" etc. below is not portable to the Windows platform.
                    # An alternative could be to use the psutil module - see http://stackoverflow.com/questions/6780035/python-how-to-run-ps-cax-grep-something-in-python and http://code.google.com/p/psutil/.
                    # Probably a better way to check for use of port 5901 on Mac is to use: "lsof -i tcp:5901"
                    # On Unix systems with fuser installed, you can use: "fuser -v -n tcp 5901"

                    # We can use sys.platform to check the OS.  
                    # Typical return values include 'darwin' (Mac OS X), 'win32', 'linux2', ...

                    if  sys.platform.startswith("win"):
                        wx.CallAfter(sys.stdout.write, "Warning: The Windows version of MASSIVE Launcher is currently not able to check for and remove existing SSH tunnel(s) using local port 5901...\n\n")
                    if not sys.platform.startswith("win"):
                        wx.CallAfter(sys.stdout.write, "Checking for and removing any existing SSH tunnel(s) using local port 5901...\n\n")
                        os.system("ps ax | grep \"5901\\:\" | grep ssh | awk '{print $1}' | xargs kill")

                    def createTunnel():
                        wx.CallAfter(sys.stdout.write, "Starting tunnelled SSH session...\n")
                        wx.CallAfter(sys.stdout.write, "ssh -L 5901:"+visnode+":5901 "+username+"@"+host+"\n\n")

                        try:
                            forward.forward_tunnel(5901, visnode, 5901, sshClient.get_transport())
                        except KeyboardInterrupt:
                            wx.CallAfter(sys.stdout.write, "C-c: Port forwarding stopped.")
                            ###sys.exit(0)

                    tunnelThread = threading.Thread(target=createTunnel)

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Creating secure tunnel...")

                    tunnelThread.start()
                    time.sleep(2)

                    if sys.platform.startswith("win"):
                        vnc = r"C:\Program Files\TurboVNC\vncviewer.exe"
                    else:
                        vnc = "/opt/TurboVNC/bin/vncviewer"
                    if sys.platform.startswith("win"):
                        key = None
                        queryResult = None
                        foundTurboVncInRegistry = False
                        if not foundTurboVncInRegistry:
                            try:
                                key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC 64-bit_is1", 0,  _winreg.KEY_WOW64_64KEY | _winreg.KEY_ALL_ACCESS)
                                queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False
                        if not foundTurboVncInRegistry:
                            try:
                                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC 64-bit_is1", 0,  _winreg.KEY_WOW64_64KEY | _winreg.KEY_ALL_ACCESS)
                                queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False
                        if not foundTurboVncInRegistry:
                            try:
                                key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_ALL_ACCESS)
                                queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False
                        if not foundTurboVncInRegistry:
                            try:
                                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_ALL_ACCESS)
                                queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False

                    if os.path.exists(vnc):
                        wx.CallAfter(sys.stdout.write, "TurboVNC was found in " + vnc + "\n")
                    else:
                        wx.CallAfter(sys.stdout.write, "Error: TurboVNC was not found in " + vnc + "\n")

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Launching TurboVNC...")

                    wx.CallAfter(sys.stdout.write, "\nStarting MASSIVE VNC...\n")

                    try:
                        if sys.platform.startswith("win"):
                            proc = subprocess.Popen("\""+vnc+"\" /user "+username+" /autopass localhost:1", 
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                universal_newlines=True)
                            proc.communicate(input=password)
                            #proc.communicate()
                        else:
                            subprocess.call("echo \"" + password + "\" | " + vnc + " -user " + username + " -autopass localhost:1",shell=True)
                        arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
                        loginDialogFrame.SetCursor(arrowCursor)
                        loginDialogPanel.SetCursor(arrowCursor)
                        massiveHostLabel.SetCursor(arrowCursor)
                        massiveProjectLabel.SetCursor(arrowCursor)
                        massiveHoursLabel.SetCursor(arrowCursor)
                        massiveUsernameLabel.SetCursor(arrowCursor)
                        massivePasswordLabel.SetCursor(arrowCursor)
                        massiveHostComboBox.SetCursor(arrowCursor)
                        massiveProjectComboBox.SetCursor(arrowCursor)
                        massiveHoursField.SetCursor(arrowCursor)
                        massiveUsernameTextField.SetCursor(arrowCursor)
                        massivePasswordField.SetCursor(arrowCursor)
                        cancelButton.SetCursor(arrowCursor)
                        loginButton.SetCursor(arrowCursor)

                    except:
                        wx.CallAfter(sys.stdout.write, "MASSIVE Launcher v" + massive_launcher_version_number.version_number + "\n")
                        wx.CallAfter(sys.stdout.write, traceback.format_exc())

                        arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
                        loginDialogFrame.SetCursor(arrowCursor)
                        loginDialogPanel.SetCursor(arrowCursor)
                        massiveHostLabel.SetCursor(arrowCursor)
                        massiveProjectLabel.SetCursor(arrowCursor)
                        massiveHoursLabel.SetCursor(arrowCursor)
                        massiveUsernameLabel.SetCursor(arrowCursor)
                        massivePasswordLabel.SetCursor(arrowCursor)
                        massiveHostComboBox.SetCursor(arrowCursor)
                        massiveProjectComboBox.SetCursor(arrowCursor)
                        massiveHoursField.SetCursor(arrowCursor)
                        massiveUsernameTextField.SetCursor(arrowCursor)
                        massivePasswordField.SetCursor(arrowCursor)
                        cancelButton.SetCursor(arrowCursor)
                        loginButton.SetCursor(arrowCursor)

                except:
                    wx.CallAfter(sys.stdout.write, "MASSIVE Launcher v" + massive_launcher_version_number.version_number + "\n")
                    wx.CallAfter(sys.stdout.write, traceback.format_exc())

                    arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
                    loginDialogFrame.SetCursor(arrowCursor)
                    loginDialogPanel.SetCursor(arrowCursor)
                    massiveHostLabel.SetCursor(arrowCursor)
                    massiveProjectLabel.SetCursor(arrowCursor)
                    massiveHoursLabel.SetCursor(arrowCursor)
                    massiveUsernameLabel.SetCursor(arrowCursor)
                    massivePasswordLabel.SetCursor(arrowCursor)
                    massiveHostComboBox.SetCursor(arrowCursor)
                    massiveProjectComboBox.SetCursor(arrowCursor)
                    massiveHoursField.SetCursor(arrowCursor)
                    massiveUsernameTextField.SetCursor(arrowCursor)
                    massivePasswordField.SetCursor(arrowCursor)
                    cancelButton.SetCursor(arrowCursor)
                    loginButton.SetCursor(arrowCursor)

                # Example of using wx.PostEvent to post an event from a thread:
                #wx.PostEvent(self._notify_window, ResultEvent(10))

            def abort(self):
                """abort worker thread."""
                # Method for use by main thread to signal an abort
                self._want_abort = 1

        username = massiveUsernameTextField.GetValue()
        password = massivePasswordField.GetValue()
        host = massiveHostComboBox.GetValue()
        hours = str(massiveHoursField.GetValue())
        project = massiveProjectComboBox.GetValue()
        if project == defaultProjectPlaceholder:
            xmlrpcServer = xmlrpclib.Server("https://m2-web.massive.org.au/kgadmin/xmlrpc/")
            # Get list of user's projects from Karaage:
            # users_projects = xmlrpcServer.get_users_projects(username,password)
            # projects = users_projects[1]
            # Get user's default project from Karaage:
            project = xmlrpcServer.get_project(username)
            massiveProjectComboBox.SetValue(project)

        config.set("MASSIVE Launcher Preferences","username",username)
        config.set("MASSIVE Launcher Preferences","project",project)
        with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
            config.write(massiveLauncherPreferencesFileObject)

        logWindow = wx.Frame(self, title="MASSIVE Login", name="MASSIVE Login",pos=(200,150),size=(700,450))

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            logWindow.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            logWindow.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        logTextCtrl = wx.TextCtrl(logWindow, style=wx.TE_MULTILINE|wx.TE_READONLY)
        gs = wx.GridSizer(rows=1, cols=1, vgap=5, hgap=5)
        gs.Add(logTextCtrl, 0, wx.EXPAND)
        logWindow.SetSizer(gs)
        if sys.platform.startswith("darwin"):
            font = wx.Font(13, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        else:
            font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        logTextCtrl.SetFont(font)
        logWindow.Show(True)

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

        appDirs = appdirs.AppDirs("MASSIVE Launcher", "Monash University")
        appUserDataDir = appDirs.user_data_dir
        # Add trailing slash:
        appUserDataDir = os.path.join(appUserDataDir,"")
        if not os.path.exists(appUserDataDir):
            os.makedirs(appUserDataDir)
        global config
        config = ConfigParser.RawConfigParser(allow_no_value=True)
        global massiveLauncherPreferencesFilePath
        massiveLauncherPreferencesFilePath = os.path.join(appUserDataDir,"MASSIVE Launcher Preferences.cfg")
        if os.path.exists(massiveLauncherPreferencesFilePath):
            config.read(massiveLauncherPreferencesFilePath)

        global loginDialogFrame
        loginDialogFrame = MyFrame(None, -1, 'MASSIVE Launcher')
        loginDialogFrame.Show(True)
        return True

app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
app.MainLoop()

