# launcher.py
"""
A wxPython GUI to provide easy login to the MASSIVE Desktop.
It can be run using "python launcher.py", assuming that you 
have a 32-bit (*) version of Python installed,
wxPython, and the dependent Python modules imported below.

(*) wxPython on Mac OS X doesn't yet work nicely in 64-bit mode.

The py2app module is required to build the "MASSIVE Launcher.app"
application bundle on Mac OS X, which can be built as follows:

   python create_mac_bundle.py py2app

See: https://confluence-vre.its.monash.edu.au/display/CVL/MASSIVE+Launcher+Mac+OS+X+build+instructions
  
The py2exe module is required to build the "MASSIVE Launcher.exe"
executable on Windows, which can be built as follows:

   python create_windows_bundle.py py2exe

See: https://confluence-vre.its.monash.edu.au/display/CVL/MASSIVE+Launcher+Windows+build+instructions

A Windows installation wizard can be built using InnoSetup,
and the MASSIVE.iss script.

A self-contained Linux binary distribution can be built using
PyInstaller, as described on the following wiki page.

See: https://confluence-vre.its.monash.edu.au/display/CVL/MASSIVE+Launcher+Linux+build+instructions

ACKNOWLEDGEMENT

Thanks to Michael Eager for a concise, non-GUI Python script
which demonstrated the use of the Python pexpect module to 
automate SSH logins and to automate calling TurboVNC 
on Linux and on Mac OS X.
 
"""

# Later, STDERR will be redirected to logTextCtrl
# For now, we just want make sure that the Launcher doesn't attempt 
# to write to MASSIVE Launcher.exe.log, because it might not have
# permission to do so.
import sys
sys.stderr = sys.stdout

if sys.platform.startswith("win"):
    import _winreg
import subprocess
import wx
import time
import traceback
import threading
import os
import ssh # Pure Python-based ssh module, based on Paramiko, published on PyPi
import HTMLParser
import urllib
import launcher_version_number
import StringIO
import xmlrpclib
import appdirs
import ConfigParser
#import logging

#logger = ssh.util.logging.getLogger()
#logger.setLevel(logging.WARN)

global vncOptions
vncOptions = {}
defaultMassiveHost = "m2-login2.massive.org.au"
global vncLoginHost
vncLoginHost = ""
global project
project = ""
global hours
hours = ""
global resolution
resolution = ""
global cipher
cipher = ""
global username
username = ""
password = ""
global sshTunnelProcess
sshTunnelProcess = None
global sshTunnelReady
sshTunnelReady = False
global localPortNumber
localPortNumber = "5901"
global privateKeyFile
global launcherMainFrame
launcherMainFrame = None

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

class MassiveLauncherMainFrame(wx.Frame):

    def __init__(self, parent, id, title):

        global logTextCtrl

        if sys.platform.startswith("darwin"):
            wx.Frame.__init__(self, parent, id, title, size=(350, 390), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        else:
            wx.Frame.__init__(self, parent, id, title, size=(350, 430), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.menu_bar  = wx.MenuBar()

        if sys.platform.startswith("win") or sys.platform.startswith("linux"):
            self.file_menu = wx.Menu()
            self.file_menu.Append(wx.ID_EXIT, "E&xit\tAlt-X", "Close window and exit program.")
            self.Bind(wx.EVT_MENU, self.onExit, id=wx.ID_EXIT)
            self.menu_bar.Append(self.file_menu, "&File")

        if sys.platform.startswith("darwin"):
            # Only do this for Mac OS X, because other platforms have
            # a right-click pop-up menu for wx.TextCtrl with Copy,
            # Select All etc. Plus, the menu doesn't look that good on
            # the MASSIVE Launcher main dialog, and doesn't work for
            # non Mac platforms, because of FindFocus() will always
            # find the window/dialog which contains the menu.
            self.edit_menu = wx.Menu()
            self.edit_menu.Append(wx.ID_CUT, "Cut", "Cut the selected text")
            self.Bind(wx.EVT_MENU, self.onCut, id=wx.ID_CUT)
            self.edit_menu.Append(wx.ID_COPY, "Copy", "Copy the selected text")
            self.Bind(wx.EVT_MENU, self.onCopy, id=wx.ID_COPY)
            self.edit_menu.Append(wx.ID_PASTE, "Paste", "Paste text from the clipboard")
            self.Bind(wx.EVT_MENU, self.onPaste, id=wx.ID_PASTE)
            self.edit_menu.Append(wx.ID_SELECTALL, "Select All")
            self.Bind(wx.EVT_MENU, self.onSelectAll, id=wx.ID_SELECTALL)
            self.menu_bar.Append(self.edit_menu, "&Edit")

        self.help_menu = wx.Menu()
        self.help_menu.Append(wx.ID_ABOUT,   "&About MASSIVE Launcher")
        self.Bind(wx.EVT_MENU, self.onAbout, id=wx.ID_ABOUT)
        self.menu_bar.Append(self.help_menu, "&Help")

        self.SetTitle("MASSIVE / CVL Launcher")

        self.SetMenuBar(self.menu_bar)

        global loginDialogPanel
        loginDialogPanel = wx.Panel(self)

        global vncLoginHostLabel
        #vncLoginHostLabel = wx.StaticText(loginDialogPanel, -1, 'MASSIVE host', (10, 20))
        vncLoginHostLabel = wx.StaticText(loginDialogPanel, -1, 'Host', (10, 20))
        global massiveProjectLabel
        massiveProjectLabel = wx.StaticText(loginDialogPanel, -1, 'MASSIVE project', (10, 60))
        global massiveHoursLabel
        massiveHoursLabel = wx.StaticText(loginDialogPanel, -1, 'Hours requested', (10, 100))
        global vncDisplayResolutionLabel
        vncDisplayResolutionLabel = wx.StaticText(loginDialogPanel, -1, 'Resolution', (10, 140))
        global sshTunnelCipherLabel
        sshTunnelCipherLabel = wx.StaticText(loginDialogPanel, -1, 'SSH tunnel cipher', (10, 180))
        global usernameLabel
        usernameLabel = wx.StaticText(loginDialogPanel, -1, 'Username', (10, 220))
        global passwordLabel
        passwordLabel = wx.StaticText(loginDialogPanel, -1, 'Password', (10, 260))

        widgetWidth1 = 180
        widgetWidth2 = 180
        if not sys.platform.startswith("win"):
            widgetWidth2 = widgetWidth2 + 25

        global vncLoginHost
        vncLoginHosts = ["m1-login1.massive.org.au", "m1-login2.massive.org.au",
            "m2-login1.massive.org.au", "m2-login2.massive.org.au","cvldemo"]
        global vncLoginHostComboBox
        vncLoginHostComboBox = wx.ComboBox(loginDialogPanel, -1, value=defaultMassiveHost, pos=(125, 15), size=(widgetWidth2, -1),choices=vncLoginHosts, style=wx.CB_DROPDOWN)
        if config.has_section("MASSIVE Launcher Preferences"):
            if config.has_option("MASSIVE Launcher Preferences", "vncLoginHost"):
                vncLoginHost = config.get("MASSIVE Launcher Preferences", "vncLoginHost")
            else:
                config.set("MASSIVE Launcher Preferences","vncLoginHost","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    config.write(massiveLauncherPreferencesFileObject)
        else:
            config.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                config.write(massiveLauncherPreferencesFileObject)
        if vncLoginHost.strip()!="":
            vncLoginHostComboBox.SetValue(vncLoginHost)

        global defaultProjectPlaceholder
        defaultProjectPlaceholder = '[Use my default project]'
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

        global hours
        hours = "4"
        if config.has_section("MASSIVE Launcher Preferences"):
            if config.has_option("MASSIVE Launcher Preferences", "hours"):
                hours = config.get("MASSIVE Launcher Preferences", "hours")
                if hours.strip() == "":
                    hours = "4"
            else:
                config.set("MASSIVE Launcher Preferences","hours","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    config.write(massiveLauncherPreferencesFileObject)
        else:
            config.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                config.write(massiveLauncherPreferencesFileObject)
        global massiveHoursField
        massiveHoursField = wx.SpinCtrl(loginDialogPanel, -1, value=hours, pos=(123, 95), size=(widgetWidth2, -1),min=1,max=24)

        global defaultResolution
        displaySize = wx.DisplaySize()
        desiredWidth = displaySize[0] * 0.99
        desiredHeight = displaySize[1] * 0.85
        defaultResolution = str(int(desiredWidth)) + "x" + str(int(desiredHeight))
        resolution = defaultResolution
        resolutions = [
            defaultResolution, "1024x768", "1152x864", "1280x800", "1280x1024", "1360x768", "1366x768", "1440x900", "1600x900", "1680x1050", "1920x1080", "1920x1200", "7680x3200",
            ]
        global massiveResolutionComboBox
        massiveResolutionComboBox = wx.ComboBox(loginDialogPanel, -1, value='', pos=(125, 135), size=(widgetWidth2, -1),choices=resolutions, style=wx.CB_DROPDOWN)
        if config.has_section("MASSIVE Launcher Preferences"):
            if config.has_option("MASSIVE Launcher Preferences", "resolution"):
                resolution = config.get("MASSIVE Launcher Preferences", "resolution")
            else:
                config.set("MASSIVE Launcher Preferences","resolution","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    config.write(massiveLauncherPreferencesFileObject)
        else:
            config.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                config.write(massiveLauncherPreferencesFileObject)
        if resolution.strip()!="":
            massiveResolutionComboBox.SetValue(resolution)
        else:
            massiveResolutionComboBox.SetValue(defaultResolution)

        cipher = ""
        if sys.platform.startswith("win"):
            defaultCipher = "arcfour"
            ciphers = ["3des-cbc", "blowfish-cbc", "arcfour"]
        else:
            defaultCipher = "arcfour128"
            ciphers = ["3des-cbc", "blowfish-cbc", "arcfour128"]
        global sshTunnelCipherComboBox
        sshTunnelCipherComboBox = wx.ComboBox(loginDialogPanel, -1, value='', pos=(125, 175), size=(widgetWidth2, -1),choices=ciphers, style=wx.CB_DROPDOWN)
        if config.has_section("MASSIVE Launcher Preferences"):
            if config.has_option("MASSIVE Launcher Preferences", "cipher"):
                cipher = config.get("MASSIVE Launcher Preferences", "cipher")
            else:
                config.set("MASSIVE Launcher Preferences","cipher","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    config.write(massiveLauncherPreferencesFileObject)
        else:
            config.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                config.write(massiveLauncherPreferencesFileObject)
        if cipher.strip()!="":
            sshTunnelCipherComboBox.SetValue(cipher)
        else:
            sshTunnelCipherComboBox.SetValue(defaultCipher)

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
        global usernameTextField
        usernameTextField = wx.TextCtrl(loginDialogPanel, -1, username,  (125, 215), (widgetWidth1, -1))
        if username.strip()!="":
            usernameTextField.SelectAll()

        global passwordField
        passwordField = wx.TextCtrl(loginDialogPanel, -1, '',  (125, 255), (widgetWidth1, -1), style=wx.TE_PASSWORD)

        usernameTextField.SetFocus()

        massiveProjectComboBox.MoveAfterInTabOrder(vncLoginHostComboBox)
        massiveHoursField.MoveAfterInTabOrder(massiveProjectComboBox)
        massiveResolutionComboBox.MoveAfterInTabOrder(massiveHoursField)
        sshTunnelCipherComboBox.MoveAfterInTabOrder(massiveResolutionComboBox)
        usernameTextField.MoveAfterInTabOrder(sshTunnelCipherComboBox)
        passwordField.MoveAfterInTabOrder(usernameTextField)

        global optionsButton
        optionsButton = wx.Button(loginDialogPanel, 1, 'Options...', (15, 305))

        global cancelButton
        cancelButton = wx.Button(loginDialogPanel, 2, 'Cancel', (130, 305))

        global loginButton
        loginButton = wx.Button(loginDialogPanel, 3, 'Login', (230, 305))
        loginButton.SetDefault()

        self.Bind(wx.EVT_BUTTON, self.onOptions, id=1)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=2)
        self.Bind(wx.EVT_BUTTON, self.onLogin, id=3)

        self.statusbar = MyStatusBar(self)
        global loginDialogStatusBar
        loginDialogStatusBar = self.statusbar
        self.SetStatusBar(self.statusbar)
        self.Centre()

        massiveLauncherURL = "https://www.massive.org.au/index.php?option=com_content&view=article&id=121"

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

        if latestVersion!=launcher_version_number.version_number:
            newVersionAlertDialog = wx.Dialog(launcherMainFrame, title="MASSIVE Launcher", name="MASSIVE Launcher",pos=(200,150),size=(680,290))

            if sys.platform.startswith("win"):
                _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
                newVersionAlertDialog.SetIcon(_icon)

            if sys.platform.startswith("linux"):
                import MASSIVE_icon
                newVersionAlertDialog.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

            massiveIconPanel = wx.Panel(newVersionAlertDialog)

            import MASSIVE_icon
            massiveIconAsBitmap = MASSIVE_icon.getMASSIVElogoTransparent128x128Bitmap()
            wx.StaticBitmap(massiveIconPanel, -1, 
                massiveIconAsBitmap,
                (0, 50),
                (massiveIconAsBitmap.GetWidth(), massiveIconAsBitmap.GetHeight())) 

            newVersionAlertTextPanel = wx.Panel(newVersionAlertDialog)

            gs = wx.FlexGridSizer(rows=4, cols=1, vgap=5, hgap=5)
            newVersionAlertTextPanel.SetSizer(gs)

            newVersionAlertTitleLabel = wx.StaticText(newVersionAlertTextPanel,
                label = "MASSIVE Launcher")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetPointSize(14)
            font.SetWeight(wx.BOLD)
            newVersionAlertTitleLabel.SetFont(font)
            gs.Add(wx.StaticText(newVersionAlertTextPanel))
            gs.Add(newVersionAlertTitleLabel, flag=wx.EXPAND)
            gs.Add(wx.StaticText(newVersionAlertTextPanel))

            newVersionAlertTextLabel1 = wx.StaticText(newVersionAlertTextPanel, 
                label = 
                "You are running version " + launcher_version_number.version_number + "\n\n" +
                "The latest version is " + myHtmlParser.data[0] + "\n\n" +
                "Please download a new version from:\n\n")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(9)
            newVersionAlertTextLabel1.SetFont(font)
            gs.Add(newVersionAlertTextLabel1, flag=wx.EXPAND)

            newVersionAlertHyperlink = wx.HyperlinkCtrl(newVersionAlertTextPanel, 
                id = wx.ID_ANY,
                label = massiveLauncherURL,
                url = massiveLauncherURL)
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(8)
            newVersionAlertHyperlink.SetFont(font)
            gs.Add(newVersionAlertHyperlink, flag=wx.EXPAND)
            gs.Add(wx.StaticText(newVersionAlertTextPanel))

            newVersionAlertTextLabel2 = wx.StaticText(newVersionAlertTextPanel, 
                label = 
                "For queries, please contact:\n\nhelp@massive.org.au\njames.wettenhall@monash.edu\n")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(9)
            newVersionAlertTextLabel2.SetFont(font)
            gs.Add(newVersionAlertTextLabel2, flag=wx.EXPAND)

            def onOK(event):
                sys.exit(1)

            okButton = wx.Button(newVersionAlertTextPanel, 1, ' OK ')
            okButton.SetDefault()
            gs.Add(okButton, flag=wx.ALIGN_RIGHT)
            gs.Add(wx.StaticText(newVersionAlertTextPanel))
            gs.Fit(newVersionAlertTextPanel)

            newVersionAlertDialog.Bind(wx.EVT_BUTTON, onOK, id=1)

            gs = wx.FlexGridSizer(rows=1, cols=3, vgap=5, hgap=5)
            gs.Add(massiveIconPanel, flag=wx.EXPAND)
            gs.Add(newVersionAlertTextPanel, flag=wx.EXPAND)
            gs.Add(wx.StaticText(newVersionAlertDialog,label="       "))
            newVersionAlertDialog.SetSizer(gs)
            gs.Fit(newVersionAlertDialog)

            newVersionAlertDialog.ShowModal()
            newVersionAlertDialog.Destroy()

            sys.exit(1)
 
    def onAbout(self, event):
        dlg = wx.MessageDialog(self, "Version " + launcher_version_number.version_number + "\n",
                                "MASSIVE Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onExit(self, event):
        try:
            os.unlink(privateKeyFile.name)
        finally:
            os._exit(0)

    def onOptions(self, event):
        import turboVncOptions
        global vncOptions
        turboVncOptionsDialog = turboVncOptions.TurboVncOptions(launcherMainFrame, wx.ID_ANY, "TurboVNC Viewer Options", vncOptions)
        turboVncOptionsDialog.ShowModal()
        if turboVncOptionsDialog.okClicked:
            vncOptions = turboVncOptionsDialog.getVncOptions()
            #import pprint
            #vncOptionsDictionaryString = pprint.pformat(vncOptions)
            #wx.CallAfter(sys.stdout.write, vncOptionsDictionaryString + "\n")

    def onCancel(self, event):
        try:
            os.unlink(privateKeyFile.name)
        finally:
            os._exit(0)

    def onCut(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.Cut()

    def onCopy(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.Copy()

    def onPaste(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.Paste()

    def onSelectAll(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.SelectAll()

    def onLogin(self, event):
        class LoginThread(threading.Thread):
            """Login Thread Class."""
            def __init__(self, notify_window):
                """Init Worker Thread Class."""
                threading.Thread.__init__(self)
                self._notify_window = notify_window
                self.start()

            def run(self):
                """Run Worker Thread."""

                waitCursor = wx.StockCursor(wx.CURSOR_WAIT)
                launcherMainFrame.SetCursor(waitCursor)
                loginDialogPanel.SetCursor(waitCursor)
                vncLoginHostLabel.SetCursor(waitCursor)
                massiveProjectLabel.SetCursor(waitCursor)
                massiveHoursLabel.SetCursor(waitCursor)
                usernameLabel.SetCursor(waitCursor)
                passwordLabel.SetCursor(waitCursor)
                vncLoginHostComboBox.SetCursor(waitCursor)
                massiveProjectComboBox.SetCursor(waitCursor)
                massiveHoursField.SetCursor(waitCursor)
                usernameTextField.SetCursor(waitCursor)
                passwordField.SetCursor(waitCursor)
                cancelButton.SetCursor(waitCursor)
                loginButton.SetCursor(waitCursor)

                global logTextCtrl
                global loginDialogStatusBar

                try:
                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Logging in to " + vncLoginHost)
                    wx.CallAfter(sys.stdout.write, "Attempting to log in to " + vncLoginHost + "...\n")
                    
                    sshClient = ssh.SSHClient()
                    sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())
                    sshClient.connect(vncLoginHost,username=username,password=password)

                    wx.CallAfter(sys.stdout.write, "First login done.\n")

                    wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Setting display resolution...")

                    set_display_resolution_cmd = "/usr/local/desktop/set_display_resolution.sh " + resolution
                    wx.CallAfter(sys.stdout.write, set_display_resolution_cmd + "\n")
                    stdin,stdout,stderr = sshClient.exec_command(set_display_resolution_cmd)
                    stderrRead = stderr.read()
                    if len(stderrRead) > 0:
                        wx.CallAfter(sys.stdout.write, stderrRead)
                    
                    wx.CallAfter(sys.stdout.write, "\n")

                    if "massive" in vncLoginHost:
                        # Begin if "massive" in vncLoginHost:

                        wx.CallAfter(loginDialogStatusBar.SetStatusText, "Checking quota...")

                        stdin,stdout,stderr = sshClient.exec_command("mybalance --hours")
                        wx.CallAfter(sys.stdout.write, stderr.read())
                        wx.CallAfter(sys.stdout.write, stdout.read())

                        wx.CallAfter(sys.stdout.write, "\n")

                        stdin,stdout,stderr = sshClient.exec_command("echo `showq -w class:vis | grep \"processors in use by local jobs\" | awk '{print $1}'` of 10 nodes in use")
                        wx.CallAfter(sys.stdout.write, stderr.read())
                        wx.CallAfter(sys.stdout.write, stdout.read())

                        wx.CallAfter(sys.stdout.write, "\n")

                        wx.CallAfter(loginDialogStatusBar.SetStatusText, "Requesting remote desktop...")

                        #qsubcmd = "qsub -A " + project + " -I -q vis -l walltime=" + hours + ":0:0,nodes=1:ppn=12:gpus=2,pmem=16000MB"
                        qsubcmd = "/usr/local/desktop/request_visnode.sh " + project + " " + hours

                        wx.CallAfter(sys.stdout.write, qsubcmd + "\n")
                        wx.CallAfter(sys.stdout.write, "\n")
                      
                        transport = sshClient.get_transport()
                        channel = transport.open_session()
                        channel.get_pty()
                        channel.setblocking(0)
                        channel.invoke_shell()
                        out = ""
                        channel.send(qsubcmd + "\n")

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
                                    # After 10 seconds, we still haven't obtained a visnode...
                                    if (not checkedShowStart) and jobNumber!="0.m2-m":
                                        checkedShowStart = True
                                        def showStart():
                                            sshClient2 = ssh.SSHClient()
                                            sshClient2.set_missing_host_key_policy(ssh.AutoAddPolicy())
                                            sshClient2.connect(vncLoginHost,username=username,password=password)
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

                        # End if "massive" in vncLoginHost:

                    wx.CallAfter(sys.stdout.write, "Generating SSH key-pair for tunnel...\n\n")

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Generating SSH key-pair for tunnel...")

                    stdin,stdout,stderr = sshClient.exec_command("/bin/rm -f ~/MassiveLauncherKeyPair*")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = sshClient.exec_command("/usr/bin/ssh-keygen -C \"MASSIVE Launcher\" -N \"\" -t rsa -f ~/MassiveLauncherKeyPair")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = sshClient.exec_command("/bin/mkdir ~/.ssh")
                    stdin,stdout,stderr = sshClient.exec_command("/bin/chmod 700 ~/.ssh")
                    stdin,stdout,stderr = sshClient.exec_command("/bin/touch ~/.ssh/authorized_keys")
                    stdin,stdout,stderr = sshClient.exec_command("/bin/chmod 600 ~/.ssh/authorized_keys")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = sshClient.exec_command("/bin/sed -i -e \"/MASSIVE Launcher/d\" ~/.ssh/authorized_keys")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = sshClient.exec_command("/bin/cat MassiveLauncherKeyPair.pub >> ~/.ssh/authorized_keys")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = sshClient.exec_command("/bin/rm -f ~/MassiveLauncherKeyPair.pub")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = sshClient.exec_command("/bin/cat MassiveLauncherKeyPair")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())

                    privateKeyString = stdout.read()

                    stdin,stdout,stderr = sshClient.exec_command("/bin/rm -f ~/MassiveLauncherKeyPair")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())

                    import tempfile
                    privateKeyFile = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
                    privateKeyFile.write(privateKeyString)
                    privateKeyFile.flush()
                    privateKeyFile.close()

                    def createTunnel():
                        wx.CallAfter(sys.stdout.write, "Starting tunnelled SSH session...\n")

                        try:
                            if sys.platform.startswith("win"):
                                sshBinary = "ssh.exe"
                                chownBinary = "chown.exe"
                                chmodBinary = "chmod.exe"
                                if hasattr(sys, 'frozen'):
                                    massiveLauncherBinary = sys.executable
                                    massiveLauncherPath = os.path.dirname(massiveLauncherBinary)
                                    sshBinary = "\"" + os.path.join(massiveLauncherPath, sshBinary) + "\""
                                    chownBinary = "\"" + os.path.join(massiveLauncherPath, chownBinary) + "\""
                                    chmodBinary = "\"" + os.path.join(massiveLauncherPath, chmodBinary) + "\""
                                else:
                                    sshBinary = "\"" + os.path.join(os.getcwd(), "sshwindows", sshBinary) + "\""
                                    chownBinary = "\"" + os.path.join(os.getcwd(), "sshwindows", chownBinary) + "\""
                                    chmodBinary = "\"" + os.path.join(os.getcwd(), "sshwindows", chmodBinary) + "\""
                            elif sys.platform.startswith("darwin"):
                                sshBinary = "/usr/bin/ssh"
                                chownBinary = "/usr/sbin/chown"
                                chmodBinary = "/bin/chmod"
                            else:
                                sshBinary = "/usr/bin/ssh"
                                chownBinary = "/bin/chown"
                                chmodBinary = "/bin/chmod"

                            import getpass
                            if sys.platform.startswith("win"):
                                # On Windows Vista/7, the private key file,
                                # will initially be created without any owner.
                                # We must set the file's owner before we
                                # can change the permissions to -rw------.
                                chown_cmd = chownBinary + " \"" + getpass.getuser() + "\" " + privateKeyFile.name
                                wx.CallAfter(sys.stdout.write, chown_cmd + "\n")
                                subprocess.call(chown_cmd, shell=True)

                            chmod_cmd = chmodBinary + " 600 " + privateKeyFile.name
                            wx.CallAfter(sys.stdout.write, chmod_cmd + "\n")
                            subprocess.call(chmod_cmd, shell=True)

                            proxyCommand = "-oProxyCommand=\"ssh -c " + cipher + " -i " + privateKeyFile.name +" "+username+"@"+vncLoginHost+" 'nc %h %p'\""
                            wx.CallAfter(loginDialogStatusBar.SetStatusText, "Requesting ephemeral port...")

                            global localPortNumber
                            localPortNumber = "5901"
                            # Request an ephemeral port from the operating system (by specifying port 0) :
                            import socket
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
                            sock.bind(('localhost', 0)) 
                            localPortNumber = sock.getsockname()[1]
                            sock.close()
                            localPortNumber = str(localPortNumber)

                            wx.CallAfter(loginDialogStatusBar.SetStatusText, "Creating secure tunnel...")

                            #tunnel_cmd = sshBinary + " -i " + privateKeyFile.name + " -c " + cipher + " " \
                                #"-oStrictHostKeyChecking=no " \
                                #"-A " + proxyCommand + " " \
                                #"-L " + localPortNumber + ":localhost:5901" + " -l " + username+" "+visnode+"-ib"

                            if "massive" in vncLoginHost:
                                tunnel_cmd = sshBinary + " -i " + privateKeyFile.name + " -c " + cipher + " " \
                                    "-t -t " \
                                    "-oStrictHostKeyChecking=no " \
                                    "-L " + localPortNumber + ":"+visnode+"-ib:5901" + " -l " + username+" "+vncLoginHost
                            else:
                                tunnel_cmd = sshBinary + " -i " + privateKeyFile.name + " -c " + cipher + " " \
                                    "-t -t " \
                                    "-oStrictHostKeyChecking=no " \
                                    "-L " + localPortNumber + ":localhost:5901" + " -l " + username+" "+vncLoginHost

                            wx.CallAfter(sys.stdout.write, tunnel_cmd + "\n")
                            global sshTunnelProcess
                            sshTunnelProcess = subprocess.Popen(tunnel_cmd,
                                universal_newlines=True,shell=True,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)

                            global sshTunnelReady
                            sshTunnelReady = False
                            print "Need to determine a way (independent of MASSIVE) to check whether SSH tunnel is ready."
                            if "massive" in vncLoginHost:
                                while True:
                                    time.sleep(1)
                                    line = sshTunnelProcess.stdout.readline()
                                    if "Welcome to MASSIVE" in line:
                                        sshTunnelReady = True
                                        break
                            else:
                                sshTunnelReady = True

                        except KeyboardInterrupt:
                            wx.CallAfter(sys.stdout.write, "C-c: Port forwarding stopped.")
                            try:
                                os.unlink(privateKeyFile.name)
                            finally:
                                os._exit(0)
                        except:
                            wx.CallAfter(sys.stdout.write, "MASSIVE Launcher v" + launcher_version_number.version_number + "\n")
                            wx.CallAfter(sys.stdout.write, traceback.format_exc())

                    tunnelThread = threading.Thread(target=createTunnel)

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Creating secure tunnel...")

                    tunnelThread.start()

                    count = 1
                    while not sshTunnelReady and count < 30 and "massive" in vncLoginHost:
                        time.sleep(1)
                        count = count + 1

                    if count < 5:
                        time.sleep (5-count)

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

                    wx.CallAfter(sys.stdout.write, "\n")

                    if os.path.exists(vnc):
                        wx.CallAfter(sys.stdout.write, "TurboVNC was found in " + vnc + "\n")
                    else:
                        wx.CallAfter(sys.stdout.write, "Error: TurboVNC was not found in " + vnc + "\n")

                    wx.CallAfter(loginDialogStatusBar.SetStatusText, "Launching TurboVNC...")

                    wx.CallAfter(sys.stdout.write, "\nStarting MASSIVE VNC...\n")

                    try:
                        if sys.platform.startswith("win"):
                            optionPrefixCharacter = "/"
                        else:
                            optionPrefixCharacter = "-"
                        vncOptionsString = ""
                        if 'jpegCompression' in vncOptions and vncOptions['jpegCompression']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "nojpeg"
                        defaultJpegChrominanceSubsampling = "1x"
                        if 'jpegChrominanceSubsampling' in vncOptions and vncOptions['jpegChrominanceSubsampling']!=defaultJpegChrominanceSubsampling:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "samp " + vncOptions['jpegChrominanceSubsampling']
                        defaultJpegImageQuality = "95"
                        if 'jpegImageQuality' in vncOptions and vncOptions['jpegImageQuality']!=defaultJpegImageQuality:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "quality " + vncOptions['jpegImageQuality']
                        if 'zlibCompressionEnabled' in vncOptions and vncOptions['zlibCompressionEnabled']==True:
                            if 'zlibCompressionLevel' in vncOptions:
                                vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "compresslevel " + vncOptions['zlibCompressionLevel']
                        if 'viewOnly' in vncOptions and vncOptions['viewOnly']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "viewonly"
                        if 'disableClipboardTransfer' in vncOptions and vncOptions['disableClipboardTransfer']==True:
                            if sys.platform.startswith("win"):
                                vncOptionsString = vncOptionsString + " /disableclipboard"
                            else:
                                vncOptionsString = vncOptionsString + " -noclipboardsend -noclipboardrecv"
                        if sys.platform.startswith("win"):
                            if 'scale' in vncOptions:
                                if vncOptions['scale']=="Auto":
                                    vncOptionsString = vncOptionsString + " /fitwindow"
                                else:
                                    vncOptionsString = vncOptionsString + " /scale " + vncOptions['scale']
                            defaultSpanMode = 'automatic'
                            if 'span' in vncOptions and vncOptions['span']!=defaultSpanMode:
                                vncOptionsString = vncOptionsString + " /span " + vncOptions['span']
                        if 'doubleBuffering' in vncOptions and vncOptions['doubleBuffering']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "singlebuffer"
                        if 'fullScreenMode' in vncOptions and vncOptions['fullScreenMode']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "fullscreen"
                        if 'deiconifyOnRemoteBellEvent' in vncOptions and vncOptions['deiconifyOnRemoteBellEvent']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "noraiseonbeep"
                        if 'dontShowRemoteCursor' in vncOptions and vncOptions['dontShowRemoteCursor']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "nocursorshape"
                        elif 'letRemoteServerDealWithCursor' in vncOptions and vncOptions['letRemoteServerDealWithCursor']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "x11cursor"
                        if 'requestSharedSession' in vncOptions and vncOptions['requestSharedSession']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "noshared"
                        if sys.platform.startswith("win"):
                            if 'toolbar' in vncOptions and vncOptions['toolbar']==False:
                                vncOptionsString = vncOptionsString + " /notoolbar"
                            
                        if sys.platform.startswith("win"):
                            vncCommandString = "\""+vnc+"\" /user "+username+" /autopass " + vncOptionsString + " localhost::" + localPortNumber
                            wx.CallAfter(sys.stdout.write, vncCommandString + "\n")
                            proc = subprocess.Popen(vncCommandString, 
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                universal_newlines=True)
                            proc.communicate(input=password)
                        else:
                            vncCommandString = vnc + " -user " + username + " -autopass " + vncOptionsString + " localhost::" + localPortNumber
                            wx.CallAfter(sys.stdout.write, vncCommandString + "\n")
                            subprocess.call("echo \"" + password + "\" | " + vncCommandString,shell=True)
                        try:
                            global sshTunnelProcess
                            sshTunnelProcess.terminate()
                            os.unlink(privateKeyFile.name)
                        finally:
                            os._exit(0)

                        arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
                        launcherMainFrame.SetCursor(arrowCursor)
                        loginDialogPanel.SetCursor(arrowCursor)
                        vncLoginHostLabel.SetCursor(arrowCursor)
                        massiveProjectLabel.SetCursor(arrowCursor)
                        massiveHoursLabel.SetCursor(arrowCursor)
                        usernameLabel.SetCursor(arrowCursor)
                        passwordLabel.SetCursor(arrowCursor)
                        vncLoginHostComboBox.SetCursor(arrowCursor)
                        massiveProjectComboBox.SetCursor(arrowCursor)
                        massiveHoursField.SetCursor(arrowCursor)
                        usernameTextField.SetCursor(arrowCursor)
                        passwordField.SetCursor(arrowCursor)
                        cancelButton.SetCursor(arrowCursor)
                        loginButton.SetCursor(arrowCursor)

                    except:
                        wx.CallAfter(sys.stdout.write, "MASSIVE Launcher v" + launcher_version_number.version_number + "\n")
                        wx.CallAfter(sys.stdout.write, traceback.format_exc())

                        arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
                        launcherMainFrame.SetCursor(arrowCursor)
                        loginDialogPanel.SetCursor(arrowCursor)
                        vncLoginHostLabel.SetCursor(arrowCursor)
                        massiveProjectLabel.SetCursor(arrowCursor)
                        massiveHoursLabel.SetCursor(arrowCursor)
                        usernameLabel.SetCursor(arrowCursor)
                        passwordLabel.SetCursor(arrowCursor)
                        vncLoginHostComboBox.SetCursor(arrowCursor)
                        massiveProjectComboBox.SetCursor(arrowCursor)
                        massiveHoursField.SetCursor(arrowCursor)
                        usernameTextField.SetCursor(arrowCursor)
                        passwordField.SetCursor(arrowCursor)
                        cancelButton.SetCursor(arrowCursor)
                        loginButton.SetCursor(arrowCursor)

                except:
                    wx.CallAfter(sys.stdout.write, "MASSIVE Launcher v" + launcher_version_number.version_number + "\n")
                    wx.CallAfter(sys.stdout.write, traceback.format_exc())

                    arrowCursor = wx.StockCursor(wx.CURSOR_ARROW)
                    launcherMainFrame.SetCursor(arrowCursor)
                    loginDialogPanel.SetCursor(arrowCursor)
                    vncLoginHostLabel.SetCursor(arrowCursor)
                    massiveProjectLabel.SetCursor(arrowCursor)
                    massiveHoursLabel.SetCursor(arrowCursor)
                    usernameLabel.SetCursor(arrowCursor)
                    passwordLabel.SetCursor(arrowCursor)
                    vncLoginHostComboBox.SetCursor(arrowCursor)
                    massiveProjectComboBox.SetCursor(arrowCursor)
                    massiveHoursField.SetCursor(arrowCursor)
                    usernameTextField.SetCursor(arrowCursor)
                    passwordField.SetCursor(arrowCursor)
                    cancelButton.SetCursor(arrowCursor)
                    loginButton.SetCursor(arrowCursor)

        username = usernameTextField.GetValue()
        password = passwordField.GetValue()
        vncLoginHost = vncLoginHostComboBox.GetValue()
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
        resolution = massiveResolutionComboBox.GetValue()
        cipher = sshTunnelCipherComboBox.GetValue()

        config.set("MASSIVE Launcher Preferences","username",username)
        config.set("MASSIVE Launcher Preferences","host",vncLoginHost)
        config.set("MASSIVE Launcher Preferences","project",project)
        config.set("MASSIVE Launcher Preferences","hours",hours)
        config.set("MASSIVE Launcher Preferences","resolution",resolution)
        config.set("MASSIVE Launcher Preferences","cipher",cipher)
        with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
            config.write(massiveLauncherPreferencesFileObject)

        if "massive" in vncLoginHost:
            logWindow = wx.Frame(self, title="MASSIVE Login", name="MASSIVE Login",pos=(200,150),size=(700,450))
        elif "cvl" in vncLoginHost:
            logWindow = wx.Frame(self, title="CVL Login", name="CVL Login",pos=(200,150),size=(700,450))
        else:
            logWindow = wx.Frame(self, title="Launcher Log Window", name="Launcher Log Window",pos=(200,150),size=(700,450))

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
        #self.SetStatusText('Welcome to MASSIVE', 0)
        self.SetStatusWidths([-5, -2])

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

        global launcherMainFrame
        launcherMainFrame = MassiveLauncherMainFrame(None, -1, 'MASSIVE Launcher')
        launcherMainFrame.Show(True)
        return True

app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
app.MainLoop()

