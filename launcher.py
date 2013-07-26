# MASSIVE/CVL Launcher - easy secure login for the MASSIVE Desktop and the CVL
#
# Copyright (c) 2012-2013, Monash e-Research Centre (Monash University, Australia)
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# In addition, redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# -  Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# -  Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# -  Neither the name of the Monash University nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. SEE THE
# GNU GENERAL PUBLIC LICENSE FOR MORE DETAILS.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Enquires: help@massive.org.au

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


# Make sure that the Launcher doesn't attempt to write to
# "CVL Launcher.exe.log", because it might not have
# permission to do so.
import sys
if sys.platform.startswith("win"):
    sys.stderr = sys.stdout

if sys.platform.startswith("win"):
    import _winreg
import subprocess
import wx
import time
import traceback
import threading
import os
import HTMLParser
import urllib2
import launcher_version_number
import xmlrpclib
import appdirs
import ConfigParser
import datetime
import shlex
import inspect
import requests
import ssh
from StringIO import StringIO
import logging
import LoginTasks
from utilityFunctions import *
import cvlsshutils.sshKeyDist
import launcher_progress_dialog
from menus.IdentityMenu import IdentityMenu
import tempfile

from logger.Logger import logger

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
global turboVncLatestVersion
turboVncLatestVersion = None

class LauncherMainFrame(wx.Frame):

    def __init__(self, parent, id, title):

#        global launcherMainFrame
#        launcherMainFrame = self

        self.logWindow = None
        self.progressDialog = None

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

        self.identity_menu = IdentityMenu()
        self.identity_menu.initialize(self, massiveLauncherConfig, massiveLauncherPreferencesFilePath)
        self.menu_bar.Append(self.identity_menu, "&Identity")

        self.help_menu = wx.Menu()
        helpContentsMenuItemID = wx.NewId()
        self.help_menu.Append(helpContentsMenuItemID, "&MASSIVE/CVL Launcher Help")
        self.Bind(wx.EVT_MENU, self.onHelpContents, id=helpContentsMenuItemID)
        self.help_menu.Append(wx.ID_ABOUT,   "&About MASSIVE/CVL Launcher")
        self.Bind(wx.EVT_MENU, self.onAbout, id=wx.ID_ABOUT)
        self.menu_bar.Append(self.help_menu, "&Help")

        self.SetTitle("MASSIVE / CVL Launcher")

        self.SetMenuBar(self.menu_bar)

        self.loginDialogPanel = wx.Panel(self, wx.ID_ANY)
        self.loginDialogPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=15, hgap=5)

        self.tabbedView = wx.Notebook(self.loginDialogPanel, wx.ID_ANY, style=(wx.NB_TOP))

        self.tabbedView.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,  self.onTabbedViewChanged)

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
        self.massiveLoginHostComboBox = wx.ComboBox(self.massiveLoginFieldsPanel, wx.ID_ANY, value=defaultMassiveHost, choices=massiveLoginHosts, size=(widgetWidth2, -1), style=wx.CB_READONLY)
        self.massiveLoginHostComboBox.Bind(wx.EVT_TEXT, self.onMassiveLoginHostNameChanged)
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
        self.massiveLoginHost = self.massiveLoginHost.strip()
        if self.massiveLoginHost!="":
            if self.massiveLoginHost in massiveLoginHosts:
                self.massiveLoginHostComboBox.SetSelection(massiveLoginHosts.index(self.massiveLoginHost))
            else:
                # Hostname was not found in combo-box.
                self.massiveLoginHostComboBox.SetSelection(-1)
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
        self.massiveProjects = [
            self.defaultProjectPlaceholder,
            'ASync001',
            'ASync002',
            'ASync003',
            'ASync004',
            'ASync005',
            'ASync006',
            'ASync008',
            'ASync009',
            'ASync010',
            'ASync011',
            'ASync012',
            'ASync013',
            'ASync_IMBL',
            'CSIRO001',
            'CSIRO002',
            'CSIRO003',
            'CSIRO004',
            'CSIRO005',
            'CSIRO006',
            'CSIRO007',
            'Desc001',
            'Desc002',
            'Desc003',
            'Desc004',
            'Desc005',
            'Desc006',
            'Desc007',
            'Monash001',
            'Monash002',
            'Monash003',
            'Monash004',
            'Monash005',
            'Monash006',
            'Monash007',
            'Monash008',
            'Monash009',
            'Monash010',
            'Monash012',
            'Monash013',
            'Monash014',
            'Monash015',
            'Monash016',
            'Monash017',
            'Monash018',
            'Monash019',
            'Monash020',
            'Monash021',
            'Monash022',
            'Monash023',
            'Monash024',
            'Monash025',
            'Monash026',
            'Monash027',
            'Monash028',
            'Monash029',
            'Monash030',
            'Monash031',
            'Monash032',
            'Monash033',
            'Monash034',
            'Monash035',
            'Monash036',
            'Monash037',
            'Monash038',
            'Monash039',
            'Monash040',
            'Monash041',
            'Monash042',
            'Monash043',
            'Monash044',
            'Monash045',
            'NCId75',
            'NCIdb5',
            'NCIdc0',
            'NCIdd2',
            'NCIdv0',
            'NCIdw3',
            'NCIdy4',
            'NCIdy7',
            'NCIdz3',
            'NCIea0',
            'NCIg61',
            'NCIg75',
            'NCIh77',
            'NCIq97',
            'NCIr14',
            'NCIv43',
            'NCIw25',
            'NCIw27',
            'NCIw67',
            'NCIw81',
            'NCIw91',
            'NCIy40',
            'NCIy95',
            'NCIy96',
            'pDeak0023',
            'pDeak0026',
            'pLaTr0011',
            'pMelb0095',
            'pMelb0100',
            'pMelb0103',
            'pMelb0104',
            'pMelb0106',
            'pMelb0107',
            'pMOSP',
            'pRMIT0074',
            'pRMIT0078',
            'pRMIT0083',
            'pVPAC0008',
            'Training',]
        self.massiveProjectComboBox = wx.ComboBox(self.massiveLoginFieldsPanel, wx.ID_ANY, value='', choices=self.massiveProjects, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.massiveProjectComboBox.Bind(wx.EVT_TEXT, self.onMassiveProjectTextChanged)
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

        self.massiveProject = self.massiveProject.strip()
        if self.massiveProject!="":
            if self.massiveProject in self.massiveProjects:
                self.massiveProjectComboBox.SetSelection(self.massiveProjects.index(self.massiveProject))
            else:
                # Project was not found in combo-box.
                self.massiveProjectComboBox.SetSelection(-1)
            self.massiveProjectComboBox.SetValue(self.massiveProject)
        else:
            self.massiveProjectComboBox.SetValue(self.defaultProjectPlaceholder)

        self.massiveHoursLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Hours requested')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveHoursLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveHoursAndVisNodesPanel = wx.Panel(self.massiveLoginFieldsPanel, wx.ID_ANY)
        self.massiveHoursAndVisNodesPanelSizer = wx.FlexGridSizer(rows=2, cols=3, vgap=3, hgap=5)
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
        self.massiveHoursAndVisNodesPanelSizer.Add(self.massiveHoursField, flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

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

        if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)


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
        self.massiveVncDisplayResolution = self.massiveVncDisplayResolution.strip()
        if self.massiveVncDisplayResolution!="":
            if self.massiveVncDisplayResolution in massiveVncDisplayResolutions:
                self.massiveVncDisplayResolutionComboBox.SetSelection(massiveVncDisplayResolutions.index(self.massiveVncDisplayResolution))
            else:
                # Resolution was not found in combo-box.
                self.massiveVncDisplayResolutionComboBox.SetSelection(-1)
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
        self.massiveSshTunnelCipher = defaultCipher
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
        self.massiveSshTunnelCipher = self.massiveSshTunnelCipher.strip()
        if self.massiveSshTunnelCipher=="":
            self.massiveSshTunnelCipher = defaultCipher
        if self.massiveSshTunnelCipher!="":
            if self.massiveSshTunnelCipher in massiveSshTunnelCiphers:
                self.massiveSshTunnelCipherComboBox.SetSelection(massiveSshTunnelCiphers.index(self.massiveSshTunnelCipher))
            else:
                # Cipher was not found in combo-box.
                self.massiveSshTunnelCipherComboBox.SetSelection(-1)
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


        self.massiveUsernameTextField.SetFocus()

        self.massiveProjectComboBox.MoveAfterInTabOrder(self.massiveLoginHostComboBox)
        #self.massiveHoursField.MoveAfterInTabOrder(self.massiveProjectComboBox)
        self.massiveHoursAndVisNodesPanel.MoveAfterInTabOrder(self.massiveProjectComboBox)
        #self.massiveVncDisplayResolutionComboBox.MoveAfterInTabOrder(self.massiveHoursField)
        self.massiveVncDisplayResolutionComboBox.MoveAfterInTabOrder(self.massiveHoursAndVisNodesPanel)
        self.massiveSshTunnelCipherComboBox.MoveAfterInTabOrder(self.massiveVncDisplayResolutionComboBox)
        self.massiveUsernameTextField.MoveAfterInTabOrder(self.massiveSshTunnelCipherComboBox)

        self.massiveShowDebugWindowLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Show debug window')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveShowDebugWindowLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveDebugAndAutoExitPanel = wx.Panel(self.massiveLoginFieldsPanel, wx.ID_ANY)
        self.massiveDebugAndAutoExitPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=3, hgap=5)
        self.massiveDebugAndAutoExitPanel.SetSizer(self.massiveDebugAndAutoExitPanelSizer)

        self.massiveShowDebugWindowCheckBox = wx.CheckBox(self.massiveDebugAndAutoExitPanel, wx.ID_ANY, "")
        self.massiveShowDebugWindowCheckBox.SetValue(False)
        self.massiveShowDebugWindowCheckBox.Bind(wx.EVT_CHECKBOX, self.onMassiveDebugWindowCheckBoxStateChanged)
        self.massiveDebugAndAutoExitPanelSizer.Add(self.massiveShowDebugWindowCheckBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.massiveAutomaticallyExitLabel = wx.StaticText(self.massiveDebugAndAutoExitPanel, wx.ID_ANY, "          Automatically exit")
        self.massiveDebugAndAutoExitPanelSizer.Add(self.massiveAutomaticallyExitLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=5)

        self.massiveAutomaticallyExit = True
        if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_automatically_exit"):
                self.massiveAutomaticallyExit = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_automatically_exit")
                if self.massiveAutomaticallyExit.strip() == "":
                    self.massiveAutomaticallyExit = True
                else:
                    if self.massiveAutomaticallyExit==True or self.massiveAutomaticallyExit=='True':
                        self.massiveAutomaticallyExit = True
                    else:
                        self.massiveAutomaticallyExit = False
            else:
                massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_automatically_exit","False")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        self.massiveAutomaticallyExitCheckBox = wx.CheckBox(self.massiveDebugAndAutoExitPanel, wx.ID_ANY, "")
        self.massiveAutomaticallyExitCheckBox.SetValue(self.massiveAutomaticallyExit)
        self.massiveDebugAndAutoExitPanelSizer.Add(self.massiveAutomaticallyExitCheckBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=5)

        self.massiveDebugAndAutoExitPanel.Fit()
        self.massiveLoginFieldsPanelSizer.Add(self.massiveDebugAndAutoExitPanel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        
        self.massiveLoginFieldsPanel.SetSizerAndFit(self.massiveLoginFieldsPanelSizer)

        self.massiveLoginDialogPanelSizer.Add(self.massiveLoginFieldsPanel, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=15)

        self.massiveLoginDialogPanel.SetSizerAndFit(self.massiveLoginDialogPanelSizer)
        self.massiveLoginDialogPanel.Layout()

        self.tabbedView.AddPage(self.massiveLoginDialogPanel, "MASSIVE")

        # CVL tab

        # Overall CVL login panel:
        self.cvlLoginDialogPanel = wx.Panel(self.tabbedView, wx.ID_ANY)
        self.tabbedView.AddPage(self.cvlLoginDialogPanel, "CVL")

        self.cvlLoginDialogPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=5, hgap=5)

        # Simple login fields: host, username, password, advanced settings checkbox
        self.cvlSimpleLoginFieldsPanel = wx.Panel(self.cvlLoginDialogPanel, wx.ID_ANY)
        self.cvlSimpleLoginFieldsPanelSizer = wx.FlexGridSizer(rows=4, cols=2, vgap=3, hgap=5)
        self.cvlSimpleLoginFieldsPanel.SetSizer(self.cvlSimpleLoginFieldsPanelSizer)

        self.cvlAdvancedLoginFieldsPanel = wx.Panel(self.cvlLoginDialogPanel, wx.ID_ANY)
        self.cvlAdvancedLoginFieldsPanelSizer = wx.FlexGridSizer(rows=4, cols=2, vgap=3, hgap=5)
        self.cvlAdvancedLoginFieldsPanel.SetSizer(self.cvlAdvancedLoginFieldsPanelSizer)

        self.cvlLoginHostLabel = wx.StaticText(self.cvlSimpleLoginFieldsPanel, wx.ID_ANY, 'Host')
        self.cvlSimpleLoginFieldsPanelSizer.Add(self.cvlLoginHostLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlLoginHost = ""
        cvlLoginHosts = ["login.cvl.massive.org.au","Huygens on the CVL"]
        defaultCvlHost = "login.cvl.massive.org.au"
        self.cvlLoginHostComboBox = wx.ComboBox(self.cvlSimpleLoginFieldsPanel, wx.ID_ANY, value=defaultCvlHost, choices=cvlLoginHosts, size=(widgetWidth2, -1), style=wx.CB_READONLY)
        self.cvlSimpleLoginFieldsPanelSizer.Add(self.cvlLoginHostComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
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
        self.cvlLoginHost = self.cvlLoginHost.strip()
        if self.cvlLoginHost!="":
            if self.cvlLoginHost in cvlLoginHosts:
                self.cvlLoginHostComboBox.SetSelection(cvlLoginHosts.index(self.cvlLoginHost))
            else:
                # Hostname was not found in combo-box.
                self.cvlLoginHostComboBox.SetSelection(-1)
            self.cvlLoginHostComboBox.SetValue(self.cvlLoginHost)



        # FIXME: Check how the Launcher dialog's 
        # 1. persistent mode check box (MASSIVE tab),
        # 2. automatic display number check box (CVL tab), and
        # 3. VNC display number spin control (CVL tab)
        # relate to the new LoginTasks.py's showReconnectDialog(event) method.
        # If these widgets are being ignored by LoginTasks.py, then perhaps they should be removed?
        # But if they are removed, will Paul be happy, given that he has made some requests about
        # the Launcher remembering the last-used state of persistent mode on m1 and on m2?



        self.cvlVncDisplayResolutionLabel = wx.StaticText(self.cvlAdvancedLoginFieldsPanel, wx.ID_ANY, 'Resolution')
        self.cvlAdvancedLoginFieldsPanelSizer.Add(self.cvlVncDisplayResolutionLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        displaySize = wx.DisplaySize()
        desiredWidth = displaySize[0] * 0.99
        desiredHeight = displaySize[1] * 0.85
        defaultResolution = str(int(desiredWidth)) + "x" + str(int(desiredHeight))
        self.cvlVncDisplayResolution = defaultResolution
        cvlVncDisplayResolutions = [
            defaultResolution, "1024x768", "1152x864", "1280x800", "1280x1024", "1360x768", "1366x768", "1440x900", "1600x900", "1680x1050", "1920x1080", "1920x1200", "7680x3200",
            ]
        self.cvlVncDisplayResolutionComboBox = wx.ComboBox(self.cvlAdvancedLoginFieldsPanel, wx.ID_ANY, value='', choices=cvlVncDisplayResolutions, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.cvlAdvancedLoginFieldsPanelSizer.Add(self.cvlVncDisplayResolutionComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
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
        self.cvlVncDisplayResolution = self.cvlVncDisplayResolution.strip()
        if self.cvlVncDisplayResolution!="":
            if self.cvlVncDisplayResolution in cvlVncDisplayResolutions:
                self.cvlVncDisplayResolutionComboBox.SetSelection(cvlVncDisplayResolutions.index(self.cvlVncDisplayResolution))
            else:
                # Resolution was not found in combo-box.
                self.cvlVncDisplayResolutionComboBox.SetSelection(-1)
            self.cvlVncDisplayResolutionComboBox.SetValue(self.cvlVncDisplayResolution)
        else:
            self.cvlVncDisplayResolutionComboBox.SetValue(defaultResolution)


        self.cvlSshTunnelCipherLabel = wx.StaticText(self.cvlAdvancedLoginFieldsPanel, wx.ID_ANY, 'SSH tunnel cipher')
        self.cvlAdvancedLoginFieldsPanelSizer.Add(self.cvlSshTunnelCipherLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        defaultCipher = ""
        self.cvlSshTunnelCipher = ""
        cvlSshTunnelCiphers = [""]
        if sys.platform.startswith("win"):
            defaultCipher = "arcfour"
            cvlSshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour"]
        else:
            defaultCipher = "arcfour128"
            cvlSshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour128"]
        self.cvlSshTunnelCipherComboBox = wx.ComboBox(self.cvlAdvancedLoginFieldsPanel, wx.ID_ANY, value='', choices=cvlSshTunnelCiphers, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)
        self.cvlAdvancedLoginFieldsPanelSizer.Add(self.cvlSshTunnelCipherComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
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
        self.cvlSshTunnelCipher = self.cvlSshTunnelCipher.strip()
        if self.cvlSshTunnelCipher=="":
            self.cvlSshTunnelCipher = defaultCipher
        if self.cvlSshTunnelCipher!="":
            if self.cvlSshTunnelCipher in cvlSshTunnelCiphers:
                self.cvlSshTunnelCipherComboBox.SetSelection(cvlSshTunnelCiphers.index(self.cvlSshTunnelCipher))
            else:
                # Cipher was not found in combo-box.
                self.cvlSshTunnelCipherComboBox.SetSelection(-1)
            self.cvlSshTunnelCipherComboBox.SetValue(self.cvlSshTunnelCipher)
        else:
            self.cvlSshTunnelCipherComboBox.SetValue(defaultCipher)

        self.cvlUsernameLabel = wx.StaticText(self.cvlSimpleLoginFieldsPanel, wx.ID_ANY, 'Username')
        self.cvlSimpleLoginFieldsPanelSizer.Add(self.cvlUsernameLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

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
        self.cvlUsernameTextField = wx.TextCtrl(self.cvlSimpleLoginFieldsPanel, wx.ID_ANY, self.cvlUsername, size=(widgetWidth1, -1))
        self.cvlSimpleLoginFieldsPanelSizer.Add(self.cvlUsernameTextField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=8)
        if self.cvlUsername.strip()!="":
            self.cvlUsernameTextField.SelectAll()

        self.cvlShowAdvancedLoginLabel = wx.StaticText(self.cvlSimpleLoginFieldsPanel, wx.ID_ANY, 'Show advanced options')
        self.cvlSimpleLoginFieldsPanelSizer.Add(self.cvlShowAdvancedLoginLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.cvlAdvancedLoginCheckBox = wx.CheckBox(self.cvlSimpleLoginFieldsPanel, wx.ID_ANY, "")
        self.cvlAdvancedLoginCheckBox.SetValue(False)
        self.cvlAdvancedLoginCheckBox.Bind(wx.EVT_CHECKBOX, self.onCvlAdvancedLoginCheckBox)
        self.cvlSimpleLoginFieldsPanelSizer.Add(self.cvlAdvancedLoginCheckBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlShowDebugWindowLabel = wx.StaticText(self.cvlAdvancedLoginFieldsPanel, wx.ID_ANY, 'Show debug window')
        self.cvlAdvancedLoginFieldsPanelSizer.Add(self.cvlShowDebugWindowLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlDebugAndAutoExitPanel = wx.Panel(self.cvlAdvancedLoginFieldsPanel, wx.ID_ANY)
        self.cvlDebugAndAutoExitPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=3, hgap=5)
        self.cvlDebugAndAutoExitPanel.SetSizer(self.cvlDebugAndAutoExitPanelSizer)

        self.cvlShowDebugWindowCheckBox = wx.CheckBox(self.cvlDebugAndAutoExitPanel, wx.ID_ANY, "")
        self.cvlShowDebugWindowCheckBox.SetValue(False)
        self.cvlShowDebugWindowCheckBox.Bind(wx.EVT_CHECKBOX, self.onCvlDebugWindowCheckBoxStateChanged)
        self.cvlDebugAndAutoExitPanelSizer.Add(self.cvlShowDebugWindowCheckBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlAutomaticallyExitLabel = wx.StaticText(self.cvlDebugAndAutoExitPanel, wx.ID_ANY, "          Automatically exit")
        self.cvlDebugAndAutoExitPanelSizer.Add(self.cvlAutomaticallyExitLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=5)

        self.cvlAutomaticallyExit = False
        if cvlLauncherConfig.has_section("CVL Launcher Preferences"):
            if cvlLauncherConfig.has_option("CVL Launcher Preferences", "cvl_automatically_exit"):
                self.cvlAutomaticallyExit = cvlLauncherConfig.get("CVL Launcher Preferences", "cvl_automatically_exit")
                if self.cvlAutomaticallyExit.strip() == "":
                    self.cvlAutomaticallyExit = False
                else:
                    if self.cvlAutomaticallyExit==True or self.cvlAutomaticallyExit=='True':
                        self.cvlAutomaticallyExit = True
                    else:
                        self.cvlAutomaticallyExit = False
            else:
                cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_automatically_exit","False")
                with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        else:
            cvlLauncherConfig.add_section("CVL Launcher Preferences")
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)

        self.cvlAutomaticallyExitCheckBox = wx.CheckBox(self.cvlDebugAndAutoExitPanel, wx.ID_ANY, "")
        self.cvlAutomaticallyExitCheckBox.SetValue(self.cvlAutomaticallyExit)
        self.cvlDebugAndAutoExitPanelSizer.Add(self.cvlAutomaticallyExitCheckBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, border=5)

        self.cvlDebugAndAutoExitPanel.Fit()
        self.cvlAdvancedLoginFieldsPanelSizer.Add(self.cvlDebugAndAutoExitPanel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        
        self.cvlSimpleLoginFieldsPanel.SetSizerAndFit(self.cvlSimpleLoginFieldsPanelSizer)

        self.cvlLoginDialogPanelSizer.Add(self.cvlSimpleLoginFieldsPanel, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=15)
        self.cvlLoginDialogPanelSizer.Add(self.cvlAdvancedLoginFieldsPanel, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=15)

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
        self.optionsButton = wx.Button(self.buttonsPanel, OPTIONS_BUTTON_ID, 'VNC Options')
        self.buttonsPanelSizer.Add(self.optionsButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.onOptions, id=OPTIONS_BUTTON_ID)

        CANCEL_BUTTON_ID = 2
        self.cancelButton = wx.Button(self.buttonsPanel, CANCEL_BUTTON_ID, 'Cancel')
        self.buttonsPanelSizer.Add(self.cancelButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.onCancel,  id=CANCEL_BUTTON_ID)

        LOGIN_BUTTON_ID = 3
        self.loginButton = wx.Button(self.buttonsPanel, LOGIN_BUTTON_ID, 'Login')
        self.buttonsPanelSizer.Add(self.loginButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.onLogin,   id=LOGIN_BUTTON_ID)

        self.buttonsPanel.SetSizerAndFit(self.buttonsPanelSizer)

        self.loginDialogPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=15)

        self.loginButton.SetDefault()

        self.loginDialogStatusBar = LauncherStatusBar(self)
        self.SetStatusBar(self.loginDialogStatusBar)

        self.loginDialogPanel.SetSizerAndFit(self.loginDialogPanelSizer)
        self.loginDialogPanel.Layout()

        self.Fit()
        self.Layout()

        self.Centre()

        import commit_def
        logger.debug('launcher commit hash: ' + commit_def.LATEST_COMMIT)
        logger.debug('cvlsshutils commit hash: ' + commit_def.LATEST_COMMIT_CVLSSHUTILS)

        # Check for the latest version of the launcher:
        try:
            myHtmlParser = MyHtmlParser('MassiveLauncherLatestVersionNumber')
            feed = urllib2.urlopen(LAUNCHER_URL, timeout=10)
            html = feed.read()
            myHtmlParser.feed(html)
            myHtmlParser.close()

            latestVersionNumber = myHtmlParser.latestVersionNumber
            htmlComments = myHtmlParser.htmlComments
            htmlCommentsSplit1 = htmlComments.split("<pre id=\"CHANGES\">")
            htmlCommentsSplit2 = htmlCommentsSplit1[1].split("</pre>")
            latestVersionChanges = htmlCommentsSplit2[0].strip()
            self.contacted_massive_website = True
        except:
            logger.debug(traceback.format_exc())
            self.contacted_massive_website = False
            dlg = wx.MessageDialog(self, "Warning: Could not contact the MASSIVE website to check version number.\n\n",
                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()

            latestVersionNumber = launcher_version_number.version_number
            latestVersionChanges = ''

        if latestVersionNumber != launcher_version_number.version_number:
            import new_version_alert_dialog
            newVersionAlertDialog = new_version_alert_dialog.NewVersionAlertDialog(launcherMainFrame, wx.ID_ANY, "MASSIVE/CVL Launcher", latestVersionNumber, latestVersionChanges, LAUNCHER_URL)
            newVersionAlertDialog.ShowModal()

            # Tried submit_log=True, but it didn't work.
            # Maybe the requests stuff hasn't been initialized yet.
            logger.debug("Failed version number check.")
            logger.dump_log(launcherMainFrame,submit_log=False)
            sys.exit(1)

    def onTabbedViewChanged(self, event):
        event.Skip()
        if hasattr(self, 'cvlAdvancedLoginCheckBox'):
            if self.cvlAdvancedLoginCheckBox.GetValue():
                launcherMainFrame.cvlAdvancedLoginFieldsPanel.Show()
            else:
                launcherMainFrame.cvlAdvancedLoginFieldsPanel.Hide()

    def onMassiveLoginHostNameChanged(self, event):
        event.Skip()
        selectedMassiveLoginHost = self.massiveLoginHostComboBox.GetValue()

    def onMassiveProjectTextChanged(self, event):
        massiveProjectTextFieldValue = launcherMainFrame.massiveProjectComboBox.GetValue().strip()
        if massiveProjectTextFieldValue=="" or massiveProjectTextFieldValue.startswith("[Use"):
            launcherMainFrame.massiveProjectComboBox.SetValue(launcherMainFrame.defaultProjectPlaceholder)
            launcherMainFrame.massiveProjectComboBox.SelectAll()
            launcherMainFrame.massiveProjectComboBox.SetFocus()
        if massiveProjectTextFieldValue in launcherMainFrame.massiveProjects:
            launcherMainFrame.massiveProjectComboBox.SetSelection(launcherMainFrame.massiveProjects.index(massiveProjectTextFieldValue))

    def onMassiveDebugWindowCheckBoxStateChanged(self, event):
        if launcherMainFrame.logWindow!=None:
            if launcherMainFrame.massiveTabSelected:
                launcherMainFrame.logWindow.Show(self.massiveShowDebugWindowCheckBox.GetValue())

    def onCvlDebugWindowCheckBoxStateChanged(self, event):
        if launcherMainFrame.logWindow!=None:
            if launcherMainFrame.cvlTabSelected:
                launcherMainFrame.logWindow.Show(self.cvlShowDebugWindowCheckBox.GetValue())

    def onCvlAdvancedLoginCheckBox(self, event):
        if self.cvlAdvancedLoginCheckBox.GetValue():
            launcherMainFrame.cvlAdvancedLoginFieldsPanel.Show()
        else:
            launcherMainFrame.cvlAdvancedLoginFieldsPanel.Hide()

    def onCloseMassiveDebugWindow(self, event):
        if launcherMainFrame.massiveTabSelected:
            self.massiveShowDebugWindowCheckBox.SetValue(False)
        if launcherMainFrame.logWindow!=None:
            launcherMainFrame.logWindow.Show(False)

    def onCloseCvlDebugWindow(self, event):
        if launcherMainFrame.cvlTabSelected:
            self.cvlShowDebugWindowCheckBox.SetValue(False)
        if launcherMainFrame.logWindow!=None:
            launcherMainFrame.logWindow.Show(False)

    def onHelpContents(self, event):
        from help.HelpController import helpController
        if helpController is not None and helpController.initializationSucceeded:
            helpController.DisplayContents()
        else:
            wx.MessageBox("Unable to open: " + helpController.launcherHelpUrl,
                          "Error", wx.OK|wx.ICON_EXCLAMATION)

    def onAbout(self, event):
        import commit_def
        dlg = wx.MessageDialog(self, "Version " + launcher_version_number.version_number + "\n"
                                   + 'launcher Commit: ' + commit_def.LATEST_COMMIT + '\n'
                                   + 'cvlsshutils Commit: ' + commit_def.LATEST_COMMIT_CVLSSHUTILS + '\n',
                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onExit(self, event):
        # Clean-up (including qdel if necessary) is now done in LoginTasks.py
        # No longer using temporary private key file, 
        # so there's no need to delete it as part of clean-up.

        try:
            logger.dump_log(launcherMainFrame)
        finally:
            os._exit(0)


    def onOptions(self, event):

        import optionsDialog

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

        launcherOptionsDialog = optionsDialog.LauncherOptionsDialog(launcherMainFrame, wx.ID_ANY, "MASSIVE/CVL Launcher Options", self.vncOptions)
        launcherOptionsDialog.ShowModal()

        if launcherOptionsDialog.okClicked:
            self.vncOptions = launcherOptionsDialog.getVncOptions()

            for key in self.vncOptions:
                turboVncConfig.set("TurboVNC Preferences", key, self.vncOptions[key])

            with open(turboVncPreferencesFilePath, 'wb') as turboVncPreferencesFileObject:
                turboVncConfig.write(turboVncPreferencesFileObject)

    def onCancel(self, event):
        # Clean-up (including qdel if necessary) is now done in LoginTasks.py
        # No longer using temporary private key file, 
        # so there's no need to delete it as part of clean-up.

        try:
            logger.dump_log(launcherMainFrame)
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
        self.massiveLoginHostComboBox.SetCursor(cursor)
        self.massiveVncDisplayResolutionComboBox.SetCursor(cursor)
        self.massiveSshTunnelCipherComboBox.SetCursor(cursor)
        self.massiveProjectComboBox.SetCursor(cursor)
        self.massiveHoursField.SetCursor(cursor)
        self.massiveUsernameTextField.SetCursor(cursor)

        self.cvlLoginHostComboBox.SetCursor(cursor)
        self.cvlUsernameTextField.SetCursor(cursor)
        self.cvlVncDisplayResolutionComboBox.SetCursor(cursor)
        self.cvlSshTunnelCipherComboBox.SetCursor(cursor)

        self.buttonsPanel.SetCursor(cursor)
        self.optionsButton.SetCursor(cursor)
        self.cancelButton.SetCursor(cursor)
        self.loginButton.SetCursor(cursor)

        if self.progressDialog!=None:
            self.progressDialog.SetCursor(cursor)

        super(LauncherMainFrame, self).SetCursor(cursor)

    def onLogin(self, event):
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
            self.massiveVncDisplayResolution = self.massiveVncDisplayResolutionComboBox.GetValue()
            self.massiveSshTunnelCipher = self.massiveSshTunnelCipherComboBox.GetValue()
            self.massiveAutomaticallyExit = self.massiveAutomaticallyExitCheckBox.GetValue()

            if self.massiveUsername.strip()=="":
                dlg = wx.MessageDialog(launcherMainFrame,
                        "Please enter your MASSIVE username.",
                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                self.massiveUsernameTextField.SetFocus()
                return
        else:
            self.cvlLoginHost = self.cvlLoginHostComboBox.GetValue()
            self.cvlUsername = self.cvlUsernameTextField.GetValue()
            self.cvlVncDisplayResolution = self.cvlVncDisplayResolutionComboBox.GetValue()
            self.cvlSshTunnelCipher = self.cvlSshTunnelCipherComboBox.GetValue()
            self.cvlAutomaticallyExit = self.cvlAutomaticallyExitCheckBox.GetValue()

            if self.cvlUsername.strip()=="":
                dlg = wx.MessageDialog(launcherMainFrame,
                        "Please enter your CVL username.",
                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                self.cvlUsernameTextField.SetFocus()
                return

        if launcherMainFrame.massiveTabSelected:
            self.massiveHoursRequested = str(self.massiveHoursField.GetValue())
            self.massiveVisNodesRequested = str(self.massiveVisNodesField.GetValue())
            self.massiveProject = self.massiveProjectComboBox.GetValue()
            if self.massiveProject == self.defaultProjectPlaceholder:
                try:
                    xmlrpcServer = xmlrpclib.Server("https://m2-web.massive.org.au/kgadmin/xmlrpc/")
                    # Get list of user's massiveProjects from Karaage:
                    # users_massiveProjects = xmlrpcServer.get_users_massiveProjects(self.massiveUsername, self.massivePassword)
                    # self.massiveProjects = users_massiveProjects[1]
                    # Get user's default massiveProject from Karaage:
                    self.massiveProject = xmlrpcServer.get_project(self.massiveUsername)
                except:
                    logger.debug(traceback.format_exc())
                    error_string = "Error contacting Massive to retrieve user's default project"
                    logger.error(error_string)
                    die_from_main_frame(launcherMainFrame,error_string)
                    return

                if self.massiveProject in self.massiveProjects:
                    self.massiveProjectComboBox.SetSelection(self.massiveProjects.index(self.massiveProject))
                else:
                    # Project was not found in combo-box.
                    self.massiveProjectComboBox.SetSelection(-1)
                self.massiveProjectComboBox.SetValue(self.massiveProject)


        if launcherMainFrame.massiveTabSelected:
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_login_host", self.massiveLoginHost)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_username", self.massiveUsername)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_vnc_display_resolution", self.massiveVncDisplayResolution)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_ssh_tunnel_cipher", self.massiveSshTunnelCipher)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_automatically_exit", self.massiveAutomaticallyExit)
        else:
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_login_host", self.cvlLoginHost)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_username", self.cvlUsername)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_vnc_display_resolution", self.cvlVncDisplayResolution)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_ssh_tunnel_cipher", self.cvlSshTunnelCipher)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_automatically_exit", self.cvlAutomaticallyExit)

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
            self.logWindow = wx.Frame(self, title="MASSIVE Login", name="MASSIVE Login",pos=(200,150),size=(700,450))
            self.logWindow.Bind(wx.EVT_CLOSE, self.onCloseMassiveDebugWindow)
        else:
            self.logWindow = wx.Frame(self, title="CVL Login", name="CVL Login",pos=(200,150),size=(700,450))
            self.logWindow.Bind(wx.EVT_CLOSE, self.onCloseCvlDebugWindow)

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.logWindow.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.logWindow.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.logTextCtrl = wx.TextCtrl(self.logWindow, style=wx.TE_MULTILINE|wx.TE_READONLY)
        logWindowSizer = wx.GridSizer(rows=1, cols=1, vgap=5, hgap=5)
        logWindowSizer.Add(self.logTextCtrl, 0, wx.EXPAND)
        self.logWindow.SetSizer(logWindowSizer)
        if sys.platform.startswith("darwin"):
            font = wx.Font(13, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        else:
            font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        self.logTextCtrl.SetFont(font)

        logger.sendLogMessagesToDebugWindowTextControl(self.logTextCtrl)

        if launcherMainFrame.massiveTabSelected:
            self.logWindow.Show(self.massiveShowDebugWindowCheckBox.GetValue())
        else:
            self.logWindow.Show(self.cvlShowDebugWindowCheckBox.GetValue())


        if launcherMainFrame.massiveTabSelected:
            host       = self.massiveLoginHost
            resolution = self.massiveVncDisplayResolution
            cipher     = self.massiveSshTunnelCipher
            username   = self.massiveUsername
            autoExit   = self.massiveAutomaticallyExit
            hours      = self.massiveHoursRequested
            nodes      = self.massiveVisNodesRequested
        else:
            host       = self.cvlLoginHost
            resolution = self.cvlVncDisplayResolution
            cipher     = self.cvlSshTunnelCipher
            username   = self.cvlUsername
            autoExit   = self.cvlAutomaticallyExit
            hours      = 298261 # maximum number of hours its possible to request without overflowing a signed int32 when converted to seconds.
            nodes      = 1

        host       = host.lstrip().rstrip()
        resolution = resolution.lstrip().rstrip()
        cipher     = cipher.lstrip().rstrip()
        username   = username.lstrip().rstrip()

        userCanAbort=True
        maximumProgressBarValue = 10

        try:
            os.mkdir(os.path.join(os.path.expanduser('~'), '.ssh'))
        except:
            logger.debug(traceback.format_exc())
            pass

        self.sshpaths = cvlsshutils.sshKeyDist.sshpaths('MassiveLauncherKey',massiveLauncherConfig,massiveLauncherPreferencesFilePath)
        # project hours and nodes will be ignored for the CVL login, but they will be used for Massive.
        jobParams={}
        jobParams['username']=username
        jobParams['loginHost']=host
        jobParams['configName']=host
        jobParams['resolution']=resolution
        jobParams['cipher']=cipher
        jobParams['project']=self.massiveProject
        jobParams['hours']=hours
        jobParams['nodes']=nodes
        jobParams['wallseconds']=int(hours)*60*60
        configName=host
        siteConfigDict = buildSiteConfigDict(configName) #eventually this will be loaded from json downloaded from a website
        siteConfigObj = siteConfig(siteConfigDict)
        self.loginProcess=LoginTasks.LoginProcess(launcherMainFrame,self,jobParams,self.sshpaths,siteConfig=siteConfigObj,autoExit=autoExit)
        if sys.platform.startswith("win"):
            cvlsshutils.sshKeyDist.start_pageant()
            if 'HOME' not in os.environ:
                os.environ['HOME'] = os.path.expanduser('~')
        self.loginProcess.doLogin()


        if self.massiveTabSelected:
            def initializeProgressDialog():
                CancelCallback=self.loginProcess.cancel
                self.progressDialog = launcher_progress_dialog.LauncherProgressDialog(self, wx.ID_ANY, "Connecting to MASSIVE...", "", maximumProgressBarValue, userCanAbort,CancelCallback)
        else:
            def initializeProgressDialog():
                CancelCallback=self.loginProcess.cancel
                self.progressDialog = launcher_progress_dialog.LauncherProgressDialog(self, wx.ID_ANY, "Connecting to CVL...", "", maximumProgressBarValue, userCanAbort,CancelCallback)

        wx.CallAfter(initializeProgressDialog)



class siteConfig():
    def __init__(self,siteConfigDict):
        self.__dict__.update(siteConfigDict)

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

        if sys.platform.startswith("win"):
            os.environ['CYGWIN'] = "nodosfilewarning"
        global launcherMainFrame
        launcherMainFrame = LauncherMainFrame(None, wx.ID_ANY, 'MASSIVE/CVL Launcher')
        launcherMainFrame.Show(True)

        def usingPrivateKeyForTheFirstTime():
            dlg = wx.MessageDialog(launcherMainFrame,
                    "It looks like this is the first time you've used " +
                    "this version of the Launcher, which requires you to " +
                    "use a private key, instead of a password.\n\n" +
                    "Would you like to view the Launcher's help on this topic?",
                    "MASSIVE/CVL Launcher", wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal()==wx.ID_YES:
                from help.HelpController import helpController
                if helpController is not None and helpController.initializationSucceeded:
                    helpController.Display("New Authentication Method")
                else:
                    wx.MessageBox("Unable to open: " + helpController.launcherHelpUrl,
                                  "Error", wx.OK|wx.ICON_EXCLAMATION)
            else:
                logger.debug('exception: ' + str(traceback.format_exc()))
                dlg = wx.MessageDialog(launcherMainFrame,
                    "You can access the help later from the Help menu or from the Identity menu.",
                    "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()

        if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_launcher_private_key_path"):
                logger.debug("Found massive_launcher_private_key_path in local settings.")
            else:
                usingPrivateKeyForTheFirstTime()
        else:
            usingPrivateKeyForTheFirstTime()

        return True

if __name__ == '__main__':
    app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
    app.MainLoop()
