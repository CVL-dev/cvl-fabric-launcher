# launcher.py
"""
A wxPython GUI to provide easy login to the MASSIVE Desktop.
It can be run using "python launcher.py", assuming that you 
have a 32-bit (*) version of Python installed,
wxPython, and the dependent Python modules imported below.

(*) wxPython on Mac OS X doesn't yet work nicely in 64-bit mode.

The py2app module is required to build the "CVL Launcher.app"
application bundle on Mac OS X, which can be built as follows:

   python create_mac_bundle.py py2app

See: https://confluence-vre.its.monash.edu.au/display/CVL/MASSIVE+Launcher+Mac+OS+X+build+instructions
  
The py2exe module is required to build the "CVL Launcher.exe"
executable on Windows, which can be built as follows:

   python create_windows_bundle.py py2exe

See: https://confluence-vre.its.monash.edu.au/display/CVL/MASSIVE+Launcher+Windows+build+instructions

A Windows installation wizard can be built using InnoSetup,
and the CVL.iss script.

A self-contained Linux binary distribution can be built using
PyInstaller, as described on the following wiki page.

See: https://confluence-vre.its.monash.edu.au/display/CVL/MASSIVE+Launcher+Linux+build+instructions

ACKNOWLEDGEMENT

Thanks to Michael Eager for a concise, non-GUI Python script
which demonstrated the use of the Python pexpect module to 
automate SSH logins and to automate calling TurboVNC 
on Linux and on Mac OS X.
 
"""

# Later, STDERR will be redirected to self.logTextCtrl
# For now, we just want make sure that the Launcher doesn't attempt 
# to write to CVL Launcher.exe.log, because it might not have
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
import ssh # Pure Python ssh module, based on Paramiko, published on PyPi
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

global launcherMainFrame
global massiveConfig
global cvlConfig
global massiveLauncherPreferencesFilePath
global cvlLauncherPreferencesFilePath

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

class LauncherMainFrame(wx.Frame):

    def __init__(self, parent, id, title):

        if sys.platform.startswith("darwin"):
            wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        else:
            wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        self.vncOptions = {}

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
        self.help_menu.Append(wx.ID_ABOUT,   "&About MASSIVE/CVL Launcher")
        self.Bind(wx.EVT_MENU, self.onAbout, id=wx.ID_ABOUT)
        self.menu_bar.Append(self.help_menu, "&Help")

        self.SetTitle("MASSIVE / CVL Launcher")

        self.SetMenuBar(self.menu_bar)

        self.loginDialogPanel = wx.Panel(self, wx.ID_ANY)
        self.loginDialogPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=15, hgap=5)

        self.tabbedView = wx.Notebook(self.loginDialogPanel, wx.ID_ANY, style=(wx.NB_TOP))

        # MASSIVE tab

        self.massiveLoginDialogPanel = wx.Panel(self.tabbedView, wx.ID_ANY)
        self.massiveLoginDialogPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=5, hgap=5)

        self.massiveLoginFieldsPanel = wx.Panel(self.massiveLoginDialogPanel, wx.ID_ANY)
        self.massiveLoginFieldsPanelSizer = wx.FlexGridSizer(rows=7, cols=2, vgap=3, hgap=5)
        self.massiveLoginFieldsPanel.SetSizer(self.massiveLoginFieldsPanelSizer)

        widgetWidth1 = 180
        widgetWidth2 = 180
        if not sys.platform.startswith("win"):
            widgetWidth2 = widgetWidth2 + 25

        self.massiveLoginHostLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Host')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveLoginHostLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveLoginHost = ""
        massiveLoginHosts = ["m1-login1.massive.org.au", "m1-login2.massive.org.au",
            "m2-login1.massive.org.au", "m2-login2.massive.org.au","cvldemo"]
        defaultMassiveHost = "m2-login2.massive.org.au"
        self.massiveLoginHostComboBox = wx.ComboBox(self.massiveLoginFieldsPanel, wx.ID_ANY, value=defaultMassiveHost, choices=massiveLoginHosts, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.massiveLoginFieldsPanelSizer.Add(self.massiveLoginHostComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        if massiveConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveConfig.has_option("MASSIVE Launcher Preferences", "massive_login_host"):
                self.massiveLoginHost = massiveConfig.get("MASSIVE Launcher Preferences", "massive_login_host")
            elif massiveConfig.has_option("MASSIVE Launcher Preferences", "host"):
                self.massiveLoginHost = massiveConfig.get("MASSIVE Launcher Preferences", "host")
            else:
                massiveConfig.set("MASSIVE Launcher Preferences","massive_login_host","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveConfig.write(massiveLauncherPreferencesFileObject)
        if self.massiveLoginHost.strip()!="":
            self.massiveLoginHostComboBox.SetValue(self.massiveLoginHost)

        self.massiveProjectLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'MASSIVE project')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveProjectLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.defaultProjectPlaceholder = '[Use my default massiveProject]'
        massiveProjects = [
            self.defaultProjectPlaceholder,
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
        self.massiveProjectComboBox = wx.ComboBox(self.massiveLoginFieldsPanel, wx.ID_ANY, value='', choices=massiveProjects, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.massiveLoginFieldsPanelSizer.Add(self.massiveProjectComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.massiveProject = ""
        if massiveConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveConfig.has_option("MASSIVE Launcher Preferences", "massive_project"):
                self.massiveProject = massiveConfig.get("MASSIVE Launcher Preferences", "massive_project")
            elif massiveConfig.has_option("MASSIVE Launcher Preferences", "project"):
                self.massiveProject = massiveConfig.get("MASSIVE Launcher Preferences", "project")
            else:
                massiveConfig.set("MASSIVE Launcher Preferences","massive_project","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveConfig.write(massiveLauncherPreferencesFileObject)
        if self.massiveProject.strip()!="":
            self.massiveProjectComboBox.SetValue(self.massiveProject)
        else:
            self.massiveProjectComboBox.SetValue(self.defaultProjectPlaceholder)

        self.massiveHoursLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Hours requested')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveHoursLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveHoursRequested = "4"
        if massiveConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveConfig.has_option("MASSIVE Launcher Preferences", "massive_hours_requested"):
                self.massiveHoursRequested = massiveConfig.get("MASSIVE Launcher Preferences", "massive_hours_requested")
                if self.massiveHoursRequested.strip() == "":
                    self.massiveHoursRequested = "4"
            elif massiveConfig.has_option("MASSIVE Launcher Preferences", "hours"):
                self.massiveHoursRequested = massiveConfig.get("MASSIVE Launcher Preferences", "hours")
                if self.massiveHoursRequested.strip() == "":
                    self.massiveHoursRequested = "4"
            else:
                massiveConfig.set("MASSIVE Launcher Preferences","massive_hours_requested","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveConfig.write(massiveLauncherPreferencesFileObject)
        self.massiveHoursField = wx.SpinCtrl(self.massiveLoginFieldsPanel, wx.ID_ANY, value=self.massiveHoursRequested, min=1,max=24)
        self.massiveLoginFieldsPanelSizer.Add(self.massiveHoursField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveVncDisplayResolutionLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Resolution')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveVncDisplayResolutionLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        displaySize = wx.DisplaySize()
        desiredWidth = displaySize[0] * 0.99
        desiredHeight = displaySize[1] * 0.85
        defaultResolution = str(int(desiredWidth)) + "x" + str(int(desiredHeight))
        self.massiveVncDisplayResolution = defaultResolution
        massiveVncDisplayResolutions = [
            defaultResolution, "1024x768", "1152x864", "1280x800", "1280x1024", "1360x768", "1366x768", "1440x900", "1600x900", "1680x1050", "1920x1080", "1920x1200", "7680x3200",
            ]
        self.massiveVncDisplayResolutionComboBox = wx.ComboBox(self.massiveLoginFieldsPanel, wx.ID_ANY, value='', choices=massiveVncDisplayResolutions, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.massiveLoginFieldsPanelSizer.Add(self.massiveVncDisplayResolutionComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        if massiveConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveConfig.has_option("MASSIVE Launcher Preferences", "massive_vnc_display_resolution"):
                self.massiveVncDisplayResolution = massiveConfig.get("MASSIVE Launcher Preferences", "massive_vnc_display_resolution")
            elif massiveConfig.has_option("MASSIVE Launcher Preferences", "resolution"):
                self.massiveVncDisplayResolution = massiveConfig.get("MASSIVE Launcher Preferences", "resolution")
            else:
                massiveConfig.set("MASSIVE Launcher Preferences","massive_vnc_display_resolution","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveConfig.write(massiveLauncherPreferencesFileObject)
        if self.massiveVncDisplayResolution.strip()!="":
            self.massiveVncDisplayResolutionComboBox.SetValue(self.massiveVncDisplayResolution)
        else:
            self.massiveVncDisplayResolutionComboBox.SetValue(defaultResolution)

        self.massiveSshTunnelCipherLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'SSH tunnel cipher')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveSshTunnelCipherLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveSshTunnelCipher = ""
        if sys.platform.startswith("win"):
            defaultCipher = "arcfour"
            massiveSshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour"]
        else:
            defaultCipher = "arcfour128"
            massiveSshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour128"]
        self.massiveSshTunnelCipherComboBox = wx.ComboBox(self.massiveLoginFieldsPanel, wx.ID_ANY, value='', choices=massiveSshTunnelCiphers, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.massiveLoginFieldsPanelSizer.Add(self.massiveSshTunnelCipherComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        if massiveConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveConfig.has_option("MASSIVE Launcher Preferences", "massive_ssh_tunnel_cipher"):
                self.massiveSshTunnelCipher = massiveConfig.get("MASSIVE Launcher Preferences", "massive_ssh_tunnel_cipher")
            if massiveConfig.has_option("MASSIVE Launcher Preferences", "cipher"):
                self.massiveSshTunnelCipher = massiveConfig.get("MASSIVE Launcher Preferences", "cipher")
            else:
                massiveConfig.set("MASSIVE Launcher Preferences","massive_ssh_tunnel_cipher","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveConfig.write(massiveLauncherPreferencesFileObject)
        if self.massiveSshTunnelCipher.strip()!="":
            self.massiveSshTunnelCipherComboBox.SetValue(self.massiveSshTunnelCipher)
        else:
            self.massiveSshTunnelCipherComboBox.SetValue(defaultCipher)

        self.massiveUsernameLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Username')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveUsernameLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveUsername = ""
        if massiveConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveConfig.has_option("MASSIVE Launcher Preferences", "massive_username"):
                self.massiveUsername = massiveConfig.get("MASSIVE Launcher Preferences", "massive_username")
            elif massiveConfig.has_option("MASSIVE Launcher Preferences", "username"):
                self.massiveUsername = massiveConfig.get("MASSIVE Launcher Preferences", "username")
            else:
                massiveConfig.set("MASSIVE Launcher Preferences","massive_username","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveConfig.write(massiveLauncherPreferencesFileObject)
        self.massiveUsernameTextField = wx.TextCtrl(self.massiveLoginFieldsPanel, wx.ID_ANY, self.massiveUsername, size=(widgetWidth1, -1))
        self.massiveLoginFieldsPanelSizer.Add(self.massiveUsernameTextField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=8)
        if self.massiveUsername.strip()!="":
            self.massiveUsernameTextField.SelectAll()

        self.massivePasswordLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Password')
        self.massiveLoginFieldsPanelSizer.Add(self.massivePasswordLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massivePassword = ""
        self.massivePasswordField = wx.TextCtrl(self.massiveLoginFieldsPanel, wx.ID_ANY, self.massivePassword, size=(widgetWidth1, -1), style=wx.TE_PASSWORD)
        self.massiveLoginFieldsPanelSizer.Add(self.massivePasswordField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=8)

        self.massiveUsernameTextField.SetFocus()

        self.massiveProjectComboBox.MoveAfterInTabOrder(self.massiveLoginHostComboBox)
        self.massiveHoursField.MoveAfterInTabOrder(self.massiveProjectComboBox)
        self.massiveVncDisplayResolutionComboBox.MoveAfterInTabOrder(self.massiveHoursField)
        self.massiveSshTunnelCipherComboBox.MoveAfterInTabOrder(self.massiveVncDisplayResolutionComboBox)
        self.massiveUsernameTextField.MoveAfterInTabOrder(self.massiveSshTunnelCipherComboBox)
        self.massivePasswordField.MoveAfterInTabOrder(self.massiveUsernameTextField)

        self.massiveLoginFieldsPanel.SetSizerAndFit(self.massiveLoginFieldsPanelSizer)

        self.massiveLoginDialogPanelSizer.Add(self.massiveLoginFieldsPanel, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=15)

        self.massiveLoginDialogPanel.SetSizerAndFit(self.massiveLoginDialogPanelSizer)
        self.massiveLoginDialogPanel.Layout()

        self.tabbedView.AddPage(self.massiveLoginDialogPanel, "MASSIVE")

        # CVL tab

        self.cvlLoginDialogPanel = wx.Panel(self.tabbedView, wx.ID_ANY)

        self.tabbedView.AddPage(self.cvlLoginDialogPanel, "CVL")

        self.cvlLoginDialogPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=5, hgap=5)

        self.cvlLoginFieldsPanel = wx.Panel(self.cvlLoginDialogPanel, wx.ID_ANY)
        self.cvlLoginFieldsPanelSizer = wx.FlexGridSizer(rows=7, cols=2, vgap=3, hgap=5)
        self.cvlLoginFieldsPanel.SetSizer(self.cvlLoginFieldsPanelSizer)

        self.cvlLoginHostLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Host')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlLoginHostLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlLoginHost = ""
        cvlLoginHosts = ["115.146.93.198"]
        defaultCvlHost = "115.146.93.198"
        self.cvlLoginHostComboBox = wx.ComboBox(self.cvlLoginFieldsPanel, wx.ID_ANY, value=defaultCvlHost, choices=cvlLoginHosts, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.cvlLoginFieldsPanelSizer.Add(self.cvlLoginHostComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        if cvlConfig.has_section("CVL Launcher Preferences"):
            if cvlConfig.has_option("CVL Launcher Preferences", "cvl_login_host"):
                self.cvlLoginHost = cvlConfig.get("CVL Launcher Preferences", "cvl_login_host")
            else:
                cvlConfig.set("CVL Launcher Preferences","cvl_login_host","")
                with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    cvlConfig.write(cvlLauncherPreferencesFileObject)
        else:
            cvlConfig.add_section("CVL Launcher Preferences")
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlConfig.write(cvlLauncherPreferencesFileObject)
        if self.cvlLoginHost.strip()!="":
            self.cvlLoginHostComboBox.SetValue(self.cvlLoginHost)

        self.cvlVncDisplayResolutionLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Resolution')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlVncDisplayResolutionLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        displaySize = wx.DisplaySize()
        desiredWidth = displaySize[0] * 0.99
        desiredHeight = displaySize[1] * 0.85
        defaultResolution = str(int(desiredWidth)) + "x" + str(int(desiredHeight))
        self.cvlVncDisplayResolution = defaultResolution
        cvlVncDisplayResolutions = [
            defaultResolution, "1024x768", "1152x864", "1280x800", "1280x1024", "1360x768", "1366x768", "1440x900", "1600x900", "1680x1050", "1920x1080", "1920x1200", "7680x3200",
            ]
        self.cvlVncDisplayResolutionComboBox = wx.ComboBox(self.cvlLoginFieldsPanel, wx.ID_ANY, value='', choices=cvlVncDisplayResolutions, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.cvlLoginFieldsPanelSizer.Add(self.cvlVncDisplayResolutionComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        if cvlConfig.has_section("CVL Launcher Preferences"):
            if cvlConfig.has_option("CVL Launcher Preferences", "cvl_vnc_display_resolution"):
                self.cvlVncDisplayResolution = cvlConfig.get("CVL Launcher Preferences", "cvl_vnc_display_resolution")
            elif cvlConfig.has_option("CVL Launcher Preferences", "resolution"):
                self.cvlVncDisplayResolution = cvlConfig.get("CVL Launcher Preferences", "resolution")
            else:
                cvlConfig.set("CVL Launcher Preferences","cvl_vnc_display_resolution","")
                with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    cvlConfig.write(cvlLauncherPreferencesFileObject)
        else:
            cvlConfig.add_section("CVL Launcher Preferences")
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlConfig.write(cvlLauncherPreferencesFileObject)
        if self.cvlVncDisplayResolution.strip()!="":
            self.cvlVncDisplayResolutionComboBox.SetValue(self.cvlVncDisplayResolution)
        else:
            self.cvlVncDisplayResolutionComboBox.SetValue(defaultResolution)

        self.cvlSshTunnelCipherLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'SSH tunnel cipher')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlSshTunnelCipherLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlSshTunnelCipher = ""
        if sys.platform.startswith("win"):
            defaultCipher = "arcfour"
            cvlSshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour"]
        else:
            defaultCipher = "arcfour128"
            cvlSshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour128"]
        self.cvlSshTunnelCipherComboBox = wx.ComboBox(self.cvlLoginFieldsPanel, wx.ID_ANY, value='', choices=cvlSshTunnelCiphers, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.cvlLoginFieldsPanelSizer.Add(self.cvlSshTunnelCipherComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        if cvlConfig.has_section("CVL Launcher Preferences"):
            if cvlConfig.has_option("CVL Launcher Preferences", "cvl_ssh_tunnel_cipher"):
                self.cvlSshTunnelCipher = cvlConfig.get("CVL Launcher Preferences", "cvl_ssh_tunnel_cipher")
            if cvlConfig.has_option("CVL Launcher Preferences", "cipher"):
                self.cvlSshTunnelCipher = cvlConfig.get("CVL Launcher Preferences", "cipher")
            else:
                cvlConfig.set("CVL Launcher Preferences","cvl_ssh_tunnel_cipher","")
                with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    cvlConfig.write(cvlLauncherPreferencesFileObject)
        else:
            cvlConfig.add_section("CVL Launcher Preferences")
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlConfig.write(cvlLauncherPreferencesFileObject)
        if self.cvlSshTunnelCipher.strip()!="":
            self.cvlSshTunnelCipherComboBox.SetValue(self.cvlSshTunnelCipher)
        else:
            self.cvlSshTunnelCipherComboBox.SetValue(defaultCipher)

        self.cvlUsernameLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Username')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlUsernameLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlUsername = ""
        if cvlConfig.has_section("CVL Launcher Preferences"):
            if cvlConfig.has_option("CVL Launcher Preferences", "cvl_username"):
                self.cvlUsername = cvlConfig.get("CVL Launcher Preferences", "cvl_username")
            else:
                cvlConfig.set("CVL Launcher Preferences","cvl_username","")
                with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    cvlConfig.write(cvlLauncherPreferencesFileObject)
        else:
            cvlConfig.add_section("CVL Launcher Preferences")
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlConfig.write(cvlLauncherPreferencesFileObject)
        self.cvlUsernameTextField = wx.TextCtrl(self.cvlLoginFieldsPanel, wx.ID_ANY, self.cvlUsername, size=(widgetWidth1, -1))
        self.cvlLoginFieldsPanelSizer.Add(self.cvlUsernameTextField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=8)
        if self.cvlUsername.strip()!="":
            self.cvlUsernameTextField.SelectAll()

        self.cvlPasswordLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Password')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlPasswordLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlPassword = ""
        self.cvlPasswordField = wx.TextCtrl(self.cvlLoginFieldsPanel, wx.ID_ANY, self.cvlPassword, size=(widgetWidth1, -1), style=wx.TE_PASSWORD)
        self.cvlLoginFieldsPanelSizer.Add(self.cvlPasswordField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=8)

        self.cvlVncDisplayResolutionComboBox.MoveAfterInTabOrder(self.cvlLoginHostComboBox)
        self.cvlSshTunnelCipherComboBox.MoveAfterInTabOrder(self.cvlVncDisplayResolutionComboBox)
        self.cvlUsernameTextField.MoveAfterInTabOrder(self.cvlSshTunnelCipherComboBox)
        self.cvlPasswordField.MoveAfterInTabOrder(self.cvlUsernameTextField)

        self.cvlLoginFieldsPanel.SetSizerAndFit(self.cvlLoginFieldsPanelSizer)

        self.cvlLoginDialogPanelSizer.Add(self.cvlLoginFieldsPanel, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=15)

        self.cvlLoginDialogPanel.SetSizerAndFit(self.cvlLoginDialogPanelSizer)
        self.cvlLoginDialogPanel.Layout()

        # End CVL tab

        self.loginDialogPanelSizer.Add(self.tabbedView, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=10)

        MASSIVE_TAB_INDEX = 0
        self.tabbedView.ChangeSelection(MASSIVE_TAB_INDEX)
        self.massiveTabSelected = True
        self.cvlTabSelected = False

        # Buttons Panel

        self.buttonsPanel = wx.Panel(self.loginDialogPanel, wx.ID_ANY)

        self.buttonsPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=5, hgap=10)
        self.buttonsPanel.SetSizer(self.buttonsPanelSizer)

        self.optionsButton = wx.Button(self.buttonsPanel, 1, 'Options...')
        self.buttonsPanelSizer.Add(self.optionsButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)

        self.cancelButton = wx.Button(self.buttonsPanel, 2, 'Cancel')
        self.buttonsPanelSizer.Add(self.cancelButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)

        self.loginButton = wx.Button(self.buttonsPanel, 3, 'Login')
        self.buttonsPanelSizer.Add(self.loginButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)

        self.buttonsPanel.SetSizerAndFit(self.buttonsPanelSizer)

        self.loginDialogPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=15)

        self.loginButton.SetDefault()

        self.Bind(wx.EVT_BUTTON, self.onOptions, id=1)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=2)
        self.Bind(wx.EVT_BUTTON, self.onLogin, id=3)

        self.loginDialogStatusBar = LauncherStatusBar(self)
        self.SetStatusBar(self.loginDialogStatusBar)

        self.loginDialogPanel.SetSizerAndFit(self.loginDialogPanelSizer)
        self.loginDialogPanel.Layout()

        self.Fit()
        self.Layout()

        self.Centre()

        launcherURL = "https://www.massive.org.au/index.php?option=com_content&view=article&id=121"

        try:
            myHtmlParser = MyHtmlParser()
            feed = urllib.urlopen(launcherURL)
            html = feed.read()
            myHtmlParser.feed(html)
            myHtmlParser.close()
        except:
            dlg = wx.MessageDialog(self, "Error: Unable to contact MASSIVE website to check version number.\n\n" +
                                        "The launcher cannot continue.\n",
                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            sys.exit(1)


        latestVersion = myHtmlParser.data[0].strip()

        if latestVersion!=launcher_version_number.version_number:
            newVersionAlertDialog = wx.Dialog(launcherMainFrame, title="MASSIVE/CVL Launcher", name="MASSIVE/CVL Launcher",pos=(200,150),size=(680,290))

            if sys.platform.startswith("win"):
                _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
                newVersionAlertDialog.SetIcon(_icon)

            if sys.platform.startswith("linux"):
                import MASSIVE_icon
                newVersionAlertDialog.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

            massiveIconPanel = wx.Panel(newVersionAlertDialog)

            import MASSIVE_icon
            massiveIconAsBitmap = MASSIVE_icon.getMASSIVElogoTransparent128x128Bitmap()
            wx.StaticBitmap(massiveIconPanel, wx.ID_ANY, 
                massiveIconAsBitmap,
                (0, 50),
                (massiveIconAsBitmap.GetWidth(), massiveIconAsBitmap.GetHeight())) 

            newVersionAlertTextPanel = wx.Panel(newVersionAlertDialog)

            newVersionAlertTextPanelSizer = wx.FlexGridSizer(rows=4, cols=1, vgap=5, hgap=5)
            newVersionAlertTextPanel.SetSizer(newVersionAlertTextPanelSizer)

            newVersionAlertTitleLabel = wx.StaticText(newVersionAlertTextPanel,
                label = "MASSIVE/CVL Launcher")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetPointSize(14)
            font.SetWeight(wx.BOLD)
            newVersionAlertTitleLabel.SetFont(font)
            newVersionAlertTextPanelSizer.Add(wx.StaticText(newVersionAlertTextPanel))
            newVersionAlertTextPanelSizer.Add(newVersionAlertTitleLabel, flag=wx.EXPAND)
            newVersionAlertTextPanelSizer.Add(wx.StaticText(newVersionAlertTextPanel))

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
            newVersionAlertTextPanelSizer.Add(newVersionAlertTextLabel1, flag=wx.EXPAND)

            newVersionAlertHyperlink = wx.HyperlinkCtrl(newVersionAlertTextPanel, 
                id = wx.ID_ANY,
                label = launcherURL,
                url = launcherURL)
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(8)
            newVersionAlertHyperlink.SetFont(font)
            newVersionAlertTextPanelSizer.Add(newVersionAlertHyperlink, flag=wx.EXPAND)
            newVersionAlertTextPanelSizer.Add(wx.StaticText(newVersionAlertTextPanel))

            newVersionAlertTextLabel2 = wx.StaticText(newVersionAlertTextPanel, 
                label = 
                "For queries, please contact:\n\nhelp@massive.org.au\njames.wettenhall@monash.edu\n")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(9)
            newVersionAlertTextLabel2.SetFont(font)
            newVersionAlertTextPanelSizer.Add(newVersionAlertTextLabel2, flag=wx.EXPAND)

            def onOK(event):
                sys.exit(1)

            okButton = wx.Button(newVersionAlertTextPanel, 1, ' OK ')
            okButton.SetDefault()
            newVersionAlertTextPanelSizer.Add(okButton, flag=wx.ALIGN_RIGHT)
            newVersionAlertTextPanelSizer.Add(wx.StaticText(newVersionAlertTextPanel))
            newVersionAlertTextPanelSizer.Fit(newVersionAlertTextPanel)

            newVersionAlertDialog.Bind(wx.EVT_BUTTON, onOK, id=1)

            newVersionAlertDialogSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=5, hgap=5)
            newVersionAlertDialogSizer.Add(massiveIconPanel, flag=wx.EXPAND)
            newVersionAlertDialogSizer.Add(newVersionAlertTextPanel, flag=wx.EXPAND)
            newVersionAlertDialogSizer.Add(wx.StaticText(newVersionAlertDialog,label="       "))
            newVersionAlertDialog.SetSizer(newVersionAlertDialogSizer)
            newVersionAlertDialogSizer.Fit(newVersionAlertDialog)

            newVersionAlertDialog.ShowModal()
            newVersionAlertDialog.Destroy()

            sys.exit(1)
 
    def onAbout(self, event):
        dlg = wx.MessageDialog(self, "Version " + launcher_version_number.version_number + "\n",
                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onExit(self, event):
        try:
            os.unlink(launcherMainFrame.loginThread.privateKeyFile.name)
        finally:
            os._exit(0)

    def onOptions(self, event):
        import turboVncOptions
        turboVncOptionsDialog = turboVncOptions.TurboVncOptions(launcherMainFrame, wx.ID_ANY, "TurboVNC Viewer Options", self.vncOptions)
        turboVncOptionsDialog.ShowModal()
        if turboVncOptionsDialog.okClicked:
            self.vncOptions = turboVncOptionsDialog.getVncOptions()
            #import pprint
            #vncOptionsDictionaryString = pprint.pformat(self.vncOptions)
            #wx.CallAfter(sys.stdout.write, vncOptionsDictionaryString + "\n")

    def onCancel(self, event):
        try:
            os.unlink(launcherMainFrame.loginThread.privateKeyFile.name)
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

    def SetCursor(self, cursor):
        self.massiveLoginDialogPanel.SetCursor(cursor)
        self.massiveLoginFieldsPanel.SetCursor(cursor)
        self.buttonsPanel.SetCursor(cursor)
        self.massiveLoginHostLabel.SetCursor(cursor)
        self.massiveProjectLabel.SetCursor(cursor)
        self.massiveHoursLabel.SetCursor(cursor)
        self.massiveVncDisplayResolutionLabel.SetCursor(cursor)
        self.massiveSshTunnelCipherLabel.SetCursor(cursor)
        self.massiveUsernameLabel.SetCursor(cursor)
        self.massivePasswordLabel.SetCursor(cursor)
        self.massiveLoginHostComboBox.SetCursor(cursor)
        self.massiveVncDisplayResolutionComboBox.SetCursor(cursor)
        self.massiveSshTunnelCipherComboBox.SetCursor(cursor)
        self.massiveProjectComboBox.SetCursor(cursor)
        self.massiveHoursField.SetCursor(cursor)
        self.massiveUsernameTextField.SetCursor(cursor)
        self.massivePasswordField.SetCursor(cursor)
        self.cancelButton.SetCursor(cursor)
        self.loginButton.SetCursor(cursor)
        super(LauncherMainFrame, self).SetCursor(cursor)

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

                try:
                    launcherMainFrame.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))

                    MASSIVE_TAB_INDEX = 0
                    CVL_TAB_INDEX =1 

                    if launcherMainFrame.tabbedView.GetSelection()==MASSIVE_TAB_INDEX:
                        launcherMainFrame.massiveTabSelected = True
                        launcherMainFrame.cvlTabSelected = False

                    if launcherMainFrame.tabbedView.GetSelection()==CVL_TAB_INDEX:
                        launcherMainFrame.massiveTabSelected = False
                        launcherMainFrame.cvlTabSelected = True

                    if launcherMainFrame.massiveTabSelected:
                        self.host       = launcherMainFrame.massiveLoginHost
                        self.resolution = launcherMainFrame.massiveVncDisplayResolution
                        self.cipher     = launcherMainFrame.massiveSshTunnelCipher
                        self.username   = launcherMainFrame.massiveUsername
                        self.password   = launcherMainFrame.massivePassword
                    else:
                        self.host       = launcherMainFrame.cvlLoginHost
                        self.resolution = launcherMainFrame.cvlVncDisplayResolution
                        self.cipher     = launcherMainFrame.cvlSshTunnelCipher
                        self.username   = launcherMainFrame.cvlUsername
                        self.password   = launcherMainFrame.cvlPassword
                    
                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Logging in to " + self.host)
                    wx.CallAfter(sys.stdout.write, "Attempting to log in to " + self.host + "...\n")
                    
                    sshClient = ssh.SSHClient()
                    sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())
                    sshClient.connect(self.host,username=self.username,password=self.password)

                    wx.CallAfter(sys.stdout.write, "First login done.\n")

                    wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Setting display resolution...")

                    set_display_resolution_cmd = "/usr/local/desktop/set_display_resolution.sh " + self.resolution
                    wx.CallAfter(sys.stdout.write, set_display_resolution_cmd + "\n")
                    stdin,stdout,stderr = sshClient.exec_command(set_display_resolution_cmd)
                    stderrRead = stderr.read()
                    if len(stderrRead) > 0:
                        wx.CallAfter(sys.stdout.write, stderrRead)
                    
                    wx.CallAfter(sys.stdout.write, "\n")

                    if launcherMainFrame.massiveTabSelected:
                        # Begin if launcherMainFrame.massiveTabSelected:

                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Checking quota...")

                        stdin,stdout,stderr = sshClient.exec_command("mybalance --hours")
                        wx.CallAfter(sys.stdout.write, stderr.read())
                        wx.CallAfter(sys.stdout.write, stdout.read())

                        wx.CallAfter(sys.stdout.write, "\n")

                        stdin,stdout,stderr = sshClient.exec_command("echo `showq -w class:vis | grep \"processors in use by local jobs\" | awk '{print $1}'` of 10 nodes in use")
                        wx.CallAfter(sys.stdout.write, stderr.read())
                        wx.CallAfter(sys.stdout.write, stdout.read())

                        wx.CallAfter(sys.stdout.write, "\n")

                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Requesting remote desktop...")

                        #qsubcmd = "qsub -A " + self.massiveProject + " -I -q vis -l walltime=" + launcherMainFrame.massiveHoursRequested + ":0:0,nodes=1:ppn=12:gpus=2,pmem=16000MB"
                        qsubcmd = "/usr/local/desktop/request_visnode.sh " + launcherMainFrame.massiveProject + " " + launcherMainFrame.massiveHoursRequested

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
                                            sshClient2.connect(self.host,username=self.username,password=self.password)
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

                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Acquired desktop node:" + visnode)

                        wx.CallAfter(sys.stdout.write, "Massive Desktop visnode: " + visnode + "\n\n")

                        # End if launcherMainFrame.massiveTabSelected:

                    wx.CallAfter(sys.stdout.write, "Generating SSH key-pair for tunnel...\n\n")

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Generating SSH key-pair for tunnel...")

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
                    self.privateKeyFile = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
                    self.privateKeyFile.write(privateKeyString)
                    self.privateKeyFile.flush()
                    self.privateKeyFile.close()

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
                                chown_cmd = chownBinary + " \"" + getpass.getuser() + "\" " + self.privateKeyFile.name
                                wx.CallAfter(sys.stdout.write, chown_cmd + "\n")
                                subprocess.call(chown_cmd, shell=True)

                            chmod_cmd = chmodBinary + " 600 " + self.privateKeyFile.name
                            wx.CallAfter(sys.stdout.write, chmod_cmd + "\n")
                            subprocess.call(chmod_cmd, shell=True)

                            proxyCommand = "-oProxyCommand=\"ssh -c " + self.cipher + " -i " + self.privateKeyFile.name +" "+self.username+"@"+self.host+" 'nc %h %p'\""
                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Requesting ephemeral port...")

                            self.localPortNumber = "5901"
                            # Request an ephemeral port from the operating system (by specifying port 0) :
                            import socket
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
                            sock.bind(('localhost', 0)) 
                            self.localPortNumber = sock.getsockname()[1]
                            sock.close()
                            self.localPortNumber = str(self.localPortNumber)

                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Creating secure tunnel...")

                            #tunnel_cmd = sshBinary + " -i " + self.privateKeyFile.name + " -c " + self.cipher + " " \
                                #"-oStrictHostKeyChecking=no " \
                                #"-A " + proxyCommand + " " \
                                #"-L " + self.localPortNumber + ":localhost:5901" + " -l " + self.username+" "+visnode+"-ib"

                            if launcherMainFrame.massiveTabSelected:
                                tunnel_cmd = sshBinary + " -i " + self.privateKeyFile.name + " -c " + self.cipher + " " \
                                    "-t -t " \
                                    "-oStrictHostKeyChecking=no " \
                                    "-L " + self.localPortNumber + ":"+visnode+"-ib:5901" + " -l " + self.username+" "+self.host
                            else:
                                tunnel_cmd = sshBinary + " -i " + self.privateKeyFile.name + " -c " + self.cipher + " " \
                                    "-t -t " \
                                    "-oStrictHostKeyChecking=no " \
                                    "-L " + self.localPortNumber + ":localhost:5901" + " -l " + self.username+" "+self.host

                            wx.CallAfter(sys.stdout.write, tunnel_cmd + "\n")
                            self.sshTunnelProcess = subprocess.Popen(tunnel_cmd,
                                universal_newlines=True,shell=True,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)

                            launcherMainFrame.loginThread.sshTunnelReady = False
                            while True:
                                time.sleep(1)
                                line = self.sshTunnelProcess.stdout.readline()
                                if "Last login" in line:
                                    launcherMainFrame.loginThread.sshTunnelReady = True
                                    break
                            else:
                                launcherMainFrame.loginThread.sshTunnelReady = True

                        except KeyboardInterrupt:
                            wx.CallAfter(sys.stdout.write, "C-c: Port forwarding stopped.")
                            try:
                                os.unlink(self.privateKeyFile.name)
                            finally:
                                os._exit(0)
                        except:
                            wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                            wx.CallAfter(sys.stdout.write, traceback.format_exc())

                    self.sshTunnelReady = False
                    tunnelThread = threading.Thread(target=createTunnel)

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Creating secure tunnel...")

                    tunnelThread.start()

                    count = 1
                    while not self.sshTunnelReady and count < 30 and launcherMainFrame.massiveTabSelected:
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

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Launching TurboVNC...")

                    wx.CallAfter(sys.stdout.write, "\nStarting MASSIVE VNC...\n")

                    try:
                        if sys.platform.startswith("win"):
                            optionPrefixCharacter = "/"
                        else:
                            optionPrefixCharacter = "-"
                        vncOptionsString = ""
                        if 'jpegCompression' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['jpegCompression']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "nojpeg"
                        defaultJpegChrominanceSubsampling = "1x"
                        if 'jpegChrominanceSubsampling' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['jpegChrominanceSubsampling']!=defaultJpegChrominanceSubsampling:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "samp " + launcherMainFrame.vncOptions['jpegChrominanceSubsampling']
                        defaultJpegImageQuality = "95"
                        if 'jpegImageQuality' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['jpegImageQuality']!=defaultJpegImageQuality:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "quality " + launcherMainFrame.vncOptions['jpegImageQuality']
                        if 'zlibCompressionEnabled' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['zlibCompressionEnabled']==True:
                            if 'zlibCompressionLevel' in launcherMainFrame.vncOptions:
                                vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "compresslevel " + launcherMainFrame.vncOptions['zlibCompressionLevel']
                        if 'viewOnly' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['viewOnly']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "viewonly"
                        if 'disableClipboardTransfer' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['disableClipboardTransfer']==True:
                            if sys.platform.startswith("win"):
                                vncOptionsString = vncOptionsString + " /disableclipboard"
                            else:
                                vncOptionsString = vncOptionsString + " -noclipboardsend -noclipboardrecv"
                        if sys.platform.startswith("win"):
                            if 'scale' in launcherMainFrame.vncOptions:
                                if launcherMainFrame.vncOptions['scale']=="Auto":
                                    vncOptionsString = vncOptionsString + " /fitwindow"
                                else:
                                    vncOptionsString = vncOptionsString + " /scale " + launcherMainFrame.vncOptions['scale']
                            defaultSpanMode = 'automatic'
                            if 'span' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['span']!=defaultSpanMode:
                                vncOptionsString = vncOptionsString + " /span " + launcherMainFrame.vncOptions['span']
                        if 'doubleBuffering' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['doubleBuffering']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "singlebuffer"
                        if 'fullScreenMode' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['fullScreenMode']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "fullscreen"
                        if 'deiconifyOnRemoteBellEvent' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['deiconifyOnRemoteBellEvent']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "noraiseonbeep"
                        if sys.platform.startswith("win"):
                            if 'emulate3' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['emulate3']==True:
                                vncOptionsString = vncOptionsString + " /emulate3"
                            if 'swapmouse' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['swapmouse']==True:
                                vncOptionsString = vncOptionsString + " /swapmouse"
                        if 'dontShowRemoteCursor' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['dontShowRemoteCursor']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "nocursorshape"
                        elif 'letRemoteServerDealWithCursor' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['letRemoteServerDealWithCursor']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "x11cursor"
                        if 'requestSharedSession' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['requestSharedSession']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "noshared"
                        if sys.platform.startswith("win"):
                            if 'toolbar' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['toolbar']==False:
                                vncOptionsString = vncOptionsString + " /notoolbar"
                            if 'dotcursor' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['dotcursor']==True:
                                vncOptionsString = vncOptionsString + " /dotcursor"
                            if 'smalldotcursor' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['smalldotcursor']==True:
                                vncOptionsString = vncOptionsString + " /smalldotcursor"
                            if 'normalcursor' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['normalcursor']==True:
                                vncOptionsString = vncOptionsString + " /normalcursor"
                            if 'nocursor' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['nocursor']==True:
                                vncOptionsString = vncOptionsString + " /nocursor"
                            if 'writelog' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['writelog']==True:
                                if 'loglevel' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['loglevel']==True:
                                    vncOptionsString = vncOptionsString + " /loglevel " + launcherMainFrame.vncOptions['loglevel']
                                if 'logfile' in launcherMainFrame.vncOptions:
                                    vncOptionsString = vncOptionsString + " /logfile \"" + launcherMainFrame.vncOptions['logfile'] + "\""

                        if sys.platform.startswith("win"):
                            vncCommandString = "\""+vnc+"\" /user "+self.username+" /autopass " + vncOptionsString + " localhost::" + self.localPortNumber
                            wx.CallAfter(sys.stdout.write, vncCommandString + "\n")
                            proc = subprocess.Popen(vncCommandString, 
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                universal_newlines=True)
                            proc.communicate(input=self.password + "\r\n")
                        else:
                            vncCommandString = vnc + " -user " + self.username + " -autopass " + vncOptionsString + " localhost::" + self.localPortNumber
                            wx.CallAfter(sys.stdout.write, vncCommandString + "\n")
                            proc = subprocess.Popen(vncCommandString, 
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                universal_newlines=True)
                            proc.communicate(input=self.password + "\n")
                        try:
                            self.sshTunnelProcess.terminate()
                            os.unlink(self.privateKeyFile.name)
                        finally:
                            os._exit(0)

                        launcherMainFrame.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))

                    except:
                        wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                        wx.CallAfter(sys.stdout.write, traceback.format_exc())

                        launcherMainFrame.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))

                except:
                    wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                    wx.CallAfter(sys.stdout.write, traceback.format_exc())

                    launcherMainFrame.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))

        MASSIVE_TAB_INDEX = 0
        CVL_TAB_INDEX =1 

        if launcherMainFrame.tabbedView.GetSelection()==MASSIVE_TAB_INDEX:
            launcherMainFrame.massiveTabSelected = True
            launcherMainFrame.cvlTabSelected = False

        if launcherMainFrame.tabbedView.GetSelection()==CVL_TAB_INDEX:
            launcherMainFrame.massiveTabSelected = False
            launcherMainFrame.cvlTabSelected = True

        if launcherMainFrame.massiveTabSelected:
            self.massiveLoginHost = self.massiveLoginHostComboBox.GetValue()
            self.massiveUsername = self.massiveUsernameTextField.GetValue()
            self.massivePassword = self.massivePasswordField.GetValue()
            self.massiveVncDisplayResolution = self.massiveVncDisplayResolutionComboBox.GetValue()
            self.massiveSshTunnelCipher = self.massiveSshTunnelCipherComboBox.GetValue()
        else:
            self.cvlLoginHost = self.cvlLoginHostComboBox.GetValue()
            self.cvlUsername = self.cvlUsernameTextField.GetValue()
            self.cvlPassword = self.cvlPasswordField.GetValue()
            self.cvlVncDisplayResolution = self.cvlVncDisplayResolutionComboBox.GetValue()
            self.cvlSshTunnelCipher = self.cvlSshTunnelCipherComboBox.GetValue()

        if launcherMainFrame.massiveTabSelected:
            self.massiveHoursRequested = str(self.massiveHoursField.GetValue())
            self.massiveProject = self.massiveProjectComboBox.GetValue()
            if self.massiveProject == self.defaultProjectPlaceholder:
                xmlrpcServer = xmlrpclib.Server("https://m2-web.massive.org.au/kgadmin/xmlrpc/")
                # Get list of user's massiveProjects from Karaage:
                # users_massiveProjects = xmlrpcServer.get_users_massiveProjects(self.massiveUsername, self.massivePassword)
                # massiveProjects = users_massiveProjects[1]
                # Get user's default massiveProject from Karaage:
                self.massiveProject = xmlrpcServer.get_massiveProject(self.massiveUsername)
                self.massiveProjectComboBox.SetValue(self.massiveProject)

        if launcherMainFrame.massiveTabSelected:
            massiveConfig.set("MASSIVE Launcher Preferences", "massive_login_host", self.massiveLoginHost)
            massiveConfig.set("MASSIVE Launcher Preferences", "massive_username", self.massiveUsername)
            massiveConfig.set("MASSIVE Launcher Preferences", "massive_vnc_display_resolution", self.massiveVncDisplayResolution)
            massiveConfig.set("MASSIVE Launcher Preferences", "massive_ssh_tunnel_cipher", self.massiveSshTunnelCipher)
        else:
            cvlConfig.set("CVL Launcher Preferences", "cvl_login_host", self.cvlLoginHost)
            cvlConfig.set("CVL Launcher Preferences", "cvl_username", self.cvlUsername)
            cvlConfig.set("CVL Launcher Preferences", "cvl_vnc_display_resolution", self.cvlVncDisplayResolution)
            cvlConfig.set("CVL Launcher Preferences", "cvl_ssh_tunnel_cipher", self.cvlSshTunnelCipher)

        if launcherMainFrame.massiveTabSelected:
            massiveConfig.set("MASSIVE Launcher Preferences", "massive_project", self.massiveProject)
            massiveConfig.set("MASSIVE Launcher Preferences", "massive_hours_requested", self.massiveHoursRequested)

        if launcherMainFrame.massiveTabSelected:
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveConfig.write(massiveLauncherPreferencesFileObject)
        else:
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlConfig.write(cvlLauncherPreferencesFileObject)

        if launcherMainFrame.massiveTabSelected:
            logWindow = wx.Frame(self, title="MASSIVE Login", name="MASSIVE Login",pos=(200,150),size=(700,450))
        else:
            logWindow = wx.Frame(self, title="CVL Login", name="CVL Login",pos=(200,150),size=(700,450))

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            logWindow.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            logWindow.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.logTextCtrl = wx.TextCtrl(logWindow, style=wx.TE_MULTILINE|wx.TE_READONLY)
        logWindowSizer = wx.GridSizer(rows=1, cols=1, vgap=5, hgap=5)
        logWindowSizer.Add(self.logTextCtrl, 0, wx.EXPAND)
        logWindow.SetSizer(logWindowSizer)
        if sys.platform.startswith("darwin"):
            font = wx.Font(13, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        else:
            font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        self.logTextCtrl.SetFont(font)
        logWindow.Show(True)

        sys.stdout = self.logTextCtrl
        sys.stderr = self.logTextCtrl
        #print "Redirected STDOUT and STDERR to self.logTextCtrl"

        self.loginThread = LoginThread(self)

class LauncherStatusBar(wx.StatusBar):
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

        global massiveConfig
        massiveConfig = ConfigParser.RawConfigParser(allow_no_value=True)

        global massiveLauncherPreferencesFilePath
        massiveLauncherPreferencesFilePath = os.path.join(appUserDataDir,"MASSIVE Launcher Preferences.cfg")
        if os.path.exists(massiveLauncherPreferencesFilePath):
            massiveConfig.read(massiveLauncherPreferencesFilePath)

        global cvlConfig
        cvlConfig = ConfigParser.RawConfigParser(allow_no_value=True)

        global cvlLauncherPreferencesFilePath
        cvlLauncherPreferencesFilePath = os.path.join(appUserDataDir,"CVL Launcher Preferences.cfg")
        if os.path.exists(cvlLauncherPreferencesFilePath):
            cvlConfig.read(cvlLauncherPreferencesFilePath)

        global launcherMainFrame
        launcherMainFrame = LauncherMainFrame(None, wx.ID_ANY, 'MASSIVE/CVL Launcher')
        launcherMainFrame.Show(True)
        return True

app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
app.MainLoop()

