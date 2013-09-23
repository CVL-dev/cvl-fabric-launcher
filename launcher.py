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
# Enquiries: help@massive.org.au

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
import cvlsshutils
import launcher_progress_dialog
from menus.IdentityMenu import IdentityMenu
import tempfile
from cvlsshutils.KeyModel import KeyModel

from logger.Logger import logger

from utilityFunctions import LAUNCHER_URL

launcherMainFrame = None
massiveLauncherConfig = None
cvlLauncherConfig = None
globalLauncherConfig = None
massiveLauncherPreferencesFilePath = None
cvlLauncherPreferencesFilePath = None
globalLauncherPreferencesFilePath = None

class LauncherMainFrame(wx.Frame):
    PERM_SSH_KEY=0
    TEMP_SSH_KEY=1

    def __init__(self, parent, id, title):

        sys.modules[__name__].launcherMainFrame = self

        launcherMainFrame = sys.modules[__name__].launcherMainFrame

        massiveLauncherConfig = sys.modules[__name__].massiveLauncherConfig
        massiveLauncherPreferencesFilePath = sys.modules[__name__].massiveLauncherPreferencesFilePath

        cvlLauncherConfig = sys.modules[__name__].cvlLauncherConfig
        cvlLauncherPreferencesFilePath = sys.modules[__name__].cvlLauncherPreferencesFilePath

        globalLauncherConfig = sys.modules[__name__].globalLauncherConfig
        globalLauncherPreferencesFilePath = sys.modules[__name__].globalLauncherPreferencesFilePath

        self.logWindow = None
        self.progressDialog = None

        if sys.platform.startswith("darwin"):
            wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        else:
            wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        self.globalOptions = {}

        if globalLauncherConfig.has_section("Global Preferences"):
            savedGlobalLauncherOptions =  globalLauncherConfig.items("Global Preferences")
            for option in savedGlobalLauncherOptions:
                key = option[0]
                value = option[1]
                if value=='True':
                    value = True
                if value=='False':
                    value = False
                self.globalOptions[key] = value
        import optionsDialog
        self.globalOptionsDialog = optionsDialog.GlobalOptionsDialog(launcherMainFrame, wx.ID_ANY, "Preferences", self.globalOptions, 0)

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.menu_bar  = wx.MenuBar()

        self.Bind(wx.EVT_CLOSE, self.onExit, id=self.GetId())

        # Do this for all platforms, even Mac OS X.
        # Even though we don't have a File menu with
        # an Exit menu item on Mac OS X, the wx.ID_EXIT
        # ID automatically gets mapped to the Quit menu
        # item (command q) in the "MASSIVE Launcher" menu.
        self.Bind(wx.EVT_MENU, self.onExit, id=wx.ID_EXIT)

        if sys.platform.startswith("win") or sys.platform.startswith("linux"):
            self.file_menu = wx.Menu()
            self.file_menu.Append(wx.ID_EXIT, "E&xit", "Close window and exit program.")
            self.menu_bar.Append(self.file_menu, "&File")

        #if sys.platform.startswith("darwin"):
            ## Only do this for Mac OS X, because other platforms have
            ## a right-click pop-up menu for wx.TextCtrl with Copy,
            ## Select All etc. Plus, the menu doesn't look that good on
            ## the MASSIVE Launcher main dialog, and doesn't work for
            ## non Mac platforms, because FindFocus() will always
            ## find the window/dialog which contains the menu.
            #self.edit_menu = wx.Menu()
            #self.edit_menu.Append(wx.ID_CUT, "Cut", "Cut the selected text")
            #self.Bind(wx.EVT_MENU, self.onCut, id=wx.ID_CUT)
            #self.edit_menu.Append(wx.ID_COPY, "Copy", "Copy the selected text")
            #self.Bind(wx.EVT_MENU, self.onCopy, id=wx.ID_COPY)
            #self.edit_menu.Append(wx.ID_PASTE, "Paste", "Paste text from the clipboard")
            #self.Bind(wx.EVT_MENU, self.onPaste, id=wx.ID_PASTE)
            #self.edit_menu.Append(wx.ID_SELECTALL, "Select All")
            #self.Bind(wx.EVT_MENU, self.onSelectAll, id=wx.ID_SELECTALL)
            #self.menu_bar.Append(self.edit_menu, "&Edit")
        self.edit_menu = wx.Menu()
        self.edit_menu.Append(wx.ID_CUT, "Cu&t", "Cut the selected text")
        self.Bind(wx.EVT_MENU, self.onCut, id=wx.ID_CUT)
        self.edit_menu.Append(wx.ID_COPY, "&Copy", "Copy the selected text")
        self.Bind(wx.EVT_MENU, self.onCopy, id=wx.ID_COPY)
        self.edit_menu.Append(wx.ID_PASTE, "&Paste", "Paste text from the clipboard")
        self.Bind(wx.EVT_MENU, self.onPaste, id=wx.ID_PASTE)
        self.edit_menu.Append(wx.ID_SELECTALL, "Select &All")
        self.Bind(wx.EVT_MENU, self.onSelectAll, id=wx.ID_SELECTALL)
        self.edit_menu.AppendSeparator()
        if sys.platform.startswith("win") or sys.platform.startswith("linux"):
            self.edit_menu.Append(wx.ID_PREFERENCES, "P&references\tCtrl-P")
        else:
            self.edit_menu.Append(wx.ID_PREFERENCES, "&Preferences")
        self.Bind(wx.EVT_MENU, self.onOptions, id=wx.ID_PREFERENCES)
        self.menu_bar.Append(self.edit_menu, "&Edit")

        self.identity_menu = IdentityMenu()
        self.identity_menu.initialize(self, globalLauncherConfig, globalLauncherPreferencesFilePath)
        self.menu_bar.Append(self.identity_menu, "&Identity")

        self.help_menu = wx.Menu()
        helpContentsMenuItemID = wx.NewId()
        self.help_menu.Append(helpContentsMenuItemID, "&MASSIVE/CVL Launcher Help")
        self.Bind(wx.EVT_MENU, self.onHelpContents, id=helpContentsMenuItemID)
        self.help_menu.AppendSeparator()
        emailHelpAtMassiveMenuItemID = wx.NewId()
        self.help_menu.Append(emailHelpAtMassiveMenuItemID, "Email &help@massive.org.au")
        self.Bind(wx.EVT_MENU, self.onEmailHelpAtMassive, id=emailHelpAtMassiveMenuItemID)
        emailCvlHelpAtMonashMenuItemID = wx.NewId()
        self.help_menu.Append(emailCvlHelpAtMonashMenuItemID, "Email &cvl-help@monash.edu")
        self.Bind(wx.EVT_MENU, self.onEmailCvlHelpAtMonash, id=emailCvlHelpAtMonashMenuItemID)
        submitDebugLogMenuItemID = wx.NewId()
        self.help_menu.Append(submitDebugLogMenuItemID, "&Submit debug log")
        self.Bind(wx.EVT_MENU, self.onSubmitDebugLog, id=submitDebugLogMenuItemID)
        # On Mac, the About menu item will automatically be moved from 
        # the Help menu to the "MASSIVE Launcher" menu, so we don't
        # need a separator.
        if not sys.platform.startswith("darwin"):
            self.help_menu.AppendSeparator()
        self.help_menu.Append(wx.ID_ABOUT,   "&About MASSIVE/CVL Launcher")
        self.Bind(wx.EVT_MENU, self.onAbout, id=wx.ID_ABOUT)
        self.menu_bar.Append(self.help_menu, "&Help")

        self.SetTitle("MASSIVE / CVL Launcher")

        self.SetMenuBar(self.menu_bar)

        self.loginDialogPanel = wx.Panel(self, wx.ID_ANY)
        self.loginDialogPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=15, hgap=5)

        self.tabbedView = wx.Notebook(self.loginDialogPanel, wx.ID_ANY, style=(wx.NB_TOP))

        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,  self.onTabbedViewChanged, id=self.tabbedView.GetId())

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
        self.massiveHoursField.Bind(wx.EVT_TEXT, self.onTextEnteredInIntegerField)

        # Spin controls are tricky to configure event-handling for,
        # because they contain both a TextCtrl object and a
        # spinner button, but they don't provide a direct interface
        # for accessing their TextCtrl object.  So we will
        # determine the TextCtrl object of each SpinCtrl the
        # first time it is focused, and then bind wx.EVT_KILL_FOCUS
        # to it, so we can ensure that the field has been
        # filled in.
        self.Bind(wx.EVT_CHILD_FOCUS, self.onChildFocus)

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
        self.massiveVisNodesField.Bind(wx.EVT_TEXT, self.onTextEnteredInIntegerField)
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
        self.massiveShowDebugWindowCheckBox.Bind(wx.EVT_CHECKBOX, self.onDebugWindowCheckBoxStateChanged)
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

        # Simple login fields: connection profile, username, advanced settings checkbox
        self.cvlSimpleLoginFieldsPanel = wx.Panel(self.cvlLoginDialogPanel, wx.ID_ANY)
        self.cvlSimpleLoginFieldsPanelSizer = wx.FlexGridSizer(rows=5, cols=2, vgap=3, hgap=5)
        self.cvlSimpleLoginFieldsPanel.SetSizer(self.cvlSimpleLoginFieldsPanelSizer)

        self.cvlAdvancedLoginFieldsPanel = wx.Panel(self.cvlLoginDialogPanel, wx.ID_ANY)
        self.cvlAdvancedLoginFieldsPanelSizer = wx.FlexGridSizer(rows=4, cols=2, vgap=3, hgap=5)
        self.cvlAdvancedLoginFieldsPanel.SetSizer(self.cvlAdvancedLoginFieldsPanelSizer)

        self.cvlConnectionProfileLabel = wx.StaticText(self.cvlSimpleLoginFieldsPanel, wx.ID_ANY, 'Connection')
        self.cvlSimpleLoginFieldsPanelSizer.Add(self.cvlConnectionProfileLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlConnectionProfile = ""
        cvlConnectionProfiles = ["login.cvl.massive.org.au","Huygens on the CVL","Other..."]
        defaultCvlConnectionProfile = "login.cvl.massive.org.au"
        self.cvlConnectionProfileComboBox = wx.ComboBox(self.cvlSimpleLoginFieldsPanel, wx.ID_ANY, value=defaultCvlConnectionProfile, choices=cvlConnectionProfiles, size=(widgetWidth2, -1), style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.onCvlConnectionProfileChanged, self.cvlConnectionProfileComboBox) 

        self.cvlSimpleLoginFieldsPanelSizer.Add(self.cvlConnectionProfileComboBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        if cvlLauncherConfig.has_section("CVL Launcher Preferences"):
            if cvlLauncherConfig.has_option("CVL Launcher Preferences", "cvl_connection_profile"):
                self.cvlConnectionProfile = cvlLauncherConfig.get("CVL Launcher Preferences", "cvl_connection_profile")

                # If the user has a setting for cvl_connection_profile that is not in our approved list, just take
                # the first known CVL connection profile.
                if self.cvlConnectionProfile not in cvlConnectionProfiles:
                    self.cvlConnectionProfile = cvlConnectionProfiles[0]

                    cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_connection_profile", self.cvlConnectionProfile)
                    with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                        cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
            else:
                cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_connection_profile","")
                with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                    cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        else:
            cvlLauncherConfig.add_section("CVL Launcher Preferences")
            with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
                cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)
        self.cvlConnectionProfile = self.cvlConnectionProfile.strip()
        if self.cvlConnectionProfile!="":
            if self.cvlConnectionProfile in cvlConnectionProfiles:
                self.cvlConnectionProfileComboBox.SetSelection(cvlConnectionProfiles.index(self.cvlConnectionProfile))
            else:
                # Connection profile was not found in combo-box.
                self.cvlConnectionProfileComboBox.SetSelection(0)

        self.cvlLoginHostLabel = wx.StaticText(self.cvlSimpleLoginFieldsPanel, wx.ID_ANY, 'Host')
        self.cvlSimpleLoginFieldsPanelSizer.Add(self.cvlLoginHostLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.cvlLoginHost = ""
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
        self.cvlLoginHostTextFieldPanel = wx.Panel(self.cvlSimpleLoginFieldsPanel, wx.ID_ANY, size=wx.Size(widgetWidth1, -1))
        self.cvlLoginHostTextFieldPanelSizer = wx.FlexGridSizer(rows=1, cols=1)
        self.cvlLoginHostTextField = wx.TextCtrl(self.cvlLoginHostTextFieldPanel, wx.ID_ANY, self.cvlLoginHost, size=wx.Size(widgetWidth1, -1))
        self.cvlLoginHostTextFieldPanelSizer.Add(self.cvlLoginHostTextField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.cvlLoginHostTextFieldPanel.SetSizerAndFit(self.cvlLoginHostTextFieldPanelSizer)
        self.cvlSimpleLoginFieldsPanelSizer.Add(self.cvlLoginHostTextFieldPanel, flag=wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=3)
        if self.cvlConnectionProfileComboBox.GetValue()!="Other...":
            self.cvlSimpleLoginFieldsPanelSizer.Show(self.cvlLoginHostTextFieldPanel,False)

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
        self.cvlShowDebugWindowCheckBox.Bind(wx.EVT_CHECKBOX, self.onDebugWindowCheckBoxStateChanged)
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
        if self.cvlConnectionProfileComboBox.GetValue()!="Other...":
            self.cvlSimpleLoginFieldsPanelSizer.Show(self.cvlLoginHostLabel,False)
            self.cvlSimpleLoginFieldsPanelSizer.Layout()
        self.cvlAdvancedLoginFieldsPanel.SetSizerAndFit(self.cvlAdvancedLoginFieldsPanelSizer)

        self.cvlLoginDialogPanelSizer.Add(self.cvlSimpleLoginFieldsPanel, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=15)
        self.cvlLoginDialogPanelSizer.Add(self.cvlAdvancedLoginFieldsPanel, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=15)

        self.cvlLoginDialogPanel.SetSizerAndFit(self.cvlLoginDialogPanelSizer)
        self.cvlLoginDialogPanel.Layout()

        # End CVL tab

        self.loginDialogPanelSizer.Add(self.tabbedView, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=10)

        lastUsedTabIndexAsString = "0"
        if globalLauncherConfig.has_section("Global Preferences"):
            if globalLauncherConfig.has_option("Global Preferences", "last_used_tab_index"):
                lastUsedTabIndexAsString = globalLauncherConfig.get("Global Preferences", "last_used_tab_index")
                if lastUsedTabIndexAsString.strip() == "":
                    lastUsedTabIndexAsString = "0"
        lastUsedTabIndex = int(lastUsedTabIndexAsString)
        MASSIVE_TAB_INDEX = 0
        CVL_TAB_INDEX = 1
        self.tabbedView.ChangeSelection(lastUsedTabIndex)
        self.massiveTabSelected = (lastUsedTabIndex==MASSIVE_TAB_INDEX)
        self.cvlTabSelected = (lastUsedTabIndex==CVL_TAB_INDEX)

        # Buttons Panel

        self.buttonsPanel = wx.Panel(self.loginDialogPanel, wx.ID_ANY)

        self.buttonsPanelSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=5, hgap=10)
        self.buttonsPanel.SetSizer(self.buttonsPanelSizer)

        self.preferencesButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Preferences')
        self.buttonsPanelSizer.Add(self.preferencesButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.onOptions, id=self.preferencesButton.GetId())

        self.exitButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Exit')
        self.buttonsPanelSizer.Add(self.exitButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.onExit,  id=self.exitButton.GetId())

        self.loginButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Login')
        self.buttonsPanelSizer.Add(self.loginButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.onLogin,   id=self.loginButton.GetId())

        self.buttonsPanel.SetSizerAndFit(self.buttonsPanelSizer)

        self.preferencesButton.Show(False)

        self.loginDialogPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=15)

        self.loginButton.SetDefault()

        self.loginDialogStatusBar = LauncherStatusBar(self)
        self.SetStatusBar(self.loginDialogStatusBar)

        self.loginDialogPanel.SetSizerAndFit(self.loginDialogPanelSizer)
        self.loginDialogPanel.Layout()

        self.Fit()
        self.Layout()

        self.Centre()

        self.logWindow = wx.Frame(self, title="MASSIVE/CVL Launcher Debug Log", name="MASSIVE/CVL Launcher Debug Log",pos=(200,150),size=(700,450))
        self.logWindow.Bind(wx.EVT_CLOSE, self.onCloseDebugWindow)
        self.logWindowPanel = wx.Panel(self.logWindow)
        self.logTextCtrl = wx.TextCtrl(self.logWindowPanel, style=wx.TE_MULTILINE|wx.TE_READONLY)
        logWindowSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=0, hgap=0)
        logWindowSizer.AddGrowableRow(0)
        logWindowSizer.AddGrowableCol(0)
        logWindowSizer.Add(self.logTextCtrl, flag=wx.EXPAND)
        self.submitDebugLogButton = wx.Button(self.logWindowPanel, wx.ID_ANY, 'Submit debug log')
        self.Bind(wx.EVT_BUTTON, self.onSubmitDebugLog, id=self.submitDebugLogButton.GetId())
        logWindowSizer.Add(self.submitDebugLogButton, flag=wx.ALIGN_RIGHT|wx.TOP|wx.BOTTOM|wx.RIGHT, border=10)
        self.logWindowPanel.SetSizer(logWindowSizer)
        if sys.platform.startswith("darwin"):
            font = wx.Font(13, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        else:
            font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        self.logTextCtrl.SetFont(font)

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.logWindow.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.logWindow.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        logger.sendLogMessagesToDebugWindowTextControl(self.logTextCtrl)

        import getpass
        logger.debug('getpass.getuser(): ' + getpass.getuser())

        logger.debug('sys.platform: ' + sys.platform)

        import platform

        logger.debug('platform.architecture: '  + str(platform.architecture()))
        logger.debug('platform.machine: '       + str(platform.machine()))
        logger.debug('platform.node: '          + str(platform.node()))
        logger.debug('platform.platform: '      + str(platform.platform()))
        logger.debug('platform.processor: '     + str(platform.processor()))
        logger.debug('platform.release: '       + str(platform.release()))
        logger.debug('platform.system: '        + str(platform.system()))
        logger.debug('platform.version: '       + str(platform.version()))
        logger.debug('platform.uname: '         + str(platform.uname()))

        if sys.platform.startswith("win"):
            logger.debug('platform.win32_ver: ' + str(platform.win32_ver()))

        if sys.platform.startswith("darwin"):
            logger.debug('platform.mac_ver: ' + str(platform.mac_ver()))

        if sys.platform.startswith("linux"):
            logger.debug('platform.linux_distribution: ' + str(platform.linux_distribution()))
            logger.debug('platform.libc_ver: ' + str(platform.libc_ver()))

        logger.debug('launcher_version_number.version_number: ' + launcher_version_number.version_number)
        import commit_def
        logger.debug('launcher commit hash: ' + commit_def.LATEST_COMMIT)
        logger.debug('cvlsshutils commit hash: ' + commit_def.LATEST_COMMIT_CVLSSHUTILS)
        MASSIVE_TAB_INDEX = 0
        CVL_TAB_INDEX =1
        if self.tabbedView.GetSelection()==MASSIVE_TAB_INDEX:
            logger.debug("Using MASSIVE display strings.")
            self.displayStrings = sshKeyDistDisplayStringsMASSIVE()
        if self.tabbedView.GetSelection()==CVL_TAB_INDEX:
            logger.debug("Using CVL display strings.")
            self.displayStrings = sshKeyDistDisplayStringsCVL()

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
            logger.debug('Old launcher version !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
            logger.debug('launcher version: ' + str(launcher_version_number.version_number))

        self.startupinfo = None
        try:
            self.startupinfo = subprocess.STARTUPINFO()
            self.startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
            self.startupinfo.wShowWindow = subprocess.SW_HIDE
        except:
            # On non-Windows systems, the previous block will throw:
            # "AttributeError: 'module' object has no attribute 'STARTUPINFO'".
            if sys.platform.startswith("win"):
                logger.debug('exception: ' + str(traceback.format_exc()))

        self.creationflags = 0
        try:
            import win32process
            self.creationflags = win32process.CREATE_NO_WINDOW
        except:
            # On non-Windows systems, the previous block will throw an exception.
            if sys.platform.startswith("win"):
                logger.debug('exception: ' + str(traceback.format_exc()))

        # launcherMainFrame.keyModel must be initialized before the
        # user presses the Login button, because the user might
        # use the Identity Menu to delete their key etc. before
        # pressing the Login button.
        self.keyModel = KeyModel(startupinfo=self.startupinfo,creationflags=self.creationflags,temporaryKey=False)


    def onTabbedViewChanged(self, event):
        event.Skip()
        if hasattr(self, 'cvlAdvancedLoginCheckBox'):
            if self.cvlAdvancedLoginCheckBox.GetValue():
                launcherMainFrame.cvlAdvancedLoginFieldsPanel.Show()
            else:
                launcherMainFrame.cvlAdvancedLoginFieldsPanel.Hide()
        MASSIVE_TAB_INDEX = 0
        CVL_TAB_INDEX =1
        if self.tabbedView.GetSelection()==MASSIVE_TAB_INDEX:
            launcherMainFrame.massiveTabSelected = True
            launcherMainFrame.cvlTabSelected = False
            logger.debug( "Using MASSIVE display strings.")
            self.displayStrings = sshKeyDistDisplayStringsMASSIVE()
        if self.tabbedView.GetSelection()==CVL_TAB_INDEX:
            launcherMainFrame.cvlTabSelected = True
            launcherMainFrame.massiveTabSelected = False
            logger.debug("Using CVL display strings.")
            self.displayStrings = sshKeyDistDisplayStringsCVL()

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

    def onDebugWindowCheckBoxStateChanged(self, event):
        if launcherMainFrame.logWindow!=None:
            if launcherMainFrame.cvlTabSelected:
                self.massiveShowDebugWindowCheckBox.SetValue(self.cvlShowDebugWindowCheckBox.GetValue())
                launcherMainFrame.logWindow.Show(self.cvlShowDebugWindowCheckBox.GetValue())
            if launcherMainFrame.massiveTabSelected:
                self.cvlShowDebugWindowCheckBox.SetValue(self.massiveShowDebugWindowCheckBox.GetValue())
                launcherMainFrame.logWindow.Show(self.massiveShowDebugWindowCheckBox.GetValue())

    def onCvlAdvancedLoginCheckBox(self, event):
        if self.cvlAdvancedLoginCheckBox.GetValue():
            launcherMainFrame.cvlLoginDialogPanelSizer.Show(launcherMainFrame.cvlAdvancedLoginFieldsPanel)
            launcherMainFrame.cvlLoginDialogPanelSizer.Layout()
        else:
            launcherMainFrame.cvlLoginDialogPanelSizer.Show(launcherMainFrame.cvlAdvancedLoginFieldsPanel,False)
            launcherMainFrame.cvlLoginDialogPanelSizer.Layout()

    def onCloseDebugWindow(self, event):
        self.massiveShowDebugWindowCheckBox.SetValue(False)
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

    def onEmailHelpAtMassive(self, event):
        import webbrowser
        webbrowser.open("mailto:help@massive.org.au")

    def onEmailCvlHelpAtMonash(self, event):
        import webbrowser
        webbrowser.open("mailto:cvl-help@monash.edu")

    def onSubmitDebugLog(self, event):
        logger.dump_log(launcherMainFrame,submit_log=True,showFailedToOpenRemoteDesktopMessage=False)

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


    def onOptions(self, event, tabIndex=0):

        self.globalOptionsDialog.tabbedView.SetSelection(tabIndex)
        rv = self.globalOptionsDialog.ShowModal()

        if rv == wx.OK:
            self.globalOptions = self.globalOptionsDialog.getVncOptions()
            self.saveGlobalOptions()
    
    def saveGlobalOptions(self):

        for key in self.globalOptions:
            globalLauncherConfig.set("Global Preferences", key, self.globalOptions[key])

        with open(globalLauncherPreferencesFilePath, 'wb') as globalPreferencesFileObject:
            globalLauncherConfig.write(globalPreferencesFileObject)


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

        self.cvlLoginDialogPanel.SetCursor(cursor)
        self.cvlSimpleLoginFieldsPanel.SetCursor(cursor)
        self.cvlAdvancedLoginFieldsPanel.SetCursor(cursor)
        self.cvlConnectionProfileLabel.SetCursor(cursor)
        self.cvlConnectionProfileComboBox.SetCursor(cursor)
        self.cvlUsernameLabel.SetCursor(cursor)
        self.cvlUsernameTextField.SetCursor(cursor)
        self.cvlVncDisplayResolutionLabel.SetCursor(cursor)
        self.cvlVncDisplayResolutionComboBox.SetCursor(cursor)
        self.cvlSshTunnelCipherLabel.SetCursor(cursor)
        self.cvlSshTunnelCipherComboBox.SetCursor(cursor)

        self.buttonsPanel.SetCursor(cursor)
        self.preferencesButton.SetCursor(cursor)
        self.exitButton.SetCursor(cursor)
        self.loginButton.SetCursor(cursor)

        if self.progressDialog!=None:
            self.progressDialog.SetCursor(cursor)

        super(LauncherMainFrame, self).SetCursor(cursor)

    def queryAuthMode(self):
        import LauncherOptionsDialog
        var='auth_mode'
        auth_mode=self.globalOptionsDialog.FindWindowByName(var)
        choices=[]
        for i in range(auth_mode.GetCount()):
            choices.append(auth_mode.GetString(i))
        message = """
Would you like to use an SSH Key pair or your password to authenticate yourself?

If this computer is shared by a number of people then passwords are preferable.

If this computer is not shared, then an SSH Key pair will give you advanced features for managing your access.
"""
        dlg = LauncherOptionsDialog.LauncherOptionsDialog(launcherMainFrame,message.strip(),title="MASSIVE/CVL Launcher",ButtonLabels=choices,helpEmailAddress=self.displayStrings.helpEmailAddress)
        rv=dlg.ShowModal()
        if rv in range(auth_mode.GetCount()):
            authModeRadioBox = self.globalOptionsDialog.FindWindowByName('auth_mode')
            authModeRadioBox.SetSelection(int(rv))
            self.identity_menu.setRadio()
            return int(rv)
        else:
            return wx.ID_CANCEL

    def onLoginProcessComplete(self, jobParams):
        logger.debug("launcher.py: onLogin: Enabling login button.")
        self.loginButton.Enable()

    def onLogin(self, event):

        logger.debug("launcher.py: onLogin: Disabling login button.")
        self.loginButton.Disable()

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
            self.cvlConnectionProfile = self.cvlConnectionProfileComboBox.GetValue()
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
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_connection_profile", self.cvlConnectionProfile)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_username", self.cvlUsername)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_vnc_display_resolution", self.cvlVncDisplayResolution)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_ssh_tunnel_cipher", self.cvlSshTunnelCipher)
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_automatically_exit", self.cvlAutomaticallyExit)

        if launcherMainFrame.massiveTabSelected:
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_project", self.massiveProject)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_hours_requested", self.massiveHoursRequested)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_visnodes_requested", self.massiveVisNodesRequested)

        globalLauncherConfig.set("Global Preferences", "last_used_tab_index", str(launcherMainFrame.tabbedView.GetSelection()))

        with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
            massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
            cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)

        with open(globalLauncherPreferencesFilePath, 'wb') as globalLauncherPreferencesFileObject:
            globalLauncherConfig.write(globalLauncherPreferencesFileObject)

        if launcherMainFrame.massiveTabSelected:
            self.logWindow.Show(self.massiveShowDebugWindowCheckBox.GetValue())
        else:
            self.logWindow.Show(self.cvlShowDebugWindowCheckBox.GetValue())


        if launcherMainFrame.massiveTabSelected:
            configName = self.massiveLoginHost
            resolution = self.massiveVncDisplayResolution
            cipher     = self.massiveSshTunnelCipher
            username   = self.massiveUsername
            autoExit   = self.massiveAutomaticallyExit
            hours      = self.massiveHoursRequested
            nodes      = self.massiveVisNodesRequested
        else:
            configName = self.cvlConnectionProfile
            resolution = self.cvlVncDisplayResolution
            cipher     = self.cvlSshTunnelCipher
            username   = self.cvlUsername
            autoExit   = self.cvlAutomaticallyExit
            hours      = 298261 # maximum number of hours its possible to request without overflowing a signed int32 when converted to seconds.
            nodes      = 1

        if configName=="Other...":
            configName = self.cvlLoginHostTextField.GetValue()
        configName = configName.lstrip().rstrip()
        resolution = resolution.lstrip().rstrip()
        cipher     = cipher.lstrip().rstrip()
        username   = username.lstrip().rstrip()

        logger.debug("Username: " + username)
        logger.debug("Config: " + configName)

        userCanAbort=True
        maximumProgressBarValue = 10

        dotSshDir = os.path.join(os.path.expanduser('~'), '.ssh')
        if not os.path.exists(dotSshDir):
            os.makedirs(dotSshDir)

        # project hours and nodes will be ignored for the CVL login, but they will be used for Massive.
        jobParams={}
        jobParams['username']=username
        jobParams['loginHost']=configName
        jobParams['configName']=configName
        jobParams['resolution']=resolution
        jobParams['cipher']=cipher
        jobParams['project']=self.massiveProject
        jobParams['hours']=hours
        jobParams['nodes']=nodes
        jobParams['wallseconds']=int(hours)*60*60
        if not self.globalOptions.has_key('auth_mode'):
            mode=self.queryAuthMode()
            if mode==wx.ID_CANCEL:
                self.onLoginProcessComplete(None)
                return
            self.globalOptions['auth_mode']=mode
            self.globalOptionsDialog.FindWindowByName('auth_mode').SetSelection(mode)
            self.identity_menu.disableItems()
            self.saveGlobalOptions()
        siteConfigDict = buildSiteConfigCmdRegExDict(configName) #eventually this will be loaded from json downloaded from a website
        siteConfigObj = siteConfig(siteConfigDict)

        if launcherMainFrame.globalOptionsDialog.FindWindowByName('auth_mode').GetSelection()==LauncherMainFrame.TEMP_SSH_KEY:
            logger.debug("launcherMainFrame.onLogin: using a temporary Key pair")
            try:
                if 'SSH_AUTH_SOCK' in os.environ:
                    os.environ['PREVIOUS_SSH_AUTH_SOCK'] = os.environ['SSH_AUTH_SOCK']
                del os.environ['SSH_AUTH_SOCK']
                logger.debug("launcherMainFrame.onLogin: spawning an ssh-agent (not using the existing agent)")
            except:
                logger.debug("launcherMainFrame.onLogin: spawning an ssh-agent (no existing agent found)")
                pass
            keyModel = KeyModel(startupinfo=self.startupinfo,creationflags=self.creationflags,temporaryKey=True)
            removeKeyOnExit = True
        else:
            logger.debug("launcherMainFrame.onLogin: using a permanent Key pair")
            keyModel = KeyModel(startupinfo=self.startupinfo,creationflags=self.creationflags,temporaryKey=False)
            
            removeKeyOnExit = False
        self.loginProcess=LoginTasks.LoginProcess(launcherMainFrame,jobParams,keyModel,siteConfig=siteConfigObj,displayStrings=self.displayStrings,autoExit=autoExit,globalOptions=self.globalOptions,removeKeyOnExit=removeKeyOnExit,startupinfo=launcherMainFrame.startupinfo,creationflags=launcherMainFrame.creationflags,completeCallback=self.onLoginProcessComplete)
        self.loginProcess.doLogin()


        if self.massiveTabSelected:
            def initializeProgressDialog():
                CancelCallback=self.loginProcess.cancel
                self.progressDialog = launcher_progress_dialog.LauncherProgressDialog(self, wx.ID_ANY, "Connecting to MASSIVE...", "", maximumProgressBarValue, userCanAbort,CancelCallback)
        else:
            def initializeProgressDialog():
                CancelCallback=self.loginProcess.cancel
                self.progressDialog = launcher_progress_dialog.LauncherProgressDialog(self, wx.ID_ANY, "Connecting to CVL...", "", maximumProgressBarValue, userCanAbort,CancelCallback)

#        wx.CallAfter(initializeProgressDialog)

    def onTextEnteredInIntegerField(self, event):
        if event.GetString()!="":

            # The code below does some validation, so for example:
            # "2a"  will be replaced by "2".
            # "a2"  will be replaced by "2"
            # "1a2" will be replaced by "12" and 
            # "a"   will be replaced with "".

            # We allow the user to clear the integer field 
            # temporarily, so they can then type in new digit(s),
            # even though an empty value is not strictly an integer.

            # If the users clears the field and then tabs away from 
            # the field, it should revert to a numerical value, set in
            # onIntegerFieldLostFocus.

            if event.GetEventObject().GetParent()==self.massiveHoursField:
                if event.GetString().startswith(str(self.massiveHoursField.GetValue())):
                    event.GetEventObject().SetValue(str(self.massiveHoursField.GetValue()))
                elif event.GetString().endswith(str(self.massiveHoursField.GetValue())):
                    event.GetEventObject().SetValue(str(self.massiveHoursField.GetValue()))
                elif len(event.GetString()) > len(str(self.massiveHoursField.GetValue())):
                    event.GetEventObject().SetValue(str(self.massiveHoursField.GetValue()))
                else:
                    event.GetEventObject().SetValue("")
            if event.GetEventObject().GetParent()==self.massiveVisNodesField:
                if event.GetString().startswith(str(self.massiveVisNodesField.GetValue())):
                    event.GetEventObject().SetValue(str(self.massiveVisNodesField.GetValue()))
                elif event.GetString().endswith(str(self.massiveVisNodesField.GetValue())):
                    event.GetEventObject().SetValue(str(self.massiveVisNodesField.GetValue()))
                elif len(event.GetString()) > len(str(self.massiveHoursField.GetValue())):
                    event.GetEventObject().SetValue(str(self.massiveVisNodesField.GetValue()))
                else:
                    event.GetEventObject().SetValue("")
        event.Skip()

    def onIntegerFieldLostFocus(self, event):
        if event.GetEventObject().GetParent()==self.massiveHoursField or event.GetEventObject().GetParent()==self.massiveVisNodesField:
            if event.GetEventObject().GetValue().strip() == "":
                event.GetEventObject().SetValue("1")
        event.Skip()

    def onChildFocus(self, event):
        if event.GetEventObject().GetParent()==self.massiveHoursField or event.GetEventObject().GetParent()==self.massiveVisNodesField:
            while event.GetEventObject().Unbind(wx.EVT_KILL_FOCUS):
                pass
            event.GetEventObject().Bind(wx.EVT_KILL_FOCUS, self.onIntegerFieldLostFocus)
        event.Skip()

    def onCvlConnectionProfileChanged(self, event):
        if self.cvlConnectionProfileComboBox.GetValue()=="Other...":
            launcherMainFrame.cvlSimpleLoginFieldsPanelSizer.Show(launcherMainFrame.cvlLoginHostLabel)
            launcherMainFrame.cvlSimpleLoginFieldsPanelSizer.Show(launcherMainFrame.cvlLoginHostTextFieldPanel)
            launcherMainFrame.cvlSimpleLoginFieldsPanelSizer.Layout()
            launcherMainFrame.cvlLoginDialogPanelSizer.Layout()
            launcherMainFrame.cvlLoginHostTextField.SelectAll()
            launcherMainFrame.cvlLoginHostTextField.SetFocus()
        else:
            launcherMainFrame.cvlSimpleLoginFieldsPanelSizer.Show(launcherMainFrame.cvlLoginHostLabel,False)
            launcherMainFrame.cvlSimpleLoginFieldsPanelSizer.Show(launcherMainFrame.cvlLoginHostTextFieldPanel,False)
            launcherMainFrame.cvlSimpleLoginFieldsPanelSizer.Layout()
            launcherMainFrame.cvlLoginDialogPanelSizer.Layout()
            #launcherMainFrame.cvlLoginHostTextField.SetValue("")

class siteConfig():
    class cmdRegEx():
        def __init__(self,cmd=None,regex=None,requireMatch=True,loop=False,async=False,host='login'):

            self.cmd=cmd
            if (not isinstance(regex,list)):
                self.regex=[regex]
            else:
                self.regex=regex
            self.loop=loop
            self.async=async
            self.requireMatch=requireMatch
            if regex==None:
                self.requireMatch=False
            self.host=host
            if (self.async):
                self.host='local'

        def getCmd(self,jobParam={}):
            if ('exec' in self.host):
                sshCmd = '{sshBinary} -A -T -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o StrictHostKeyChecking=no -l {username} {execHost} '
            elif ('local' in self.host):
                sshCmd = ''
            else:
                sshCmd = '{sshBinary} -A -T -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o StrictHostKeyChecking=yes -l {username} {loginHost} '
            string=sshCmd.format(**jobParam)+self.cmd.format(**jobParam)
            return string
            
        
    def __init__(self,siteConfigDict):
        self.listAll=siteConfig.cmdRegEx()
        self.running=siteConfig.cmdRegEx()
        self.stop=siteConfig.cmdRegEx()
        self.stopForRestart=siteConfig.cmdRegEx()
        self.execHost=siteConfig.cmdRegEx()
        self.startServer=siteConfig.cmdRegEx()
        self.runSanityCheck=siteConfig.cmdRegEx()
        self.setDisplayResolution=siteConfig.cmdRegEx()
        self.getProjects=siteConfig.cmdRegEx()
        self.showStart=siteConfig.cmdRegEx()
        self.vncDisplay=siteConfig.cmdRegEx()
        self.otp=siteConfig.cmdRegEx()
        self.directConnect=siteConfig.cmdRegEx()
        self.messageRegeexs=siteConfig.cmdRegEx()
        self.dbusSessionBusAddress=siteConfig.cmdRegEx()
        self.webDavIntermediatePort=siteConfig.cmdRegEx()
        self.webDavRemotePort=siteConfig.cmdRegEx()
        self.openWebDavShareInRemoteFileBrowser=siteConfig.cmdRegEx()
        self.webDavWindowID=siteConfig.cmdRegEx()
        self.displayWebDavInfoDialogOnRemoteDesktop=siteConfig.cmdRegEx()
        self.webDavTunnel=siteConfig.cmdRegEx()
        self.webDavUnmount=siteConfig.cmdRegEx()
        self.webDavCloseWindow=siteConfig.cmdRegEx()
        self.__dict__.update(siteConfigDict)

def buildSiteConfigCmdRegExDict(configName):
    import re
    if sys.platform.startswith("win"):
        lt = "^<"
        gt = "^>"
        pipe = "^|"
        ampersand = "^&"
    else:
        lt = "<"
        gt = ">"
        pipe = "|"
        ampersand = "&"
    siteConfigDict={}
    siteConfigDict['messageRegexs']=[re.compile("^INFO:(?P<info>.*(?:\n|\r\n?))",re.MULTILINE),re.compile("^WARN:(?P<warn>.*(?:\n|\r\n?))",re.MULTILINE),re.compile("^ERROR:(?P<error>.*(?:\n|\r\n?))",re.MULTILINE)]
    if ("m1" in configName or "m2" in configName):
        siteConfigDict['loginHost']=configName
        siteConfigDict['listAll']=siteConfig.cmdRegEx('qstat -u {username}','^\s*(?P<jobid>(?P<jobidNumber>[0-9]+).\S+)\s+{username}\s+(?P<queue>\S+)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>[^C])\s+(?P<elapTime>\S+)\s*$',requireMatch=False)
        siteConfigDict['running']=siteConfig.cmdRegEx('qstat -u {username}','^\s*(?P<jobid>{jobid})\s+{username}\s+(?P<queue>\S+)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>R)\s+(?P<elapTime>\S+)\s*$')
        siteConfigDict['stop']=siteConfig.cmdRegEx('\'qdel -a {jobid}\'')
        siteConfigDict['stopForRestart']=siteConfig.cmdRegEx('qdel {jobid} ; sleep 5\'')
        siteConfigDict['execHost']=siteConfig.cmdRegEx('qpeek {jobidNumber}','\s*To access the desktop first create a secure tunnel to (?P<execHost>\S+)\s*$')
        siteConfigDict['startServer']=siteConfig.cmdRegEx("\'/usr/local/desktop/request_visnode.sh {project} {hours} {nodes} True False False\'","^(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s*$")
        siteConfigDict['runSanityCheck']=siteConfig.cmdRegEx("\'/usr/local/desktop/sanity_check.sh {launcher_version_number}\'")
        siteConfigDict['setDisplayResolution']=siteConfig.cmdRegEx("\'/usr/local/desktop/set_display_resolution.sh {resolution}\'")
        siteConfigDict['getProjects']=siteConfig.cmdRegEx('\"glsproject -A -q | grep \',{username},\|\s{username},\|,{username}\s\' \"','^(?P<group>\S+)\s+.*$')
        siteConfigDict['showStart']=siteConfig.cmdRegEx("showstart {jobid}","Estimated Rsv based start .*?on (?P<estimatedStart>.*)")
        siteConfigDict['vncDisplay']= siteConfig.cmdRegEx('"/usr/bin/ssh {execHost} \' module load turbovnc ; vncserver -list\'"','^(?P<vncDisplay>:[0-9]+)\s*(?P<vncPID>[0-9]+)\s*$')
        siteConfigDict['otp']= siteConfig.cmdRegEx('"/usr/bin/ssh {execHost} \' module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\'"','^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$')
        siteConfigDict['agent']=siteConfig.cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -l {username} {loginHost} \"/usr/bin/ssh -A {execHost} \\"echo agent_hello; bash \\"\"','agent_hello',async=True)
        siteConfigDict['tunnel']=siteConfig.cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -L {localPortNumber}:{execHost}:{remotePortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"','tunnel_hello',async=True)

        cmd='"echo DBUS_SESSION_BUS_ADDRESS=dummy_dbus_session_bus_address"'
        regex='^DBUS_SESSION_BUS_ADDRESS=(?P<dbusSessionBusAddress>.*)$'
        siteConfigDict['dbusSessionBusAddress']=siteConfig.cmdRegEx(cmd,regex)

        cmd='\"/usr/local/desktop/get_ephemeral_port.py\"'
        regex='^(?P<intermediateWebDavPortNumber>[0-9]+)$'
        siteConfigDict['webDavIntermediatePort']=siteConfig.cmdRegEx(cmd,regex)

        cmd='\"/usr/bin/ssh {execHost} /usr/local/desktop/get_ephemeral_port.py\"'
        regex='^(?P<remoteWebDavPortNumber>[0-9]+)$'
        siteConfigDict['webDavRemotePort']=siteConfig.cmdRegEx(cmd,regex)

        cmd='"/usr/bin/ssh {execHost} \'DISPLAY={vncDisplay} /usr/bin/konqueror webdav://{localUsername}:{vncPasswd}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\'"'
        siteConfigDict['openWebDavShareInRemoteFileBrowser']=siteConfig.cmdRegEx(cmd)

        # The Window ID is not needed for MASSIVE.  We use the server-side script: /usr/local/desktop/close_webdav_window.sh which figures out which window to close.
        cmd='"echo DummyWebDavWindowID=-1"'
        regex='^DummyWebDavWindowID=(?P<webDavWindowID>.*)$'
        siteConfigDict['webDavWindowID']=siteConfig.cmdRegEx(cmd,regex)

        cmd='"/usr/bin/ssh {execHost} \'echo -e \\"You can access your local home directory in Konqueror with the URL:%sbr%s\\nwebdav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}%sbr%s\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$(hostname){vncDisplay}-webdav.txt;\'"'
        siteConfigDict['displayWebDavInfoDialogOnRemoteDesktop'] = siteConfig.cmdRegEx(cmd)

        # Chris trying to avoid using the intermediate port:
        #cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {execHost}:{remoteWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"'

        cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {intermediateWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "ssh -R {remoteWebDavPortNumber}:localhost:{intermediateWebDavPortNumber} {execHost} \'echo tunnel_hello; bash\'"'
        regex='tunnel_hello'
        siteConfigDict['webDavTunnel']=siteConfig.cmdRegEx(cmd,regex,async=True)

        cmd = 'echo hello'
        regex = 'hello'
        siteConfigDict['webDavUnmount']=siteConfig.cmdRegEx(cmd,regex)

        cmd = '"/usr/bin/ssh {execHost} \'DISPLAY={vncDisplay} /usr/local/desktop/close_webdav_window.sh webdav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\'"'
        siteConfigDict['webDavCloseWindow']=siteConfig.cmdRegEx(cmd)

        cmd='echo hello;exit'
        regex='hello'

    elif ('cvl' in configName or 'CVL' in configName or 'Huygens' in configName):
        siteConfigDict['loginHost']='login.cvl.massive.org.au'
        siteConfigDict['directConnect']=True
        cmd='\"module load pbs ; qstat -f {jobidNumber} | grep exec_host | sed \'s/\ \ */\ /g\' | cut -f 4 -d \' \' | cut -f 1 -d \'/\' | xargs -iname hostn name | grep address | sed \'s/\ \ */\ /g\' | cut -f 3 -d \' \' | xargs -iip echo execHost ip; qstat -f {jobidNumber}\"'
        regex='^\s*execHost (?P<execHost>\S+)\s*$'
        siteConfigDict['execHost'] = siteConfig.cmdRegEx(cmd,regex)
        cmd='\"groups | sed \'s@ @\\n@g\'\"' # '\'groups | sed \'s\/\\\\ \/\\\\\\\\n\/g\'\''
        regex='^\s*(?P<group>\S+)\s*$'
        siteConfigDict['getProjects'] = siteConfig.cmdRegEx(cmd,regex)
        if ("Huygens" in configName):
            siteConfigDict['listAll']=siteConfig.cmdRegEx('\"module load pbs ; qstat -u {username} | tail -n +6\"','^\s*(?P<jobid>(?P<jobidNumber>[0-9]+).\S+)\s+{username}\s+(?P<queue>huygens)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>[^C])\s+(?P<elapTime>\S+)\s*$',requireMatch=False)
        else:
            siteConfigDict['listAll']=siteConfig.cmdRegEx('\"module load pbs ; qstat -u {username} | tail -n +6\"','^\s*(?P<jobid>(?P<jobidNumber>[0-9]+).\S+)\s+{username}\s+(?P<queue>batch)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>[^C])\s+(?P<elapTime>\S+)\s*$',requireMatch=False)
        cmd='\"module load pbs ; module load maui ; qstat | grep {username}\"'
        regex='^\s*(?P<jobid>{jobidNumber}\.\S+)\s+(?P<jobname>desktop_\S+)\s+{username}\s+(?P<elapTime>\S+)\s+(?P<state>R)\s+(?P<queue>\S+)\s*$'
        siteConfigDict['running']=siteConfig.cmdRegEx(cmd,regex)
        if ("Huygens" in configName):
            cmd="\"module load pbs ; module load maui ; echo \'module load pbs ; /usr/local/bin/vncsession --vnc turbovnc --geometry {resolution} ; sleep {wallseconds}\' |  qsub -q huygens -l nodes=1:ppn=1 -N desktop_{username} -o .vnc/ -e .vnc/\""
        else:
            cmd="\"module load pbs ; module load maui ; echo \'module load pbs ; /usr/local/bin/vncsession --vnc turbovnc --geometry {resolution} ; sleep {wallseconds}\' |  qsub -l nodes=1:ppn=1,walltime={wallseconds} -N desktop_{username} -o .vnc/ -e .vnc/\""
        regex="^(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s*$"
        siteConfigDict['startServer']=siteConfig.cmdRegEx(cmd,regex)
        siteConfigDict['stop']=siteConfig.cmdRegEx('\"module load pbs ; module load maui ; qdel -a {jobidNumber}\"')
        siteConfigDict['stopForRestart']=siteConfig.cmdRegEx('\"module load pbs ; module load maui ; qdel {jobid}\"')
        #siteConfigDict['vncDisplay']= siteConfig.cmdRegEx('" /usr/bin/ssh {execHost} \' cat /var/spool/torque/spool/{jobidNumber}.*\'"' ,'^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$')
        siteConfigDict['vncDisplay']= siteConfig.cmdRegEx('\"cat /var/spool/torque/spool/{jobidNumber}.*\"' ,'^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$',host='exec')
        cmd= '\"module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\"'
        regex='^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$'
        siteConfigDict['otp']=siteConfig.cmdRegEx(cmd,regex,host='exec')
        siteConfigDict['agent']=siteConfig.cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -l {username} {execHost} "echo agent_hello; bash "','agent_hello',async=True)
        siteConfigDict['tunnel']=siteConfig.cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -L {localPortNumber}:localhost:{remotePortNumber} -l {username} {execHost} "echo tunnel_hello; bash"','tunnel_hello',async=True)

        cmd='"/usr/bin/ssh {execHost} \'export DISPLAY={vncDisplay};timeout 15 /usr/local/bin/cat_dbus_session_file.sh\'"'
        regex='^DBUS_SESSION_BUS_ADDRESS=(?P<dbusSessionBusAddress>.*)$'
        siteConfigDict['dbusSessionBusAddress']=siteConfig.cmdRegEx(cmd,regex)

        cmd='\"/usr/local/bin/get_ephemeral_port.py\"'
        regex='^(?P<intermediateWebDavPortNumber>[0-9]+)$'
        siteConfigDict['webDavIntermediatePort']=siteConfig.cmdRegEx(cmd,regex,host='exec')

        cmd='\"/usr/local/bin/get_ephemeral_port.py\"'
        regex='^(?P<remoteWebDavPortNumber>[0-9]+)$'
        siteConfigDict['webDavRemotePort']=siteConfig.cmdRegEx(cmd,regex,host='exec')

        # Below, I initially tried to respect the user's Nautilus setting of always_use_location_entry and change it back after launching Nautilus,
        # but doing so changes this setting in already-running Nautilus windows, and I want the user to see Nautilus's location bar when showing 
        # them the WebDav share.  So now, I just brutally change the user's Nautilus location-bar setting to always_use_location_entry.
        # Note that we might end up mounting WebDAV in a completely different way (e.g. using wdfs), but for now I'm trying to make the user
        # experience similar on MASSIVE and the CVL.  On MASSIVE, users are not automatically added to the "fuse" group, but they can still 
        # access a WebDAV share within Konqueror.  The method below for the CVL/Nautilus does require fuse membership, but it ends up looking
        # similar to MASSIVE/Konqueror from the user's point of view.  

        #cmd="\"/usr/bin/ssh {execHost} \\\"export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};echo \\\\\\\"import pexpect;child = pexpect.spawn('gvfs-mount dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}');child.expect('Password: ');child.sendline('{vncPasswd}')\\\\\\\" %s python %s%s /usr/bin/gconftool-2 --type=Boolean --set /apps/nautilus/preferences/always_use_location_entry true %s%s DISPLAY={vncDisplay} /usr/bin/nautilus --no-desktop --sm-disable dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName} %s%s echo WebDavMountingDone\\\"\"" % (pipe,ampersand,ampersand,ampersand,ampersand,ampersand,ampersand)
        cmd="\"/usr/bin/ssh {execHost} \\\"export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};echo \\\\\\\"import pexpect;child = pexpect.spawn('gvfs-mount dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}');child.expect('Password: ');child.sendline('{vncPasswd}')\\\\\\\" %s python %s%s /usr/bin/gconftool-2 --type=Boolean --set /apps/nautilus/preferences/always_use_location_entry true %s%s DISPLAY={vncDisplay} /usr/bin/nautilus --no-desktop --sm-disable dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName} %s%s echo intentially crashing\\\"\"" % (pipe,ampersand,ampersand,ampersand,ampersand,ampersand,ampersand)
        regex='^.*(?P<webDavMountingDone>WebDavMountingDone).*$'
        siteConfigDict['openWebDavShareInRemoteFileBrowser']=siteConfig.cmdRegEx(cmd,regex,requireMatch=False)

        cmd='"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress}; DISPLAY={vncDisplay} xwininfo -root -tree\'"'
        regex= '^\s+(?P<webDavWindowID>\S+)\s+"{homeDirectoryWebDavShareName}.*Browser.*$'
        siteConfigDict['webDavWindowID']=siteConfig.cmdRegEx(cmd,regex)

        cmd = '"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$(hostname){vncDisplay}-webdav.txt\'"'
        siteConfigDict['displayWebDavInfoDialogOnRemoteDesktop']=siteConfig.cmdRegEx(cmd)

        cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {remoteWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {execHost} "echo tunnel_hello; bash"'
        regex='tunnel_hello'
        siteConfigDict['webDavTunnel']=siteConfig.cmdRegEx(cmd,regex,async=True)

        # 1. I'm using gvfs-mount --unmount-scheme dav for now, to unmount all GVFS WebDAV mounts,
        #    because using "gvfs-mount --unmount " on a specific mount point from a Launcher
        #    subprocess doesn't seem to work reliably, even though it works fine outside of the 
        #    Launcher.
        # 2. I'm using timeout with gvfs-mount, because sometimes the process never exits
        #    when unmounting, even though the unmounting operation is complete.
        #cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};DISPLAY={vncDisplay} timeout 3 gvfs-mount -u \".gvfs/WebDAV on localhost\"\'"'
        cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};export DISPLAY={vncDisplay};timeout 1 gvfs-mount --unmount-scheme dav\'"'
        siteConfigDict['webDavUnmount']=siteConfig.cmdRegEx(cmd)

        cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};export DISPLAY={vncDisplay}; wmctrl -F -i -c {webDavWindowID}\'"'
        siteConfigDict['webDavCloseWindow']=siteConfig.cmdRegEx(cmd)
    else:
        siteConfigDict['loginHost']=configName
        siteConfigDict['listAll']=siteConfig.cmdRegEx('\'module load turbovnc ; vncserver -list\'','^(?P<vncDisplay>:[0-9]+)\s+[0-9]+\s*$',requireMatch=False)
        siteConfigDict['startServer']=siteConfig.cmdRegEx('\"/usr/local/bin/vncsession --vnc turbovnc --geometry {resolution}\"','^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$')
        siteConfigDict['stop']=siteConfig.cmdRegEx('\'module load turbovnc ; vncserver -kill {vncDisplay}\'')
        siteConfigDict['otp']= siteConfig.cmdRegEx('\'module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\'','^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$')
        siteConfigDict['agent']=siteConfig.cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -l {username} {loginHost} "echo agent_hello; bash "','agent_hello',async=True)
        siteConfigDict['tunnel']=siteConfig.cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -L {localPortNumber}:localhost:{remotePortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"','tunnel_hello',async=True)

        cmd='"/usr/bin/ssh {execHost} \'export DISPLAY={vncDisplay};timeout 15 /usr/local/bin/cat_dbus_session_file.sh\'"'
        regex='^DBUS_SESSION_BUS_ADDRESS=(?P<dbusSessionBusAddress>.*)$'
        siteConfigDict['dbusSessionBusAddress']=siteConfig.cmdRegEx(cmd,regex)

        cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {intermediateWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "ssh -R {remoteWebDavPortNumber}:localhost:{intermediateWebDavPortNumber} {execHost} \'echo tunnel_hello; bash\'"'
        regex='tunnel_hello'
        siteConfigDict['webDavTunnel']=siteConfig.cmdRegEx(cmd,regex,async=True)

        cmd="\"/usr/bin/ssh {execHost} \\\"export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};echo \\\\\\\"import pexpect;child = pexpect.spawn('gvfs-mount dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}');child.expect('Password: ');child.sendline('{vncPasswd}')\\\\\\\" %s python %s%s /usr/bin/gconftool-2 --type=Boolean --set /apps/nautilus/preferences/always_use_location_entry true %s%s DISPLAY={vncDisplay} /usr/bin/nautilus --no-desktop --sm-disable dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName} %s%s echo WebDavMountingDone\\\"\"" % (pipe,ampersand,ampersand,ampersand,ampersand,ampersand,ampersand)
        regex='^.*(?P<webDavMountingDone>WebDavMountingDone).*$'
        siteConfigDict['openWebDavShareInRemoteFileBrowser']=siteConfig.cmdRegEx(cmd,regex)


        cmd='"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress}; DISPLAY={vncDisplay} xwininfo -root -tree\'"'
        regex= '^\s+(?P<webDavWindowID>\S+)\s+"{homeDirectoryWebDavShareName}.*Browser.*$'
        siteConfigDict['webDavWindowID']=siteConfig.cmdRegEx(cmd,regex)

        # 1. I'm using gvfs-mount --unmount-scheme dav for now, to unmount all GVFS WebDAV mounts,
        #    because using "gvfs-mount --unmount " on a specific mount point from a Launcher
        #    subprocess doesn't seem to work reliably, even though it works fine outside of the 
        #    Launcher.
        # 2. I'm using timeout with gvfs-mount, because sometimes the process never exits
        #    when unmounting, even though the unmounting operation is complete.
        #cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};DISPLAY={vncDisplay} wmctrl -F -c \"{homeDirectoryWebDavShareName} - File Browser\"; DISPLAY={vncDisplay} timeout 3 gvfs-mount -u \".gvfs/WebDAV on localhost\"\'"'
        cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};export DISPLAY={vncDisplay};timeout 1 gvfs-mount --unmount-scheme dav\'"'
        siteConfigDict['webDavUnmount']=siteConfig.cmdRegEx(cmd)

        cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};export DISPLAY={vncDisplay}; wmctrl -F -i -c {webDavWindowID}\'"'
        siteConfigDict['webDavCloseWindow']=siteConfig.cmdRegEx(cmd)








    return siteConfigDict

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

        sys.modules[__name__].massiveLauncherConfig = ConfigParser.RawConfigParser(allow_no_value=True)
        massiveLauncherConfig = sys.modules[__name__].massiveLauncherConfig
        sys.modules[__name__].massiveLauncherPreferencesFilePath = os.path.join(appUserDataDir,"MASSIVE Launcher Preferences.cfg")
        massiveLauncherPreferencesFilePath = sys.modules[__name__].massiveLauncherPreferencesFilePath
        if os.path.exists(massiveLauncherPreferencesFilePath):
            massiveLauncherConfig.read(massiveLauncherPreferencesFilePath)
        if not massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")

        sys.modules[__name__].cvlLauncherConfig = ConfigParser.RawConfigParser(allow_no_value=True)
        cvlLauncherConfig = sys.modules[__name__].cvlLauncherConfig
        sys.modules[__name__].cvlLauncherPreferencesFilePath = os.path.join(appUserDataDir,"CVL Launcher Preferences.cfg")
        cvlLauncherPreferencesFilePath = sys.modules[__name__].cvlLauncherPreferencesFilePath
        if os.path.exists(cvlLauncherPreferencesFilePath):
            cvlLauncherConfig.read(cvlLauncherPreferencesFilePath)
        if not cvlLauncherConfig.has_section("CVL Launcher Preferences"):
            cvlLauncherConfig.add_section("CVL Launcher Preferences")

        sys.modules[__name__].globalLauncherConfig = ConfigParser.RawConfigParser(allow_no_value=True)
        globalLauncherConfig = sys.modules[__name__].globalLauncherConfig
        sys.modules[__name__].globalLauncherPreferencesFilePath = os.path.join(appUserDataDir,"Global Preferences.cfg")
        globalLauncherPreferencesFilePath = sys.modules[__name__].globalLauncherPreferencesFilePath
        if os.path.exists(globalLauncherPreferencesFilePath):
            globalLauncherConfig.read(globalLauncherPreferencesFilePath)
        if not globalLauncherConfig.has_section("Global Preferences"):
            globalLauncherConfig.add_section("Global Preferences")

        logger.setGlobalLauncherConfig(globalLauncherConfig)
        logger.setGlobalLauncherPreferencesFilePath(globalLauncherPreferencesFilePath)

        if sys.platform.startswith("win"):
            os.environ['CYGWIN'] = "nodosfilewarning"
        sys.modules[__name__].launcherMainFrame = LauncherMainFrame(None, wx.ID_ANY, 'MASSIVE/CVL Launcher')
        launcherMainFrame = sys.modules[__name__].launcherMainFrame
        launcherMainFrame.Show(True)

        return True

if __name__ == '__main__':
    app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
    app.MainLoop()
