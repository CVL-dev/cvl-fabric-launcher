#  MASSIVE/CVL Launcher - easy secure login for the MASSIVE Desktop and the CVL
#  Copyright (C) 2012  James Wettenhall, Monash University
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  Enquires: James.Wettenhall@monash.edu or help@massive.org.au

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
import datetime
#import logging

#logger = ssh.util.logging.getLogger()
#logger.setLevel(logging.WARN)

global launcherMainFrame
launcherMainFrame = None
global massiveLauncherConfig
massiveLauncherConfig = None
global cvlLauncherConfig
cvlLauncherConfig = None
global turboVncConfig
turboVncConfig = None
global massiveLauncherPreferencesFilePath
massiveLauncherPreferencesFilePath = None
global cvlLauncherPreferencesFilePath
cvlLauncherPreferencesFilePath = None
global turboVncPreferencesFilePath
turboVncPreferencesFilePath = None

class MyHtmlParser(HTMLParser.HTMLParser):
  def __init__(self):
    HTMLParser.HTMLParser.__init__(self)
    self.recording = 0
    self.data = []
    self.recordingLatestVersionNumber = 0
    self.latestVersionNumber = "0.0.0"
    self.htmlComments = ""

  def handle_starttag(self, tag, attributes):
    if tag != 'span':
      return
    if tag == "span":
        if self.recordingLatestVersionNumber:
          self.recordingLatestVersionNumber += 1
          return
    foundLatestVersionNumberTag = False
    for name, value in attributes:
      if name == 'id' and value == 'MassiveLauncherLatestVersionNumber':
        foundLatestVersionNumberTag = True
        break
    else:
      return
    if foundLatestVersionNumberTag:
        self.recordingLatestVersionNumber = 1

  def handle_endtag(self, tag):
    if tag == 'span' and self.recordingLatestVersionNumber:
      self.recordingLatestVersionNumber -= 1

  def handle_data(self, data):
    if self.recordingLatestVersionNumber:
      #self.data.append(data)
      self.latestVersionNumber = data.strip()

  def handle_comment(self,data):
      self.htmlComments += data.strip()

class LauncherMainFrame(wx.Frame):

    def __init__(self, parent, id, title):

        if sys.platform.startswith("darwin"):
            wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        else:
            wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        self.vncOptions = {}

        if turboVncConfig.has_section("TurboVNC Preferences"):
            savedTurboVncOptions =  turboVncConfig.items("TurboVNC Preferences")
            for option in savedTurboVncOptions:
                key = option[0]
                value = option[1]
                if value=='True':
                    value = True
                if value=='False':
                    value = False
                self.vncOptions[key] = value

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
        widgetWidth3 = 75

        self.massiveLoginHostLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Host')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveLoginHostLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveLoginHost = ""
        massiveLoginHosts = ["m1-login1.massive.org.au", "m1-login2.massive.org.au",
            "m2-login1.massive.org.au", "m2-login2.massive.org.au"]
        defaultMassiveHost = "m2-login2.massive.org.au"
        self.massiveLoginHostComboBox = wx.ComboBox(self.massiveLoginFieldsPanel, wx.ID_ANY, value=defaultMassiveHost, choices=massiveLoginHosts, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.massiveLoginFieldsPanelSizer.Add(self.massiveLoginHostComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_login_host"):
                self.massiveLoginHost = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_login_host")
            elif massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "host"):
                self.massiveLoginHost = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "host")
            else:
                massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_login_host","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        if self.massiveLoginHost.strip()!="":
            self.massiveLoginHostComboBox.SetValue(self.massiveLoginHost)

        self.massiveProjectLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'MASSIVE project')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveProjectLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        # The pre-populated list of projects in the combo-box is 
        # hard-coded for now, because 
        # Karaage (http://code.vpac.org/trac/karaage/)
        # doesn't appear to provide a way to list all projects on MASSIVE
        # without authenticating.
        # The user can type in the project name themself, or use the
        # [Use my default project] option.
        self.defaultProjectPlaceholder = '[Use my default project]'
        massiveProjects = [
            self.defaultProjectPlaceholder,
            'ASync001','ASync002','ASync003','ASync004','ASync005','ASync006',
            'ASync007','ASync008','ASync009','ASync010','ASync011',

            'CSIRO001','CSIRO002','CSIRO003','CSIRO004','CSIRO005','CSIRO006',
            'CSIRO007',

            'Desc001','Desc002','Desc003','Desc004',

            'Monash001','Monash002','Monash003','Monash004',
            'Monash005','Monash006','Monash007','Monash008',
            'Monash009','Monash010','Monash011','Monash012','Monash013',
            'Monash014','Monash015','Monash016','Monash017','Monash018',
            'Monash019','Monash020','Monash021','Monash022','Monash023',
            'Monash024','Monash025','Monash026','Monash027','Monash028',
            'Monash029','Monash030','Monash031','Monash032','Monash033',
            'Monash034','Monash035','Monash036',

            'NCId75','NCIdb5','NCIdc0','NCIdd2','NCIg61','NCIg75',
            'NCIq97','NCIr14','NCIw25','NCIw27','NCIw67','NCIw81','NCIw91',
            'NCIy40','NCIy95','NCIy96',

            'pDeak0023','pDeak0024','pDeak0026',

            'pLaTr0011',

            'pMelb0095','pMelb0100','pMelb0103','pMelb0104',

            'pMOSP',

            'pRMIT0074','pRMIT0078','pRMIT0083',

            'pVPAC0005',

            'Training'
            ]
        self.massiveProjectComboBox = wx.ComboBox(self.massiveLoginFieldsPanel, wx.ID_ANY, value='', choices=massiveProjects, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.massiveLoginFieldsPanelSizer.Add(self.massiveProjectComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.massiveProject = ""
        if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_project"):
                self.massiveProject = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_project")
            elif massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "project"):
                self.massiveProject = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "project")
            else:
                massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_project","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        if self.massiveProject.strip()!="":
            self.massiveProjectComboBox.SetValue(self.massiveProject)
        else:
            self.massiveProjectComboBox.SetValue(self.defaultProjectPlaceholder)

        self.massiveHoursLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Hours requested')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveHoursLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveHoursAndVisNodesPanel = wx.Panel(self.massiveLoginFieldsPanel, wx.ID_ANY)
        self.massiveHoursAndVisNodesPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=3, hgap=5)
        self.massiveHoursAndVisNodesPanel.SetSizer(self.massiveHoursAndVisNodesPanelSizer)

        self.massiveHoursRequested = "4"
        if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_hours_requested"):
                self.massiveHoursRequested = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_hours_requested")
                if self.massiveHoursRequested.strip() == "":
                    self.massiveHoursRequested = "4"
            elif massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "hours"):
                self.massiveHoursRequested = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "hours")
                if self.massiveHoursRequested.strip() == "":
                    self.massiveHoursRequested = "4"
            else:
                massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_hours_requested","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        # Maximum of 336 hours is 2 weeks:
        #self.massiveHoursField = wx.SpinCtrl(self.massiveLoginFieldsPanel, wx.ID_ANY, value=self.massiveHoursRequested, min=1,max=336)
        self.massiveHoursField = wx.SpinCtrl(self.massiveHoursAndVisNodesPanel, wx.ID_ANY, value=self.massiveHoursRequested, size=(widgetWidth3,-1), min=1,max=336)

        #self.massiveLoginFieldsPanelSizer.Add(self.massiveHoursField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.massiveHoursAndVisNodesPanelSizer.Add(self.massiveHoursField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveVisNodesLabel = wx.StaticText(self.massiveHoursAndVisNodesPanel, wx.ID_ANY, 'Vis nodes')
        self.massiveHoursAndVisNodesPanelSizer.Add(self.massiveVisNodesLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveVisNodesRequested = "1"
        if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_visnodes_requested"):
                self.massiveVisNodesRequested = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_visnodes_requested")
                if self.massiveVisNodesRequested.strip() == "":
                    self.massiveVisNodesRequested = "1"
            elif massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "visnodes"):
                self.massiveVisNodesRequested = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "visnodes")
                if self.massiveVisNodesRequested.strip() == "":
                    self.massiveVisNodesRequested = "1"
            else:
                massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_visnodes_requested","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        self.massiveVisNodesField = wx.SpinCtrl(self.massiveHoursAndVisNodesPanel, wx.ID_ANY, value=self.massiveVisNodesRequested, size=(widgetWidth3,-1), min=1,max=10)
        self.massiveHoursAndVisNodesPanelSizer.Add(self.massiveVisNodesField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveHoursAndVisNodesPanel.SetSizerAndFit(self.massiveHoursAndVisNodesPanelSizer)
        self.massiveLoginFieldsPanelSizer.Add(self.massiveHoursAndVisNodesPanel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

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
        if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_vnc_display_resolution"):
                self.massiveVncDisplayResolution = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_vnc_display_resolution")
            elif massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "resolution"):
                self.massiveVncDisplayResolution = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "resolution")
            else:
                massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_vnc_display_resolution","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
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
        if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_ssh_tunnel_cipher"):
                self.massiveSshTunnelCipher = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_ssh_tunnel_cipher")
            if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "cipher"):
                self.massiveSshTunnelCipher = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "cipher")
            else:
                massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_ssh_tunnel_cipher","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        if self.massiveSshTunnelCipher.strip()!="":
            self.massiveSshTunnelCipherComboBox.SetValue(self.massiveSshTunnelCipher)
        else:
            self.massiveSshTunnelCipherComboBox.SetValue(defaultCipher)

        self.massiveUsernameLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Username')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveUsernameLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveUsername = ""
        if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_username"):
                self.massiveUsername = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_username")
            elif massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "username"):
                self.massiveUsername = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "username")
            else:
                massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_username","")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
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
        #self.massiveHoursField.MoveAfterInTabOrder(self.massiveProjectComboBox)
        self.massiveHoursAndVisNodesPanel.MoveAfterInTabOrder(self.massiveProjectComboBox)
        #self.massiveVncDisplayResolutionComboBox.MoveAfterInTabOrder(self.massiveHoursField)
        self.massiveVncDisplayResolutionComboBox.MoveAfterInTabOrder(self.massiveHoursAndVisNodesPanel)
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
        if cvlLauncherConfig.has_section("CVL Launcher Preferences"):
            if cvlLauncherConfig.has_option("CVL Launcher Preferences", "cvl_login_host"):
                self.cvlLoginHost = cvlLauncherConfig.get("CVL Launcher Preferences", "cvl_login_host")
            else:
                cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_login_host","")
                with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        else:
            cvlLauncherConfig.add_section("CVL Launcher Preferences")
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        if self.cvlLoginHost.strip()!="":
            self.cvlLoginHostComboBox.SetValue(self.cvlLoginHost)

        self.cvlVncDisplayNumberLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Display number')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlVncDisplayNumberLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlVncDisplayNumberAutomatic = True
        self.cvlVncDisplayNumber = 1
        # The following section is commented out for the following reason:
        # It is better to always default to "automatic display number",
        # i.e. always start a new VNC session on the server by default,
        # rather than remember what the user did last time.
        # If a manual choice of display number is remembered, then the
        # user could accidentally try to connect to a stale or 
        # non-existent VNC session.
        #if cvlLauncherConfig.has_section("CVL Launcher Preferences"):
            #if cvlLauncherConfig.has_option("CVL Launcher Preferences", "cvl_vnc_display_number_automatic"):
                #self.cvlVncDisplayNumberAutomatic = cvlLauncherConfig.get("CVL Launcher Preferences", "cvl_vnc_display_number_automatic")
                #if self.cvlVncDisplayNumberAutomatic.strip() == "":
                    #self.cvlVncDisplayNumberAutomatic = True
                #else:
                    #if self.cvlVncDisplayNumberAutomatic==True or self.cvlVncDisplayNumberAutomatic=='True':
                        #self.cvlVncDisplayNumberAutomatic = True
                    #else:
                        #self.cvlVncDisplayNumberAutomatic = False
            #else:
                #cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_vnc_display_number_automatic","True")
                #with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    #cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
            #if cvlLauncherConfig.has_option("CVL Launcher Preferences", "cvl_vnc_display_number"):
                #self.cvlVncDisplayNumber = cvlLauncherConfig.get("CVL Launcher Preferences", "cvl_vnc_display_number")
                #if self.cvlVncDisplayNumber.strip() == "":
                    #self.cvlVncDisplayNumber = 1
                #else:
                    #self.cvlVncDisplayNumber = int(self.cvlVncDisplayNumber)
            #else:
                #cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_vnc_display_number","1")
                #with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    #cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        #else:
            #cvlLauncherConfig.add_section("CVL Launcher Preferences")
            #with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                #cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)

        self.cvlVncDisplayNumberPanel = wx.Panel(self.cvlLoginFieldsPanel, wx.ID_ANY)
        self.cvlVncDisplayNumberPanelSizer = wx.FlexGridSizer(rows=1, cols=2, vgap=5, hgap=20)
        self.cvlVncDisplayNumberPanel.SetSizer(self.cvlVncDisplayNumberPanelSizer)

        self.cvlVncDisplayNumberAutomaticCheckBox = wx.CheckBox(self.cvlVncDisplayNumberPanel, wx.ID_ANY, "Automatic")
        self.cvlVncDisplayNumberPanelSizer.Add(self.cvlVncDisplayNumberAutomaticCheckBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_BOTTOM, border=5)
        self.cvlVncDisplayNumberSpinCtrl = wx.SpinCtrl(self.cvlVncDisplayNumberPanel, wx.ID_ANY, min=0,max=100)
        if self.cvlVncDisplayNumberAutomatic==True:
            self.cvlVncDisplayNumberAutomaticCheckBox.SetValue(True)
            self.cvlVncDisplayNumberSpinCtrl.SetValue(1)
            self.cvlVncDisplayNumberSpinCtrl.Disable()
        if self.cvlVncDisplayNumberAutomatic==False:
            self.cvlVncDisplayNumberAutomaticCheckBox.SetValue(False)
            self.cvlVncDisplayNumberSpinCtrl.SetValue(self.cvlVncDisplayNumber)
        self.cvlVncDisplayNumberPanelSizer.Add(self.cvlVncDisplayNumberSpinCtrl, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_BOTTOM, border=5)
        self.cvlVncDisplayNumberAutomaticCheckBox.Bind(wx.EVT_CHECKBOX, self.onToggleCvlVncDisplayNumberAutomaticCheckBox)

        self.cvlVncDisplayNumberPanel.SetSizerAndFit(self.cvlVncDisplayNumberPanelSizer)

        self.cvlLoginFieldsPanelSizer.Add(self.cvlVncDisplayNumberPanel, flag=wx.ALIGN_RIGHT|wx.RIGHT, border=10)


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
        if cvlLauncherConfig.has_section("CVL Launcher Preferences"):
            if cvlLauncherConfig.has_option("CVL Launcher Preferences", "cvl_vnc_display_resolution"):
                self.cvlVncDisplayResolution = cvlLauncherConfig.get("CVL Launcher Preferences", "cvl_vnc_display_resolution")
            elif cvlLauncherConfig.has_option("CVL Launcher Preferences", "resolution"):
                self.cvlVncDisplayResolution = cvlLauncherConfig.get("CVL Launcher Preferences", "resolution")
            else:
                cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_vnc_display_resolution","")
                with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        else:
            cvlLauncherConfig.add_section("CVL Launcher Preferences")
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        if self.cvlVncDisplayResolution.strip()!="":
            self.cvlVncDisplayResolutionComboBox.SetValue(self.cvlVncDisplayResolution)
        else:
            self.cvlVncDisplayResolutionComboBox.SetValue(defaultResolution)

        if self.cvlVncDisplayNumberAutomatic==False:
            self.cvlVncDisplayResolutionComboBox.Disable()
            self.cvlVncDisplayResolutionLabel.Disable()

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
        if cvlLauncherConfig.has_section("CVL Launcher Preferences"):
            if cvlLauncherConfig.has_option("CVL Launcher Preferences", "cvl_ssh_tunnel_cipher"):
                self.cvlSshTunnelCipher = cvlLauncherConfig.get("CVL Launcher Preferences", "cvl_ssh_tunnel_cipher")
            if cvlLauncherConfig.has_option("CVL Launcher Preferences", "cipher"):
                self.cvlSshTunnelCipher = cvlLauncherConfig.get("CVL Launcher Preferences", "cipher")
            else:
                cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_ssh_tunnel_cipher","")
                with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        else:
            cvlLauncherConfig.add_section("CVL Launcher Preferences")
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        if self.cvlSshTunnelCipher.strip()!="":
            self.cvlSshTunnelCipherComboBox.SetValue(self.cvlSshTunnelCipher)
        else:
            self.cvlSshTunnelCipherComboBox.SetValue(defaultCipher)

        self.cvlUsernameLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Username')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlUsernameLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlUsername = ""
        if cvlLauncherConfig.has_section("CVL Launcher Preferences"):
            if cvlLauncherConfig.has_option("CVL Launcher Preferences", "cvl_username"):
                self.cvlUsername = cvlLauncherConfig.get("CVL Launcher Preferences", "cvl_username")
            else:
                cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_username","")
                with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        else:
            cvlLauncherConfig.add_section("CVL Launcher Preferences")
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        self.cvlUsernameTextField = wx.TextCtrl(self.cvlLoginFieldsPanel, wx.ID_ANY, self.cvlUsername, size=(widgetWidth1, -1))
        self.cvlLoginFieldsPanelSizer.Add(self.cvlUsernameTextField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=8)
        if self.cvlUsername.strip()!="":
            self.cvlUsernameTextField.SelectAll()

        self.cvlPasswordLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Password')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlPasswordLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlPassword = ""
        self.cvlPasswordField = wx.TextCtrl(self.cvlLoginFieldsPanel, wx.ID_ANY, self.cvlPassword, size=(widgetWidth1, -1), style=wx.TE_PASSWORD)
        self.cvlLoginFieldsPanelSizer.Add(self.cvlPasswordField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=8)

        self.cvlVncDisplayNumberPanel.MoveAfterInTabOrder(self.cvlLoginHostComboBox)
        self.cvlVncDisplayNumberPanel.MoveAfterInTabOrder(self.cvlVncDisplayNumberPanel)
        self.cvlVncDisplayResolutionComboBox.MoveAfterInTabOrder(self.cvlVncDisplayNumberPanel)
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

        OPTIONS_BUTTON_ID = 1
        self.optionsButton = wx.Button(self.buttonsPanel, OPTIONS_BUTTON_ID, 'Options...')
        self.buttonsPanelSizer.Add(self.optionsButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)

        CANCEL_BUTTON_ID = 2
        self.cancelButton = wx.Button(self.buttonsPanel, CANCEL_BUTTON_ID, 'Cancel')
        self.buttonsPanelSizer.Add(self.cancelButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)

        LOGIN_BUTTON_ID = 3
        self.loginButton = wx.Button(self.buttonsPanel, LOGIN_BUTTON_ID, 'Login')
        self.buttonsPanelSizer.Add(self.loginButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)

        self.buttonsPanel.SetSizerAndFit(self.buttonsPanelSizer)

        self.loginDialogPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=15)

        self.loginButton.SetDefault()

        self.Bind(wx.EVT_BUTTON, self.onOptions, id=OPTIONS_BUTTON_ID)
        self.Bind(wx.EVT_BUTTON, self.onCancel,  id=CANCEL_BUTTON_ID)
        self.Bind(wx.EVT_BUTTON, self.onLogin,   id=LOGIN_BUTTON_ID)

        self.loginDialogStatusBar = LauncherStatusBar(self)
        self.SetStatusBar(self.loginDialogStatusBar)

        self.loginDialogPanel.SetSizerAndFit(self.loginDialogPanelSizer)
        self.loginDialogPanel.Layout()

        self.Fit()
        self.Layout()

        self.Centre()

        #launcherURL = "https://www.massive.org.au/index.php?option=com_content&view=article&id=121"
        launcherURL = "https://www.massive.org.au/userguide/cluster-instructions/massive-launcher"

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


        latestVersionNumber = myHtmlParser.latestVersionNumber
        htmlComments = myHtmlParser.htmlComments
        htmlCommentsSplit1 = htmlComments.split("<pre id=\"CHANGES\">")
        htmlCommentsSplit2 = htmlCommentsSplit1[1].split("</pre>")
        latestVersionChanges = htmlCommentsSplit2[0].strip()

        if latestVersionNumber!=launcher_version_number.version_number:
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

            newVersionAlertPanel = wx.Panel(newVersionAlertDialog)

            newVersionAlertPanelSizer = wx.FlexGridSizer(rows=8, cols=1, vgap=5, hgap=5)
            newVersionAlertPanel.SetSizer(newVersionAlertPanelSizer)

            newVersionAlertTitleLabel = wx.StaticText(newVersionAlertPanel,
                label = "MASSIVE/CVL Launcher")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetPointSize(14)
            font.SetWeight(wx.BOLD)
            newVersionAlertTitleLabel.SetFont(font)
            newVersionAlertPanelSizer.Add(wx.StaticText(newVersionAlertPanel))
            newVersionAlertPanelSizer.Add(newVersionAlertTitleLabel, flag=wx.EXPAND)
            newVersionAlertPanelSizer.Add(wx.StaticText(newVersionAlertPanel))

            newVersionAlertTextLabel1 = wx.StaticText(newVersionAlertPanel, 
                label = 
                "You are running version " + launcher_version_number.version_number + "\n\n" +
                "The latest version is " + latestVersionNumber + "\n\n" +
                "Please download a new version from:\n\n")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(9)
            newVersionAlertTextLabel1.SetFont(font)
            newVersionAlertPanelSizer.Add(newVersionAlertTextLabel1, flag=wx.EXPAND)

            newVersionAlertHyperlink = wx.HyperlinkCtrl(newVersionAlertPanel, 
                id = wx.ID_ANY,
                label = launcherURL,
                url = launcherURL)
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(8)
            newVersionAlertHyperlink.SetFont(font)
            newVersionAlertPanelSizer.Add(newVersionAlertHyperlink, border=10, flag=wx.LEFT|wx.BORDER)
            newVersionAlertPanelSizer.Add(wx.StaticText(newVersionAlertPanel))

            self.latestVersionChangesTextCtrl = wx.TextCtrl(newVersionAlertPanel, 
                size=(600, 200), style=wx.TE_MULTILINE|wx.TE_READONLY)
            newVersionAlertPanelSizer.Add(self.latestVersionChangesTextCtrl, flag=wx.EXPAND)
            if sys.platform.startswith("darwin"):
                font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
            else:
                font = wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
            self.latestVersionChangesTextCtrl.SetFont(font)
            self.latestVersionChangesTextCtrl.AppendText(latestVersionChanges)
            self.latestVersionChangesTextCtrl.SetInsertionPoint(0)

            newVersionAlertPanelSizer.Add(wx.StaticText(newVersionAlertPanel, wx.ID_ANY, ""))
            newVersionAlertQueriesContactLabel = wx.StaticText(newVersionAlertPanel, 
                label = 
                "For queries, please contact:")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(9)
            newVersionAlertQueriesContactLabel.SetFont(font)
            newVersionAlertPanelSizer.Add(newVersionAlertQueriesContactLabel, border=10, flag=wx.EXPAND|wx.BORDER)

            contactEmailHyperlink = wx.HyperlinkCtrl(newVersionAlertPanel, 
                id = wx.ID_ANY,
                label = "help@massive.org.au",
                url = "mailto:help@massive.org.au")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(8)
            contactEmailHyperlink.SetFont(font)
            newVersionAlertPanelSizer.Add(contactEmailHyperlink, border=20, flag=wx.LEFT|wx.BORDER)

            contactEmail2Hyperlink = wx.HyperlinkCtrl(newVersionAlertPanel, 
                id = wx.ID_ANY,
                label = "James.Wettenhall@monash.edu",
                url = "mailto:James.Wettenhall@monash.edu")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            if sys.platform.startswith("darwin"):
                font.SetPointSize(11)
            else:
                font.SetPointSize(8)
            contactEmail2Hyperlink.SetFont(font)
            newVersionAlertPanelSizer.Add(contactEmail2Hyperlink, border=20, flag=wx.LEFT|wx.BORDER)

            def onOK(event):
                sys.exit(1)

            okButton = wx.Button(newVersionAlertPanel, 1, ' OK ')
            okButton.SetDefault()
            newVersionAlertPanelSizer.Add(okButton, flag=wx.ALIGN_RIGHT)
            newVersionAlertPanelSizer.Add(wx.StaticText(newVersionAlertPanel))
            newVersionAlertPanelSizer.Fit(newVersionAlertPanel)

            newVersionAlertDialog.Bind(wx.EVT_BUTTON, onOK, id=1)

            newVersionAlertDialogSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=5, hgap=5)
            newVersionAlertDialogSizer.Add(massiveIconPanel, flag=wx.EXPAND)
            newVersionAlertDialogSizer.Add(newVersionAlertPanel, flag=wx.EXPAND)
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

    def onToggleCvlVncDisplayNumberAutomaticCheckBox(self, event):
        if self.cvlVncDisplayNumberAutomaticCheckBox.GetValue()==True:
            self.cvlVncDisplayNumberSpinCtrl.Disable()
            self.cvlVncDisplayResolutionComboBox.Enable()
            self.cvlVncDisplayResolutionLabel.Enable()
        else:
            self.cvlVncDisplayNumberSpinCtrl.Enable()
            self.cvlVncDisplayResolutionComboBox.Disable()
            self.cvlVncDisplayResolutionLabel.Disable()

    def onOptions(self, event):

        import turboVncOptions

        if len(self.vncOptions)==0:
            if turboVncConfig.has_section("TurboVNC Preferences"):
                savedTurboVncOptions =  turboVncConfig.items("TurboVNC Preferences")
                for option in savedTurboVncOptions:
                    key = option[0]
                    value = option[1]
                    if value=='True':
                        value = True
                    if value=='False':
                        value = False
                    self.vncOptions[key] = value

        turboVncOptionsDialog = turboVncOptions.TurboVncOptions(launcherMainFrame, wx.ID_ANY, "TurboVNC Viewer Options", self.vncOptions)
        turboVncOptionsDialog.ShowModal()

        if turboVncOptionsDialog.okClicked:
            self.vncOptions = turboVncOptionsDialog.getVncOptions()

            for key in self.vncOptions:
                turboVncConfig.set("TurboVNC Preferences", key, self.vncOptions[key])

            with open(turboVncPreferencesFilePath, 'wb') as turboVncPreferencesFileObject:
                turboVncConfig.write(turboVncPreferencesFileObject)

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

        self.cvlLoginHostComboBox.SetCursor(cursor)
        self.cvlUsernameTextField.SetCursor(cursor)
        self.cvlPasswordField.SetCursor(cursor)
        self.cvlVncDisplayResolutionComboBox.SetCursor(cursor)
        self.cvlSshTunnelCipherComboBox.SetCursor(cursor)

        self.buttonsPanel.SetCursor(cursor)
        self.optionsButton.SetCursor(cursor)
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
                    
                    # Check for TurboVNC

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
                                # 64-bit Windows installation, 64-bit TurboVNC, HKEY_CURRENT_USER
                                key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC 64-bit_is1", 0,  _winreg.KEY_WOW64_64KEY | _winreg.KEY_READ)
                                queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                                queryResult = _winreg.QueryValueEx(key, "DisplayVersion") 
                                self.turboVncVersionNumber = queryResult[0]
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False
                                #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                                #wx.CallAfter(sys.stdout.write, traceback.format_exc())
                        if not foundTurboVncInRegistry:
                            try:
                                # 64-bit Windows installation, 64-bit TurboVNC, HKEY_LOCAL_MACHINE
                                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC 64-bit_is1", 0,  _winreg.KEY_WOW64_64KEY | _winreg.KEY_READ)
                                queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                                queryResult = _winreg.QueryValueEx(key, "DisplayVersion") 
                                self.turboVncVersionNumber = queryResult[0]
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False
                                #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                                #wx.CallAfter(sys.stdout.write, traceback.format_exc())
                        if not foundTurboVncInRegistry:
                            try:
                                # 32-bit Windows installation, 32-bit TurboVNC, HKEY_CURRENT_USER
                                key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_READ)
                                queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                                queryResult = _winreg.QueryValueEx(key, "DisplayVersion") 
                                self.turboVncVersionNumber = queryResult[0]
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False
                                #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                                #wx.CallAfter(sys.stdout.write, traceback.format_exc())
                        if not foundTurboVncInRegistry:
                            try:
                                # 32-bit Windows installation, 32-bit TurboVNC, HKEY_LOCAL_MACHINE
                                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_READ)
                                queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                                queryResult = _winreg.QueryValueEx(key, "DisplayVersion") 
                                self.turboVncVersionNumber = queryResult[0]
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False
                                #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                                #wx.CallAfter(sys.stdout.write, traceback.format_exc())
                        if not foundTurboVncInRegistry:
                            try:
                                # 64-bit Windows installation, 32-bit TurboVNC, HKEY_CURRENT_USER
                                key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_WOW64_32KEY | _winreg.KEY_READ)
                                queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                                queryResult = _winreg.QueryValueEx(key, "DisplayVersion") 
                                self.turboVncVersionNumber = queryResult[0]
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False
                                #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                                #wx.CallAfter(sys.stdout.write, traceback.format_exc())
                        if not foundTurboVncInRegistry:
                            try:
                                # 64-bit Windows installation, 32-bit TurboVNC, HKEY_LOCAL_MACHINE
                                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_WOW64_32KEY | _winreg.KEY_READ)
                                queryResult = _winreg.QueryValueEx(key, "InstallLocation") 
                                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                                queryResult = _winreg.QueryValueEx(key, "DisplayVersion") 
                                self.turboVncVersionNumber = queryResult[0]
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False
                                #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                                #wx.CallAfter(sys.stdout.write, traceback.format_exc())

                    if os.path.exists(vnc):
                        wx.CallAfter(sys.stdout.write, "TurboVNC was found in " + vnc + "\n")
                    else:
                        wx.CallAfter(sys.stdout.write, "Error: TurboVNC was not found in: " + vnc + "\n")
                        dlg = wx.MessageDialog(launcherMainFrame, "Error: TurboVNC was not found in:\n\n" + 
                                                    "    " + vnc + "\n\n" +
                                                    "The launcher cannot continue.\n",
                                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                        dlg.ShowModal()
                        dlg.Destroy()
                        try:
                            os.unlink(self.privateKeyFile.name)
                            self.sshTunnelProcess.terminate()
                            self.sshClient.exec_command("exit")
                            self.sshClient.close()
                        finally:
                            os._exit(1)

                    wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Logging in to " + self.host)
                    wx.CallAfter(sys.stdout.write, "Attempting to log in to " + self.host + "...\n")
                    
                    self.sshClient = ssh.SSHClient()
                    self.sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())
                    self.sshClient.connect(self.host,username=self.username,password=self.password)

                    wx.CallAfter(sys.stdout.write, "First login done.\n")

                    wx.CallAfter(sys.stdout.write, "\n")

                    self.cvlVncDisplayNumber = launcherMainFrame.cvlVncDisplayNumber

                    if launcherMainFrame.massiveTabSelected:
                        self.massiveVisNodes = []
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Setting display resolution...")

                        set_display_resolution_cmd = "/usr/local/desktop/set_display_resolution.sh " + self.resolution
                        wx.CallAfter(sys.stdout.write, set_display_resolution_cmd + "\n")
                        stdin,stdout,stderr = self.sshClient.exec_command(set_display_resolution_cmd)
                        stderrRead = stderr.read()
                        if len(stderrRead) > 0:
                            wx.CallAfter(sys.stdout.write, stderrRead)
                        
                        wx.CallAfter(sys.stdout.write, "\n")

                        # Begin if launcherMainFrame.massiveTabSelected:

                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Checking quota...")

                        stdin,stdout,stderr = self.sshClient.exec_command("mybalance --hours")
                        wx.CallAfter(sys.stdout.write, stderr.read())
                        wx.CallAfter(sys.stdout.write, stdout.read())

                        wx.CallAfter(sys.stdout.write, "\n")

                        stdin,stdout,stderr = self.sshClient.exec_command("echo `showq -w class:vis | grep \"processors in use by local jobs\" | awk '{print $1}'` of 10 nodes in use")
                        wx.CallAfter(sys.stdout.write, stderr.read())
                        wx.CallAfter(sys.stdout.write, stdout.read())

                        wx.CallAfter(sys.stdout.write, "\n")

                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Requesting remote desktop...")

                        #qsubcmd = "qsub -A " + self.massiveProject + " -I -q vis -l walltime=" + launcherMainFrame.massiveHoursRequested + ":0:0,nodes=1:ppn=12:gpus=2,pmem=16000MB"
                        #qsubcmd = "/usr/local/desktop/request_visnode.sh " + launcherMainFrame.massiveProject + " " + launcherMainFrame.massiveHoursRequested
                        qsubcmd = "/usr/local/desktop/request_visnode.sh " + launcherMainFrame.massiveProject + " " + launcherMainFrame.massiveHoursRequested + " " + launcherMainFrame.massiveVisNodesRequested

                        wx.CallAfter(sys.stdout.write, qsubcmd + "\n")
                        wx.CallAfter(sys.stdout.write, "\n")
                    
                        # We will open a channel to allow us to monitor output from qsub,
                        # even before the "qsub" command has finished running. 

                        # From: http://www.lag.net/paramiko/docs/paramiko.Channel-class.html#recv_stderr_ready
                        # "Only channels using exec_command or invoke_shell without a pty 
                        #  will ever have data on the stderr stream."
 
                        transport = self.sshClient.get_transport()
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
                                    launcherMainFrame.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
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
                                    if "ERROR" in line or "Error" in line or "error" in line:
                                        wx.CallAfter(sys.stdout.write, line)
                                        launcherMainFrame.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))
                                    if "waiting for job" in line:
                                        wx.CallAfter(sys.stdout.write, line)
                                        lineSplit = line.split(" ")
                                        jobNumber = lineSplit[4] # e.g. 3050965.m2-m
                                        jobNumberSplit = jobNumber.split(".")
                                        jobNumber = jobNumberSplit[0]
                                    if "Starting XServer on the following nodes" in line:
                                        startingXServerLineNumber = lineNumber
                                    if startingXServerLineNumber!=-1 and \
                                            lineNumber >= (startingXServerLineNumber+1) and \
                                            lineNumber <= (startingXServerLineNumber+int(launcherMainFrame.massiveVisNodesRequested)): # vis nodes
                                        #wx.CallAfter(sys.stdout.write, "VISNODE LINE: " + line + "\n");
                                        visnode = line.strip()
                                        self.massiveVisNodes.append(visnode)
                                        if lineNumber==startingXServerLineNumber+int(launcherMainFrame.massiveVisNodesRequested):
                                            breakOutOfMainLoop = True
                                    line = buff.readline()
                            if breakOutOfMainLoop:
                                break

                        #wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Acquired desktop node:" + visnode)
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Acquired desktop node:" + self.massiveVisNodes[0])

                        
                        wx.CallAfter(sys.stdout.write, "\nMassive Desktop visnode")
                        if int(launcherMainFrame.massiveVisNodesRequested)>1:
                            wx.CallAfter(sys.stdout.write, "s: ")
                        else:
                            wx.CallAfter(sys.stdout.write, ": ")

                        for visNodeNumber in range(0,int(launcherMainFrame.massiveVisNodesRequested)):
                            wx.CallAfter(sys.stdout.write, self.massiveVisNodes[visNodeNumber] + " ")

                        wx.CallAfter(sys.stdout.write, "\n\n")

                        # End if launcherMainFrame.massiveTabSelected:
                    else:
                        self.cvlVncDisplayNumber = launcherMainFrame.cvlVncDisplayNumber
                        if launcherMainFrame.cvlVncDisplayNumberAutomatic==True:
                            cvlVncServerCommand = "vncsession --vnc tigervnc --geometry \"" + launcherMainFrame.cvlVncDisplayResolution + "\""
                            if launcherMainFrame.cvlVncDisplayNumberAutomatic==False:
                                cvlVncServerCommand = cvlVncServerCommand + " --display " + str(self.cvlVncDisplayNumber)
                            wx.CallAfter(sys.stdout.write, cvlVncServerCommand + "\n")
                            stdin,stdout,stderr = self.sshClient.exec_command(cvlVncServerCommand)
                            stderrRead = stderr.read()
                            wx.CallAfter(sys.stdout.write, stderrRead)
                            stdoutRead = stdout.read()
                            wx.CallAfter(sys.stdout.write, stdoutRead)
                            lines = stderrRead.split("\n")
                            foundDisplayNumber = False
                            for line in lines:
                                if "desktop is" in line:
                                    lineComponents = line.split(":")
                                    # An extra parsing step is required for TigerVNC server output, compared with TurboVNC
                                    displayComponents = lineComponents[1].split(" ")
                                    self.cvlVncDisplayNumber = int(displayComponents[0])
                                    foundDisplayNumber = True

                        if launcherMainFrame.cvlVncDisplayNumberAutomatic==False:
                            wx.CallAfter(sys.stdout.write, "CVL VNC Display Number is " + str(self.cvlVncDisplayNumber) + "\n")
                        if launcherMainFrame.cvlVncDisplayNumberAutomatic==True:
                            if foundDisplayNumber:
                                wx.CallAfter(sys.stdout.write, "CVL VNC Display Number is " + str(self.cvlVncDisplayNumber) + "\n")
                                launcherMainFrame.cvlVncDisplayNumberSpinCtrl.SetValue(int(self.cvlVncDisplayNumber))
                            else:
                                wx.CallAfter(sys.stdout.write, "Failed to parse vncserver output for display number.\n")

                        wx.CallAfter(sys.stdout.write, "\n")

                    wx.CallAfter(sys.stdout.write, "Generating SSH key-pair for tunnel...\n\n")

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Generating SSH key-pair for tunnel...")

                    stdin,stdout,stderr = self.sshClient.exec_command("/bin/rm -f ~/MassiveLauncherKeyPair*")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = self.sshClient.exec_command("/usr/bin/ssh-keygen -C \"MASSIVE Launcher\" -N \"\" -t rsa -f ~/MassiveLauncherKeyPair")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = self.sshClient.exec_command("/bin/mkdir -p ~/.ssh")
                    stdin,stdout,stderr = self.sshClient.exec_command("/bin/chmod 700 ~/.ssh")
                    stdin,stdout,stderr = self.sshClient.exec_command("/bin/touch ~/.ssh/authorized_keys")
                    stdin,stdout,stderr = self.sshClient.exec_command("/bin/chmod 600 ~/.ssh/authorized_keys")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = self.sshClient.exec_command("/bin/sed -i -e \"/MASSIVE Launcher/d\" ~/.ssh/authorized_keys")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = self.sshClient.exec_command("/bin/cat MassiveLauncherKeyPair.pub >> ~/.ssh/authorized_keys")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = self.sshClient.exec_command("/bin/rm -f ~/MassiveLauncherKeyPair.pub")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())
                    stdin,stdout,stderr = self.sshClient.exec_command("/bin/cat MassiveLauncherKeyPair")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())

                    privateKeyString = stdout.read()

                    stdin,stdout,stderr = self.sshClient.exec_command("/bin/rm -f ~/MassiveLauncherKeyPair")
                    if len(stderr.read()) > 0:
                        wx.CallAfter(sys.stdout.write, stderr.read())

                    import tempfile
                    self.privateKeyFile = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
                    self.privateKeyFile.write(privateKeyString)
                    self.privateKeyFile.flush()
                    self.privateKeyFile.close()

                    def createTunnel(localPortNumber,remoteHost,remotePortNumber,tunnelServer,tunnelUsername,tunnelPrivateKeyFileName):
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
                                chown_cmd = chownBinary + " \"" + getpass.getuser() + "\" " + tunnelPrivateKeyFileName
                                wx.CallAfter(sys.stdout.write, chown_cmd + "\n")
                                subprocess.call(chown_cmd, shell=True)

                            chmod_cmd = chmodBinary + " 600 " + tunnelPrivateKeyFileName
                            wx.CallAfter(sys.stdout.write, chmod_cmd + "\n")
                            subprocess.call(chmod_cmd, shell=True)

                            localPortNumber = str(localPortNumber)

                            if localPortNumber=="0":
                                # Request an ephemeral port from the operating system (by specifying port 0) :
                                wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Requesting ephemeral port...")
                                import socket
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
                                sock.bind(('localhost', 0)) 
                                localPortNumber = sock.getsockname()[1]
                                sock.close()
                                localPortNumber = str(localPortNumber)

                            launcherMainFrame.loginThread.localPortNumber = localPortNumber

                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Creating secure tunnel...")

                            remotePortNumber = str(remotePortNumber)

                            tunnel_cmd = sshBinary + " -i " + tunnelPrivateKeyFileName + " -c " + self.cipher + " " \
                                "-t -t " \
                                "-oStrictHostKeyChecking=no " \
                                "-L " + localPortNumber + ":" + remoteHost + ":" + remotePortNumber + " -l " + tunnelUsername + " " + tunnelServer

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

                        except KeyboardInterrupt:
                            wx.CallAfter(sys.stdout.write, "C-c: Port forwarding stopped.")
                            try:
                                os.unlink(tunnelPrivateKeyFileName)
                            finally:
                                os._exit(0)
                        except:
                            wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                            wx.CallAfter(sys.stdout.write, traceback.format_exc())

                    self.sshTunnelReady = False
                    localPortNumber = "0" # Request ephemeral port.
                    tunnelServer = self.host
                    tunnelUsername = self.username
                    tunnelPrivateKeyFileName = self.privateKeyFile.name
                    if launcherMainFrame.massiveTabSelected:
                        remoteHost = self.massiveVisNodes[0] + "-ib"
                        remotePortNumber = "5901"
                    else:
                        remoteHost = "localhost"
                        remotePortNumber = str(5900+self.cvlVncDisplayNumber)
                    tunnelThread = threading.Thread(target=createTunnel, args=(localPortNumber,remoteHost,remotePortNumber,tunnelServer,tunnelUsername,tunnelPrivateKeyFileName))

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Creating secure tunnel...")

                    tunnelThread.start()

                    count = 1
                    while not self.sshTunnelReady and count < 30:
                        time.sleep(1)
                        count = count + 1

                    if count < 5:
                        time.sleep(5-count)

                    self.turboVncStartTime = datetime.datetime.now()

                    # TurboVNC

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Launching TurboVNC...")

                    if launcherMainFrame.massiveTabSelected:
                        wx.CallAfter(sys.stdout.write, "\nStarting MASSIVE VNC...\n")
                    if launcherMainFrame.cvlTabSelected:
                        wx.CallAfter(sys.stdout.write, "\nStarting CVL VNC...\n")

                    try:
                        if sys.platform.startswith("win"):
                            optionPrefixCharacter = "/"
                        else:
                            optionPrefixCharacter = "-"
                        vncOptionsString = ""

                        # This is necessary to avoid confusion arising from connecting to localhost::[port] after creating SSH tunnel.
                        # In this case, the X11 version of TurboVNC assumes that the client and server are the same computer:
                        # "Same machine: preferring raw encoding"
                        if not sys.platform.startswith("win"):
                            vncOptionsString = "-encodings \"tight copyrect\""

                        if 'jpeg_compression' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['jpeg_compression']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "nojpeg"
                        defaultJpegChrominanceSubsampling = "1x"
                        if 'jpeg_chrominance_subsampling' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['jpeg_chrominance_subsampling']!=defaultJpegChrominanceSubsampling:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "samp " + launcherMainFrame.vncOptions['jpeg_chrominance_subsampling']
                        defaultJpegImageQuality = "95"
                        if 'jpeg_image_quality' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['jpeg_image_quality']!=defaultJpegImageQuality:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "quality " + launcherMainFrame.vncOptions['jpeg_image_quality']
                        if 'zlib_compression_enabled' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['zlib_compression_enabled']==True:
                            if 'zlib_compression_level' in launcherMainFrame.vncOptions:
                                vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "compresslevel " + launcherMainFrame.vncOptions['zlib_compression_level']
                        if 'view_only' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['view_only']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "viewonly"
                        if 'disable_clipboard_transfer' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['disable_clipboard_transfer']==True:
                            if sys.platform.startswith("win"):
                                vncOptionsString = vncOptionsString + " /disableclipboard"
                            #else:
                                #vncOptionsString = vncOptionsString + " -noclipboardsend -noclipboardrecv"
                        if sys.platform.startswith("win"):
                            if 'scale' in launcherMainFrame.vncOptions:
                                if launcherMainFrame.vncOptions['scale']=="Auto":
                                    vncOptionsString = vncOptionsString + " /fitwindow"
                                else:
                                    vncOptionsString = vncOptionsString + " /scale " + launcherMainFrame.vncOptions['scale']
                            defaultSpanMode = 'automatic'
                            if 'span' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['span']!=defaultSpanMode:
                                vncOptionsString = vncOptionsString + " /span " + launcherMainFrame.vncOptions['span']
                        if 'double_buffering' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['double_buffering']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "singlebuffer"
                        if 'full_screen_mode' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['full_screen_mode']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "fullscreen"
                        if 'deiconify_on_remote_bell_event' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['deiconify_on_remote_bell_event']==False:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "noraiseonbeep"
                        if sys.platform.startswith("win"):
                            if 'emulate3' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['emulate3']==True:
                                vncOptionsString = vncOptionsString + " /emulate3"
                            if 'swapmouse' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['swapmouse']==True:
                                vncOptionsString = vncOptionsString + " /swapmouse"
                        if 'dont_show_remote_cursor' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['dont_show_remote_cursor']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "nocursorshape"
                        elif 'let_remote_server_deal_with_mouse_cursor' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['let_remote_server_deal_with_mouse_cursor']==True:
                            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "x11cursor"
                        if 'request_shared_session' in launcherMainFrame.vncOptions and launcherMainFrame.vncOptions['request_shared_session']==False:
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

                        if not sys.platform.startswith("win"):
                            turboVncVersionNumberCommandString = vnc + " -help"
                            proc = subprocess.Popen(turboVncVersionNumberCommandString, 
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                universal_newlines=True)
                            turboVncStdout, turboVncStderr = proc.communicate(input=self.password + "\n")
                            if turboVncStderr != None:
                                wx.CallAfter(sys.stdout.write, turboVncStderr)
                            turboVncVersionNumberComponents = turboVncStdout.split(" v")
                            turboVncVersionNumberComponents = turboVncVersionNumberComponents[1].split(" ")
                            self.turboVncVersionNumber = turboVncVersionNumberComponents[0]

                        wx.CallAfter(sys.stdout.write, "TurboVNC viewer version number = " + self.turboVncVersionNumber + "\n")

                        if self.turboVncVersionNumber.startswith("0.") or self.turboVncVersionNumber.startswith("1.0"):
                            dlg = wx.MessageDialog(launcherMainFrame, "Warning: Using a TurboVNC viewer earlier than v1.1 means that you will need to enter your password twice.\n",
                                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                            dlg.ShowModal()
                            dlg.Destroy()
                        if sys.platform.startswith("win"):
                            vncCommandString = "\""+vnc+"\" /user "+self.username+" /autopass " + vncOptionsString + " localhost::" + launcherMainFrame.loginThread.localPortNumber
                            wx.CallAfter(sys.stdout.write, vncCommandString + "\n")
                            proc = subprocess.Popen(vncCommandString, 
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                universal_newlines=True)
                            turboVncStdout, turboVncStderr = proc.communicate(input=self.password + "\r\n")
                        else:
                            vncCommandString = vnc + " -user " + self.username + " -autopass " + vncOptionsString + " localhost::" + launcherMainFrame.loginThread.localPortNumber
                            wx.CallAfter(sys.stdout.write, vncCommandString + "\n")
                            proc = subprocess.Popen(vncCommandString, 
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                universal_newlines=True)
                            turboVncStdout, turboVncStderr = proc.communicate(input=self.password + "\n")

                        if sys.platform.startswith("darwin"):
                            # Grab focus back from X11, i.e. reactive MASSIVE Launcher app.
                            subprocess.Popen(['osascript', '-e', 
                                "tell application \"System Events\"\r" +
                                "  set procName to name of first process whose unix id is " + str(os.getpid()) + "\r" +
                                "end tell\r" +
                                "tell application procName to activate\r"])

                        self.turboVncFinishTime = datetime.datetime.now()

                        # Below, we display the TurboVNC viewer's STDERR in the Log window.
                        # If the Launcher can accurately determine that the TurboVNC viewer 
                        # encountered a critical error, it will remain open long enough for
                        # the user to be able to view any error messages in the Launcher's
                        # Log window, instead of automatically exiting.
                        if turboVncStderr != None and turboVncStderr.strip()!="":
                            wx.CallAfter(sys.stdout.write, turboVncStderr)

                        # If the TurboVNC viewer return an exit code, indicating that an 
                        # error occurred (this only works in the Mac and Linux version of 
                        # TurboVNC at present), display the TurboVNC viewer's STDOUT in 
                        # the Launcher's Log window (as well as STDERR).
                        if proc.returncode != 0:
                            wx.CallAfter(sys.stdout.write, turboVncStdout)

                        try:
                            if launcherMainFrame.cvlTabSelected:
                                if launcherMainFrame.cvlVncDisplayNumberAutomatic:
                                    import questionDialog
                                    result = questionDialog.questionDialog("Do you want to keep your VNC session (Display #" + str(self.cvlVncDisplayNumber) + ") running for future use?",
                                        #buttons=["Discard VNC Session", wx.ID_CANCEL, "Save VNC Session"])
                                        buttons=["Discard VNC Session", "Save VNC Session"],
                                        caption="MASSIVE/CVL Launcher")
                                    if result == "Discard VNC Session":
                                        cvlVncSessionStopCommand = "vncsession stop " + str(self.cvlVncDisplayNumber)
                                        wx.CallAfter(sys.stdout.write, cvlVncSessionStopCommand + "\n")
                                    self.turboVncFinishTime = datetime.datetime.now()
                                    # Earlier sshClient connection may have timed out by now.
                                    sshClient2 = ssh.SSHClient()
                                    sshClient2.set_missing_host_key_policy(ssh.AutoAddPolicy())
                                    sshClient2.connect(self.host,username=self.username,password=self.password)
                                    stdin,stdout,stderr = sshClient2.exec_command(cvlVncSessionStopCommand)
                                    wx.CallAfter(sys.stdout.write, stderr.read())
                                    wx.CallAfter(sys.stdout.write, stdout.read())
                                    sshClient2.close()
                                else:
                                    wx.CallAfter(sys.stdout.write, "Don't need to stop vnc session.\n")

                            os.unlink(self.privateKeyFile.name)
                            self.sshTunnelProcess.terminate()

                        finally:
                            # If the TurboVNC process completed less than 3 seconds after it started,
                            # then the Launcher assumes that something went wrong, so it will
                            # remain open to display any STDERR from TurboVNC in its Log window,
                            # rather than automatically exiting. This technique is most useful for
                            # the Mac / Linux (X11) version of TurboVNC.  On Windows, the TurboVNC
                            # viewer may display an error message in a message dialog for longer 
                            # than 3 seconds.
                            turboVncElapsedTime = self.turboVncFinishTime - self.turboVncStartTime
                            turboVncElapsedTimeInSeconds = turboVncElapsedTime.total_seconds()
                            if turboVncElapsedTimeInSeconds>=3 and proc.returncode==0 and (turboVncStderr==None or turboVncStderr.strip()==""):
                                os._exit(0)
                            elif turboVncElapsedTimeInSeconds<3:
                                wx.CallAfter(sys.stdout.write, "Disabling auto-quit because TurboVNC's elapsed time is less than 3 seconds.\n")

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
            self.massiveVisNodesRequested = str(self.massiveVisNodesField.GetValue())
            self.massiveProject = self.massiveProjectComboBox.GetValue()
            if self.massiveProject == self.defaultProjectPlaceholder:
                xmlrpcServer = xmlrpclib.Server("https://m2-web.massive.org.au/kgadmin/xmlrpc/")
                # Get list of user's massiveProjects from Karaage:
                # users_massiveProjects = xmlrpcServer.get_users_massiveProjects(self.massiveUsername, self.massivePassword)
                # massiveProjects = users_massiveProjects[1]
                # Get user's default massiveProject from Karaage:
                self.massiveProject = xmlrpcServer.get_project(self.massiveUsername)
                self.massiveProjectComboBox.SetValue(self.massiveProject)

        if launcherMainFrame.cvlTabSelected:
            self.cvlVncDisplayNumberAutomatic = self.cvlVncDisplayNumberAutomaticCheckBox.GetValue()
            self.cvlVncDisplayNumber = self.cvlVncDisplayNumberSpinCtrl.GetValue()

        if launcherMainFrame.massiveTabSelected:
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_login_host", self.massiveLoginHost)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_username", self.massiveUsername)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_vnc_display_resolution", self.massiveVncDisplayResolution)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_ssh_tunnel_cipher", self.massiveSshTunnelCipher)
        else:
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_login_host", self.cvlLoginHost)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_vnc_display_number_automatic", self.cvlVncDisplayNumberAutomatic)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_vnc_display_number", self.cvlVncDisplayNumber)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_username", self.cvlUsername)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_vnc_display_resolution", self.cvlVncDisplayResolution)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_ssh_tunnel_cipher", self.cvlSshTunnelCipher)

        if launcherMainFrame.massiveTabSelected:
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_project", self.massiveProject)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_hours_requested", self.massiveHoursRequested)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_visnodes_requested", self.massiveVisNodesRequested)

        if launcherMainFrame.massiveTabSelected:
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)

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

        global massiveLauncherConfig
        massiveLauncherConfig = ConfigParser.RawConfigParser(allow_no_value=True)

        global massiveLauncherPreferencesFilePath
        massiveLauncherPreferencesFilePath = os.path.join(appUserDataDir,"MASSIVE Launcher Preferences.cfg")
        if os.path.exists(massiveLauncherPreferencesFilePath):
            massiveLauncherConfig.read(massiveLauncherPreferencesFilePath)
        if not massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")

        global cvlLauncherConfig
        cvlLauncherConfig = ConfigParser.RawConfigParser(allow_no_value=True)

        global cvlLauncherPreferencesFilePath
        cvlLauncherPreferencesFilePath = os.path.join(appUserDataDir,"CVL Launcher Preferences.cfg")
        if os.path.exists(cvlLauncherPreferencesFilePath):
            cvlLauncherConfig.read(cvlLauncherPreferencesFilePath)
        if not cvlLauncherConfig.has_section("CVL Launcher Preferences"):
            cvlLauncherConfig.add_section("CVL Launcher Preferences")

        global turboVncConfig
        turboVncConfig = ConfigParser.RawConfigParser(allow_no_value=True)

        global turboVncPreferencesFilePath
        turboVncPreferencesFilePath = os.path.join(appUserDataDir,"TurboVNC Preferences.cfg")
        if os.path.exists(turboVncPreferencesFilePath):
            turboVncConfig.read(turboVncPreferencesFilePath)
        if not turboVncConfig.has_section("TurboVNC Preferences"):
            turboVncConfig.add_section("TurboVNC Preferences")

        global launcherMainFrame
        launcherMainFrame = LauncherMainFrame(None, wx.ID_ANY, 'MASSIVE/CVL Launcher')
        launcherMainFrame.Show(True)
        return True

app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
app.MainLoop()

