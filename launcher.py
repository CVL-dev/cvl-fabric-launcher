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
import cvlsshutils
import launcher_progress_dialog
from menus.IdentityMenu import IdentityMenu
import tempfile
from cvlsshutils.KeyModel import KeyModel

from logger.Logger import logger

global launcherMainFrame
launcherMainFrame = None
global launcherConfig
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
    PERM_SSH_KEY=0
    TEMP_SSH_KEY=1

    def loadPrefs(self,prefs,window,site=None):
        if (site==None):
            if prefs.has_option("siteConfigDefault"):
                siteConfigDefault = prefs.get("siteConfigDefault")
                if siteConfigDefault in configChoices:
                    siteConfigComboBox.SetValue(siteConfigDefault)
                    site=siteConfigDefault
        if (site != None):
            for item in window.GetChildren():
                if isinstance(item,wx.Control):
                    print "control name %s"%item.GetName()
                else:
                    print "Recusring"
                    self.loadPrefs(prefs,item,site)
#                   if prefs.has_section(site,'projects'):
#                       self.projects = prefs.get(site,projects)
#                   if prefs.has_section(site,'defaultProject'):
#                       project=prefs.get(site,'defaltProject')
#                       if project in self.projects:
#                           self.projectComboBox.SetSelection(project)
#                   if prefs.has_section(site,'hours'):
#                        self.hoursField.setvalue(prefs.get(site,'hours')
#                   if prefs.has_section(site,'nodes'):
#                        self.hoursField.setvalue(prefs.get(site,'nodes')
       # 
       # def savePrefs(prefs):
       #     if (prefsFilePath!=None):
       #         with(open(prefsFilePath,'wx') as prefsFileObject:
       #             prefs.write(prefsFileObject)


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
        import optionsDialog
        self.launcherOptionsDialog = optionsDialog.LauncherOptionsDialog(launcherMainFrame, wx.ID_ANY, "Preferences", self.vncOptions, 0)

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.menu_bar  = wx.MenuBar()

        if sys.platform.startswith("win") or sys.platform.startswith("linux"):
            self.file_menu = wx.Menu()
            self.file_menu.Append(wx.ID_EXIT, "E&xit", "Close window and exit program.")
            self.Bind(wx.EVT_MENU, self.onExit, id=wx.ID_EXIT)
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
        print "set the menu bar"

        self.loginDialogPanel = wx.Panel(self, wx.ID_ANY)
        self.loginDialogPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=15, hgap=5)

        self.tabbedView = wx.Notebook(self.loginDialogPanel, wx.ID_ANY, style=(wx.NB_TOP))
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,  self.onTabbedViewChanged, id=self.tabbedView.GetId())

        self.loginFieldsPanel = wx.Panel(self.tabbedView, wx.ID_ANY)
        #self.loginFieldsPanelSizer = wx.FlexGridSizer(rows=7, cols=2, vgap=3, hgap=5)
        self.loginFieldsPanelSizer = wx.BoxSizer(wx.VERTICAL)
        self.loginFieldsPanel.SetSizer(self.loginFieldsPanelSizer)

        widgetWidth1 = 180
        widgetWidth2 = 180
        if not sys.platform.startswith("win"):
            widgetWidth2 = widgetWidth2 + 25
        widgetWidth3 = 75

        self.siteConfigPanel = wx.Panel(self.loginFieldsPanel, wx.ID_ANY)
        self.siteConfigPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.configLabel = wx.StaticText(self.siteConfigPanel, wx.ID_ANY, 'Host')
        self.siteConfigPanelSizer.Add(self.configLabel, proportion=1, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border=5)
        configChoices=["choice 1","choice 2"]
        self.siteConfigComboBox = wx.ComboBox(self.siteConfigPanel, wx.ID_ANY, choices=configChoices, size=(widgetWidth2, -1), style=wx.CB_READONLY,name='jobParams_siteName')
        #self.siteConfigComboBox.Bind(wx.EVT_TEXT, self.onSiteConfigChanged)
        self.siteConfigPanelSizer.Add(self.siteConfigComboBox, proportion=0,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.siteConfigPanel.SetSizerAndFit(self.siteConfigPanelSizer)
        self.loginFieldsPanelSizer.Add(self.siteConfigPanel,proportion=0,flag=wx.EXPAND)

        # load the default site from the users preferences
        #loadPrefs(prefs)
        self.projectPanel = wx.Panel(self.loginFieldsPanel,wx.ID_ANY,name="projectPanel")
        self.projectPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.projectLabel = wx.StaticText(self.projectPanel, wx.ID_ANY, 'Project')
        self.projectPanelSizer.Add(self.projectLabel, proportion=1, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border=5)

        self.defaultProjectPlaceholder = '[Use my default project]'
        self.projects = ['[Use my defauly projec]']
        self.projectField = wx.ComboBox(self.projectPanel, wx.ID_ANY, value='', choices=self.projects, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN,name='jobParams_project')
        #self.projectComboBox.Bind(wx.EVT_TEXT, self.onProjectTextChanged)
        self.projectPanelSizer.Add(self.projectField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.projectPanel.SetSizerAndFit(self.projectPanelSizer)
        self.loginFieldsPanelSizer.Add(self.projectPanel, proportion=0,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)


        self.resourcePanel = wx.Panel(self.loginFieldsPanel, wx.ID_ANY)
        self.resourcePanelSizer = wx.FlexGridSizer(rows=1, cols=4, vgap=3, hgap=5)
        self.resourcePanel.SetSizer(self.resourcePanelSizer)

        self.hoursLabel = wx.StaticText(self.resourcePanel, wx.ID_ANY, 'Hours requested')
        self.resourcePanelSizer.Add(self.hoursLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        # Maximum of 336 hours is 2 weeks:
        #self.massiveHoursField = wx.SpinCtrl(self.massiveLoginFieldsPanel, wx.ID_ANY, value=self.massiveHoursRequested, min=1,max=336)
        self.hoursField = wx.SpinCtrl(self.resourcePanel, wx.ID_ANY, size=(widgetWidth3,-1), min=1,max=336,name='jobParams_hours')
        #self.massiveLoginFieldsPanelSizer.Add(self.massiveHoursField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.resourcePanelSizer.Add(self.hoursField, proportion=0,flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.nodesLabel = wx.StaticText(self.resourcePanel, wx.ID_ANY, 'Vis nodes')
        self.resourcePanelSizer.Add(self.nodesLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.nodesField = wx.SpinCtrl(self.resourcePanel, wx.ID_ANY, value="1", size=(widgetWidth3,-1), min=1,max=10,name='jobParams_nodes')
        self.resourcePanelSizer.Add(self.nodesField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.resourcePanel.SetSizerAndFit(self.resourcePanelSizer)
        self.loginFieldsPanelSizer.Add(self.resourcePanel, proportion=0,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)


        self.resolutionPanel = wx.Panel(self.loginFieldsPanel,name="resolutionPanel")
        self.resolutionPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.resolutionLabel = wx.StaticText(self.resolutionPanel, wx.ID_ANY, 'Resolution',name='label_resolution')
        self.resolutionPanelSizer.Add(self.resolutionLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        displaySize = wx.DisplaySize()
        desiredWidth = displaySize[0] * 0.99
        desiredHeight = displaySize[1] * 0.85
        defaultResolution = str(int(desiredWidth)) + "x" + str(int(desiredHeight))

        displaySize = wx.DisplaySize()
        desiredWidth = displaySize[0] * 0.99
        desiredHeight = displaySize[1] * 0.85
        defaultResolution = str(int(desiredWidth)) + "x" + str(int(desiredHeight))
        vncDisplayResolutions = [
            defaultResolution, "1024x768", "1152x864", "1280x800", "1280x1024", "1360x768", "1366x768", "1440x900", "1600x900", "1680x1050", "1920x1080", "1920x1200", "7680x3200",
            ]
        self.resolutionField = wx.ComboBox(self.resolutionPanel, wx.ID_ANY, value='', choices=vncDisplayResolutions, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN,name='jobParams_resolution')
        self.resolutionPanelSizer.Add(self.resolutionField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.resolutionPanel.SetSizerAndFit(self.resolutionPanelSizer)
        self.loginFieldsPanelSizer.Add(self.resolutionPanel,proportion=0,flag=wx.EXPAND)

        
        self.cipherPanel = wx.Panel(self.loginFieldsPanel,name="ciphersPanel")
        self.cipherPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sshTunnelCipherLabel = wx.StaticText(self.cipherPanel, wx.ID_ANY, 'SSH tunnel cipher',name='label_cipher')
        self.cipherPanelSizer.Add(self.sshTunnelCipherLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        if sys.platform.startswith("win"):
            defaultCipher = "arcfour"
            sshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour"]
        else:
            defaultCipher = "arcfour128"
            sshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour128"]
        self.sshTunnelCipherComboBox = wx.ComboBox(self.cipherPanel, wx.ID_ANY, value=defaultCipher, choices=sshTunnelCiphers, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN,name='jobParams_cipher')
        self.cipherPanelSizer.Add(self.sshTunnelCipherComboBox, proportion=0,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.cipherPanel.SetSizerAndFit(self.cipherPanelSizer)
        self.loginFieldsPanelSizer.Add(self.cipherPanel,proportion=0,flag=wx.EXPAND)

        self.usernamePanel=wx.Panel(self.loginFieldsPanel,name='usernamePanel')
        self.usernamePanelSizer=wx.BoxSizer(wx.HORIZONTAL)
        self.usernameLabel = wx.StaticText(self.usernamePanel, wx.ID_ANY, 'Username',name='label_username')
        self.usernamePanelSizer.Add(self.usernameLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        #self.usernameTextField = wx.TextCtrl(self.usernamePanel, wx.ID_ANY, size=(widgetWidth1, -1),name='jobParams_username')
        self.usernameTextField = wx.TextCtrl(self.usernamePanel, wx.ID_ANY, size=(widgetWidth2, -1),name='jobParams_username')
        self.usernamePanelSizer.Add(self.usernameTextField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=8)
        self.usernamePanel.SetSizerAndFit(self.usernamePanelSizer)
        self.loginFieldsPanelSizer.Add(self.usernamePanel,proportion=0,flag=wx.EXPAND)

        self.checkBoxPanel = wx.Panel(self.loginFieldsPanel)
        self.checkBoxPanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        p = wx.Panel(self.checkBoxPanel)
        s = wx.BoxSizer(wx.HORIZONTAL)

        p = wx.Panel(self.checkBoxPanel,name="debugCheckBoxPanel")
        s = wx.BoxSizer(wx.HORIZONTAL)
        l = wx.StaticText(p, wx.ID_ANY, 'Show debug window')
        c = wx.CheckBox(p, wx.ID_ANY, "")
        c.Bind(wx.EVT_CHECKBOX, self.onDebugWindowCheckBoxStateChanged)
        s.Add(l)
        s.Add(c)
        p.SetSizerAndFit(s)
        self.checkBoxPanelSizer.Add(p,flag=wx.ALIGN_LEFT)

        p = wx.Panel(self.checkBoxPanel,name="advancedCheckBoxPanel")
        s = wx.BoxSizer(wx.HORIZONTAL)
        l = wx.StaticText(p, wx.ID_ANY, 'Show Advanced Options')
        c = wx.CheckBox(p, wx.ID_ANY, "")
        c.Bind(wx.EVT_CHECKBOX, self.onAdvancedVisibilityStateChanged)
        s.Add(l)
        s.Add(c)
        p.SetSizerAndFit(s)
        self.checkBoxPanelSizer.Add(p,flag=wx.ALIGN_RIGHT)

        self.checkBoxPanel.SetSizerAndFit(self.checkBoxPanelSizer) 
        self.loginFieldsPanelSizer.Add(self.checkBoxPanel)

        self.tabbedView.AddPage(self.loginFieldsPanel, "Login")
        self.loadPrefs(None,self.tabbedView,'m2')

        self.loginDialogPanelSizer.Add(self.tabbedView, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=10)

        MASSIVE_TAB_INDEX = 0
        self.tabbedView.ChangeSelection(MASSIVE_TAB_INDEX)

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

        self.loginDialogStatusBar = LauncherStatusBar(self)
        self.SetStatusBar(self.loginDialogStatusBar)

        self.loginDialogPanel.SetSizerAndFit(self.loginDialogPanelSizer)
        print "setsizer and fit"
        self.loginDialogPanel.Layout()
        print "set sizer and layedout"

        self.Fit()
        self.Layout()
        self.menu_bar.Show(False)

        self.Centre()
        print "seup the panel and fit"

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
        MASSIVE_TAB_INDEX = 0
        CVL_TAB_INDEX =1
        if self.tabbedView.GetSelection()==MASSIVE_TAB_INDEX:
            logger.debug( "Using MASSIVE display strings.")
            self.displayStrings = sshKeyDistDisplayStringsMASSIVE()
        if self.tabbedView.GetSelection()==CVL_TAB_INDEX:
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

    def buildJobParams(self,window):
        jobParams={}
        for item in window.GetChildren():
            name = item.GetName()
            if ('jobParam' in name):
                (prefix,keyname) = name.split('_') 
                print "foudn parameter for %s"%keyname
                jobParams[keyname]=item.GetValue()
            r = self.buildJobParams(item)
            jobParams.update(r)
        return jobParams

    def onAdvancedVisibilityStateChanged(self, event):
        advanced=event.GetEventObject().GetValue()
        # hacky little dict to hide some stuff. Make this part of the site definition.
        visible={}
        visible['ciphersPanel']='Advanced'
        visible['resolutionPanel']='Advanced'
        visible['projectPanel']=False
        visible['debugCheckBoxPanel']='Advanced'
        for key in visible.keys():
            try:
                window=self.FindWindowByName(key) #Panels and controls are all subclasses of windows
                if visible[key]==False:
                    window.Hide()
                if visible[key]==True:
                    window.Show()
                if visible[key]=='Advanced' and advanced==True:
                    window.Show()
                else:
                    window.Hide()
            except:
                pass # a value in the dictionary didn't correspond to a named component of the panel. Fail silently.

    def onDebugWindowCheckBoxStateChanged(self, event):
        if launcherMainFrame.logWindow!=None:
            launcherMainFrame.logWindow.Show(event.GetEventObject().GetValue())

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


    def onOptions(self, event, tabIndex=0):

        self.launcherOptionsDialog.tabbedView.SetSelection(tabIndex)
        rv = self.launcherOptionsDialog.ShowModal()

        if rv == wx.OK:
            self.vncOptions = self.launcherOptionsDialog.getVncOptions()
            self.saveGlobalOptions()
    
    def saveGlobalOptions(self):

        for key in self.vncOptions:
            turboVncConfig.set("TurboVNC Preferences", key, self.vncOptions[key])

        with open(turboVncPreferencesFilePath, 'wb') as turboVncPreferencesFileObject:
            turboVncConfig.write(turboVncPreferencesFileObject)


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

        self.cvlConnectionProfileComboBox.SetCursor(cursor)
        self.cvlUsernameTextField.SetCursor(cursor)
        self.cvlVncDisplayResolutionComboBox.SetCursor(cursor)
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
        auth_mode=self.launcherOptionsDialog.FindWindowByName(var)
        choices=[]
        for i in range(auth_mode.GetCount()):
            choices.append(auth_mode.GetString(i))
        dlg = LauncherOptionsDialog.LauncherOptionsDialog(launcherMainFrame,"""
Would you like to use an SSH Key pair or your password to authenticate yourself?
Most of the time, an SSH Key pair is preferable.
If this account is shared by a number of people then passwords are preferable
""",title="MASSIVE/CVL Launcher",ButtonLabels=choices)
        rv=dlg.ShowModal()
        if rv in range(auth_mode.GetCount()):
            return int(rv)
        else:
            self.queryAuthMode()

    def onLogin(self, event):
        MASSIVE_TAB_INDEX = 0
        CVL_TAB_INDEX =1
        jobParams={}
        jobParams = self.buildJobParams(self)
        if jobParams['username'] == "":
            dlg = wx.MessageDialog(launcherMainFrame,
                    "Please enter your username.",
                    "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            usernamefield = self.FindWindowByName('jobParams_username')
            usernamefield.SetFocus()
            return


        if (self.logWindow == None):

            #self.logWindow = wx.Frame(self, title='{configName} Login'.format(**jobParams), name='{configName} Login'.format(**jobParams),pos=(200,150),size=(700,450))
            self.logWindow = wx.Frame(self, title='Debug Log'.format(**jobParams), pos=(200,150),size=(700,450))
            #self.logWindow.Bind(wx.EVT_CLOSE, self.onCloseDebugWindow)

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

        self.logWindow.Show(True)


        userCanAbort=True
        maximumProgressBarValue = 10

        try:
            os.mkdir(os.path.join(os.path.expanduser('~'), '.ssh'))
        except:
            logger.debug(traceback.format_exc())
            pass

        # project hours and nodes will be ignored for the CVL login, but they will be used for Massive.
        configName=host
        if not self.vncOptions.has_key('auth_mode'):
            mode=self.queryAuthMode()
            self.vncOptions['auth_mode']=mode
            self.launcherOptionsDialog.FindWindowByName('auth_mode').SetSelection(mode)
            self.identity_menu.disableItems()
            self.saveGlobalOptions()
        siteConfigDict = buildSiteConfigCmdRegExDict(configName) #eventually this will be loaded from json downloaded from a website
        jobParams=self.buildJobParams(self)
        jobParams['wallseconds']=int(jobParams['hours'])*60*60
        siteConfigDict = buildSiteConfigDict(configName) #eventually this will be loaded from json downloaded from a website
        siteConfigObj = siteConfig(siteConfigDict)
        if launcherMainFrame.launcherOptionsDialog.FindWindowByName('auth_mode').GetSelection()==LauncherMainFrame.TEMP_SSH_KEY:
            logger.debug("launcherMainFrame.onLogin: using a temporary Key pair")
            try:
                del os.environ['SSH_AUTH_SOCK']
                logger.debug("launcherMainFrame.onLogin: spawning an ssh-agent (not using the existing agent)")
            except:
                logger.debug("launcherMainFrame.onLogin: spawning an ssh-agent (no existing agent found)")
                pass
            launcherMainFrame.keyModel=KeyModel(temporaryKey=True)
            removeKeyOnExit = True
        else:
            logger.debug("launcherMainFrame.onLogin: using a permanent Key pair")
            launcherMainFrame.keyModel=KeyModel(temporaryKey=False)
            removeKeyOnExit = False
        self.loginProcess=LoginTasks.LoginProcess(launcherMainFrame,jobParams,launcherMainFrame.keyModel,siteConfig=siteConfigObj,displayStrings=self.displayStrings,autoExit=autoExit,vncOptions=self.vncOptions,removeKeyOnExit=removeKeyOnExit)
        self.loginProcess.doLogin()


        def initializeProgressDialog():
            CancelCallback=self.loginProcess.cancel
            self.progressDialog = launcher_progress_dialog.LauncherProgressDialog(self, wx.ID_ANY, 'Connecting to {configCN}...'.format(**jobParams), "", maximumProgressBarValue, userCanAbort,CancelCallback)

#        wx.CallAfter(initializeProgressDialog)



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
        self.displayWebDavInfoDialogOnRemoteDesktop=siteConfig.cmdRegEx()
        self.webDavTunnel=siteConfig.cmdRegEx()
        self.webDavUnmount=siteConfig.cmdRegEx()
        self.__dict__.update(siteConfigDict)

def buildSiteConfigCmdRegExDict(configName):
    import re
    if sys.platform.startswith("win"):
        lt = "^<"
        gt = "^>"
        pipe = "^|"
    else:
        lt = "<"
        gt = ">"
        pipe = "|"
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

        #cmd='"/usr/bin/ssh {execHost} \'DISPLAY={vncDisplay} /usr/bin/konqueror webdav://{localUsername}:{vncPasswd}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName} && /usr/local/desktop/get_pid_of_active_window.sh\'"'
        #regex='^(?P<webDavKonquerorWindowPid>[0-9]+)$'
        #siteConfigDict['openWebDavShareInRemoteFileBrowser']=siteConfig.cmdRegEx(cmd,regex)
        cmd='"/usr/bin/ssh {execHost} \'DISPLAY={vncDisplay} /usr/bin/konqueror webdav://{localUsername}:{vncPasswd}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\'"'
        siteConfigDict['openWebDavShareInRemoteFileBrowser']=siteConfig.cmdRegEx(cmd)

#        cmd='"/usr/bin/ssh {execHost} \'echo -e \\"You can access your local home directory in Konqueror with the URL:%sbr%s\\nwebdav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}%sbr%s\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt; sleep 2; DISPLAY={vncDisplay} kdialog --title \\"MASSIVE/CVL Launcher\\" --textbox ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt 490 150\'"' % (lt,gt,lt,gt)
        cmd='"/usr/bin/ssh {execHost} \'echo -e \\"You can access your local home directory in Konqueror with the URL:%sbr%s\\nwebdav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}%sbr%s\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt;\'"'
        siteConfigDict['displayWebDavInfoDialogOnRemoteDesktop'] = siteConfig.cmdRegEx(cmd)

        # Chris trying to avoid using the intermediate port:
        #cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {execHost}:{remoteWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"'

        #cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -T -R {intermediateWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "ssh -T -R {remoteWebDavPortNumber}:localhost:{intermediateWebDavPortNumber} {execHost} \'echo tunnel_hello; bash\'"'
        cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {intermediateWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "ssh -R {remoteWebDavPortNumber}:localhost:{intermediateWebDavPortNumber} {execHost} \'echo tunnel_hello; bash\'"'
        regex='tunnel_hello'
        siteConfigDict['webDavTunnel']=siteConfig.cmdRegEx(cmd,regex,async=True)

        cmd = '"/usr/bin/ssh {execHost} \'DISPLAY={vncDisplay} /usr/local/desktop/close_webdav_window.sh webdav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\'"'
        # Maybe call server-side script to do something like this:
        #for konq in `dcop konqueror-*`; do KONQPID=`echo $konq | tr '-' '\n' | tail -1`; if [ "`dcop $konq konqueror-mainwindow#1 currentTitle`" == 'webdav://wettenhj@localhost:56865/wettenhj' ]; then kill $KONQPID; fi; done

        siteConfigDict['webDavUnmount']=siteConfig.cmdRegEx(cmd)

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
        #siteConfigDict['vncDisplay']= siteConfig.cmdRegEx('" /usr/bin/ssh {execHost} \' cat /var/spool/torque/spool/{jobidNumber}.*\'"' ,'^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$')
        siteConfigDict['vncDisplay']= siteConfig.cmdRegEx('\"cat /var/spool/torque/spool/{jobidNumber}.*\"' ,'^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$',host='exec')
        cmd= '\"module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\"'
        regex='^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$'
        siteConfigDict['otp']=siteConfig.cmdRegEx(cmd,regex,host='exec')
        siteConfigDict['agent']=siteConfig.cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -l {username} {execHost} "echo agent_hello; bash "','agent_hello',async=True)
        siteConfigDict['tunnel']=siteConfig.cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -L {localPortNumber}:localhost:{remotePortNumber} -l {username} {execHost} "echo tunnel_hello; bash"','tunnel_hello',async=True)

        cmd='"/usr/bin/ssh {execHost} \'MACHINE_ID=\\$(cat /var/lib/dbus/machine-id); cat ~/.dbus/session-bus/\\$MACHINE_ID-\\$(echo {vncDisplay} | tr -d \\":\\" | tr -d \\".0\\")\'"'
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
        cmd="\"/usr/bin/ssh {execHost} \\\"export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};echo \\\\\\\"import pexpect;child = pexpect.spawn('gvfs-mount dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}');child.expect('Password: ');child.sendline('{vncPasswd}')\\\\\\\" %s python;/usr/bin/gconftool-2 --type=Boolean --set /apps/nautilus/preferences/always_use_location_entry true;DISPLAY={vncDisplay} /usr/bin/nautilus --no-desktop --sm-disable dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName};\\\"\"" % (pipe)
        siteConfigDict['openWebDavShareInRemoteFileBrowser']=siteConfig.cmdRegEx(cmd)

        #cmd = '"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" | DISPLAY={vncDisplay} zenity --title \\"MASSIVE/CVL Launcher\\" --text-info --width 490 --height 175\'"'
        cmd = '"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt\'"'
        siteConfigDict['displayWebDavInfoDialogOnRemoteDesktop']=siteConfig.cmdRegEx(cmd)

        cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {remoteWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {execHost} "echo tunnel_hello; bash"'
        regex='tunnel_hello'
        siteConfigDict['webDavTunnel']=siteConfig.cmdRegEx(cmd,regex,async=True)

        # 1. Due to a bug in gvfs-mount, I'm using timeout, so it doesn't matter if "gvfs-mount -u" never exits.
        # 2. I'm using gvfs-mount --unmount-scheme dav for now, to unmount all GVFS WebDAV mounts,
        #    because otherwise it's too painful to refer to the specific mount point at "$HOME/.gvfs/WebDAV on localhost",
        #    because the $HOME environment variable could be evaluated in the wrong shell.
        # 3. The wmctrl command to close the Nautilus window doesn't seem to work from the Launcher,
        #    even though it seems to work fine when I run paste the command used by the Launcher's
        #    subprocess into a Terminal window.  Maybe I should use the same method I'm using for
        #    Konqueror instead (which is a server-side script).
        # 4. Occassionally the DBUS_SESSION_BUS_ADDRESS environment variable gets out of sync with
        #    ~/.dbus/session-bus/$MACHINE_ID-$DISPLAY which causes gvfs-mount etc. to fail.
        #cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};DISPLAY={vncDisplay} wmctrl -F -c \"{homeDirectoryWebDavShareName} - File Browser\"; DISPLAY={vncDisplay} timeout 3 gvfs-mount -u \"$HOME/.gvfs/WebDAV on localhost\"\'"'
        cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};DISPLAY={vncDisplay} wmctrl -F -c \"{homeDirectoryWebDavShareName} - File Browser\"; DISPLAY={vncDisplay} timeout 3 gvfs-mount --unmount-scheme dav\'"'
        siteConfigDict['webDavUnmount']=siteConfig.cmdRegEx(cmd)
    else:
        siteConfigDict['listAll']=siteConfig.cmdRegEx('\'module load turbovnc ; vncserver -list\'','^(?P<vncDisplay>:[0-9]+)\s+[0-9]+\s*$',requireMatch=False)
        siteConfigDict['startServer']=siteConfig.cmdRegEx('\"/usr/local/bin/vncsession --vnc turbovnc --geometry {resolution}\"','^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$')
        siteConfigDict['stop']=siteConfig.cmdRegEx('\'module load turbovnc ; vncserver -kill {vncDisplay}\'')
        siteConfigDict['otp']= siteConfig.cmdRegEx('\'module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\'','^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$')
        siteConfigDict['agent']=siteConfig.cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -l {username} {loginHost} "echo agent_hello; bash "','agent_hello',async=True)
        siteConfigDict['tunnel']=siteConfig.cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -L {localPortNumber}:localhost:{remotePortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"','tunnel_hello',async=True)

        cmd='"/usr/bin/ssh {execHost} \'MACHINE_ID=\\$(cat /var/lib/dbus/machine-id); cat ~/.dbus/session-bus/\\$MACHINE_ID-\\$(echo {vncDisplay} | tr -d \\":\\" | tr -d \\".0\\")\'"'
        regex='^DBUS_SESSION_BUS_ADDRESS=(?P<dbusSessionBusAddress>.*)$'
        siteConfigDict['dbusSessionBusAddress']=siteConfig.cmdRegEx(cmd,regex)

        cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {intermediateWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "ssh -R {remoteWebDavPortNumber}:localhost:{intermediateWebDavPortNumber} {execHost} \'echo tunnel_hello; bash\'"'
        regex='tunnel_hello'
        siteConfigDict['webDavTunnel']=siteConfig.cmdRegEx(cmd,regex,async=True)

        cmd="\"/usr/bin/ssh {execHost} \\\"export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};echo \\\\\\\"import pexpect;child = pexpect.spawn('gvfs-mount dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}');child.expect('Password: ');child.sendline('{vncPasswd}')\\\\\\\" %s python;/usr/bin/gconftool-2 --type=Boolean --set /apps/nautilus/preferences/always_use_location_entry true;DISPLAY={vncDisplay} /usr/bin/nautilus --no-desktop --sm-disable dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName};\\\"\"" % (pipe)
        siteConfigDict['openWebDavShareInRemoteFileBrowser']=siteConfig.cmdRegEx(cmd)

        #cmd = '"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" | DISPLAY={vncDisplay} zenity --title \\"MASSIVE/CVL Launcher\\" --text-info --width 490 --height 175\'"'
        cmd = '"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt\'"'
        siteConfigDict['displayWebDavInfoDialogOnRemoteDesktop']=siteConfig.cmdRegEx(cmd)

        # 1. Due to a bug in gvfs-mount, I'm using timeout, so it doesn't matter if "gvfs-mount -u" never exits.
        # 2. I'm using gvfs-mount --unmount-scheme dav for now, to unmount all GVFS WebDAV mounts,
        #    because otherwise it's too painful to refer to the specific mount point at "$HOME/.gvfs/WebDAV on localhost",
        #    because the $HOME environment variable could be evaluated in the wrong shell.
        # 3. The wmctrl command to close the Nautilus window doesn't seem to work from the Launcher,
        #    even though it seems to work fine when I run paste the command used by the Launcher's
        #    subprocess into a Terminal window.  Maybe I should use the same method I'm using for
        #    Konqueror instead (which is a server-side script).
        # 4. Occassionally the DBUS_SESSION_BUS_ADDRESS environment variable gets out of sync with
        #    ~/.dbus/session-bus/$MACHINE_ID-$DISPLAY which causes gvfs-mount etc. to fail.
        #cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};DISPLAY={vncDisplay} wmctrl -F -c \"{homeDirectoryWebDavShareName} - File Browser\"; DISPLAY={vncDisplay} timeout 3 gvfs-mount -u \"$HOME/.gvfs/WebDAV on localhost\"\'"'
        cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};DISPLAY={vncDisplay} wmctrl -F -c \"{homeDirectoryWebDavShareName} - File Browser\"; DISPLAY={vncDisplay} timeout 3 gvfs-mount --unmount-scheme dav\'"'
        siteConfigDict['webDavUnmount']=siteConfig.cmdRegEx(cmd)








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
        launcherMainFrame.menu_bar.Show(True)


#        if massiveLauncherConfig is not None:
#            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_launcher_private_key_path", launcherMainFrame.keyModel.getsshKeyPath())
#            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
#                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)


        return True

if __name__ == '__main__':
    app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
    app.MainLoop()
