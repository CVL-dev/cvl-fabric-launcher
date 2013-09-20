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
import siteConfig

from MacMessageDialog import LauncherMessageDialog
from logger.Logger import logger
import collections


class LauncherMainFrame(wx.Frame):
    PERM_SSH_KEY=0
    TEMP_SSH_KEY=1


    def shouldSave(self,item):
        # I should be able to use a python iterator here
        shouldSave=False
        for ctrl in self.savedControls:
            if isinstance(item,ctrl):
                shouldSave=True
        return shouldSave

    
    def loadPrefs(self,window=None,site=None):
        if (self.prefs==None):
            self.prefs=ConfigParser.RawConfigParser(allow_no_value=True)
            if (os.path.exists(launcherPreferencesFilePath)):
                with open(launcherPreferencesFilePath,'r') as o:
                    self.prefs.readfp(o)
        if window==None:
            window=self
        window.Freeze()
        if (site==None):
            siteConfigComboBox=self.FindWindowByName('jobParams_configName')
            site=siteConfigComboBox.GetValue()
            if (site==None or site==""):
                if self.prefs.has_option("Launcher Config","siteConfigDefault"):
                    siteConfigDefault = self.prefs.get("Launcher Config","siteConfigDefault")
                    if siteConfigDefault in self.sites.keys():
                        siteConfigComboBox.SetValue(siteConfigDefault)
                        site=siteConfigDefault
                        self.loadPrefs(window=self,site=site)
                        #self.updateVisibility()
        if (site != None):
            if self.prefs.has_section(site):
                for item in window.GetChildren():
                    if self.shouldSave(item):
                        name=item.GetName()
                        if self.prefs.has_option(site,name):
                            val=self.prefs.get(site,name)
                            try: # Most wx Controls expect a string in SetValue, but at least SpinCtrl expects an int.
                                item.SetValue(val)
                            except TypeError:
                                item.SetValue(int(val))
                    else:
                        self.loadPrefs(window=item,site=site)
        window.Thaw()

    def savePrefsEventHandler(self,event):
        threading.Thread(target=self.savePrefs).start()
        event.Skip()
        
    def savePrefs(self,prefs=None,window=None,site=None):
        write=False
        # If we called savePrefs without a window specified, its the root of recussion
        if (window==None):
            write=True
            window=self
        if (site==None):
            configName=self.FindWindowByName('jobParams_configName').GetValue()
            if (configName!=None):
                if (not self.prefs.has_section("Launcher Config")):
                    self.prefs.add_section("Launcher Config")
                self.prefs.set("Launcher Config","siteConfigDefault",configName)
                self.savePrefs(prefs=prefs,site=configName)
        elif (site!=None):
            if (not self.prefs.has_section(site)):
                self.prefs.add_section(site)
            for item in window.GetChildren():
                if self.shouldSave(item):
                    self.prefs.set(site,item.GetName(),item.GetValue())
                else:
                    self.savePrefs(prefs=prefs,site=site,window=item)
        if (write):
            with open(launcherPreferencesFilePath,'w') as o:
                self.prefs.write(o)


    def __init__(self, parent, id, title):

        super(LauncherMainFrame,self).__init__(parent, id, title, style=wx.DEFAULT_FRAME_STYLE )
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.SetAutoLayout(0)

        self.savedControls=[]
        self.savedControls.append(wx.TextCtrl)
        self.savedControls.append(wx.ComboBox)
        self.savedControls.append(wx.SpinCtrl)

        self.prefs=None
        self.loginProcess=[]
        self.logWindow = None
        self.progressDialog = None




        self.vncOptions = {}
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

        self.launcherOptionsDialog = optionsDialog.LauncherOptionsDialog(self, wx.ID_ANY, "VNC Options", self.vncOptions, 0)
        self.launcherOptionsDialog.Show(False)

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.menu_bar  = wx.MenuBar()

        self.file_menu = wx.Menu()
        self.menu_bar.Append(self.file_menu, "&File")
        shareDesktop=wx.MenuItem(self.file_menu,wx.ID_ANY,"&Share my Desktop")
        self.file_menu.AppendItem(shareDesktop)
        self.Bind(wx.EVT_MENU, self.saveSessionEvent, id=shareDesktop.GetId())
        loadSession=wx.MenuItem(self.file_menu,wx.ID_ANY,"&Load a saved Session")
        self.file_menu.AppendItem(loadSession)
        self.Bind(wx.EVT_MENU, self.loadSessionEvent, id=loadSession.GetId())
        loadDefaultSessions=wx.MenuItem(self.file_menu,wx.ID_ANY,"&Load default sessions")
        self.file_menu.AppendItem(loadDefaultSessions)
        self.Bind(wx.EVT_MENU, self.loadDefaultSessionsEvent, id=loadDefaultSessions.GetId())
        if sys.platform.startswith("win") or sys.platform.startswith("linux"):
            self.file_menu = wx.Menu()
            self.file_menu.Append(wx.ID_EXIT, "E&xit", "Close window and exit program.")
            self.Bind(wx.EVT_MENU, self.onExit, id=wx.ID_EXIT)
           
            

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
        self.identity_menu.initialize(self)
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


        self.loginDialogPanel = wx.Panel(self, wx.ID_ANY)
        self.loginDialogPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.GetSizer().Add(self.loginDialogPanel)

        self.loginFieldsPanel = wx.Panel(self.loginDialogPanel, wx.ID_ANY)
        self.loginFieldsPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.loginDialogPanel.GetSizer().Add(self.loginFieldsPanel, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=10)

        widgetWidth1 = 180
        widgetWidth2 = 180
        if not sys.platform.startswith("win"):
            widgetWidth2 = widgetWidth2 + 25
        widgetWidth3 = 75

        DEFAULT_SITES_JSON='defaultSites.json'
        self.defaultSites={}
        with open(DEFAULT_SITES_JSON,'r') as f:
            self.defaultSites=siteConfig.GenericJSONDecoder().decode(f.read())
        if (isinstance(self.defaultSites,list)):
            keyorder=self.defaultSites[0]
            defaultSites=collections.OrderedDict()
            for key in keyorder:
                defaultSites[key]=self.defaultSites[1][key]
            self.defaultSites=defaultSites
        
        self.noneVisible={}
        self.noneVisible['usernamePanel']=False
        self.noneVisible['projectPanel']=False
        self.noneVisible['execHostPanel']=False
        self.noneVisible['resourcePanel']=False
        self.noneVisible['resolutionPanel']=False
        self.noneVisible['cipherPanel']=False
        self.noneVisible['debugCheckBoxPanel']=False
        self.noneVisible['advancedCheckBoxPanel']=False
        self.noneVisible['optionsDialog']=False

        self.sites=self.defaultSites.copy()

        self.siteConfigPanel = wx.Panel(self.loginFieldsPanel, wx.ID_ANY)
        self.siteConfigPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.configLabel = wx.StaticText(self.siteConfigPanel, wx.ID_ANY, 'Site')
        self.siteConfigPanel.GetSizer().Add(self.configLabel, proportion=0, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND, border=5)
        self.siteConfigComboBox = wx.ComboBox(self.siteConfigPanel, wx.ID_ANY, choices=self.sites.keys(), value='', style=wx.CB_READONLY,name='jobParams_configName')
        self.siteConfigComboBox.Bind(wx.EVT_TEXT, self.onSiteConfigChanged)
        self.siteConfigPanel.GetSizer().Add(self.siteConfigComboBox, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.loginFieldsPanel.GetSizer().Add(self.siteConfigPanel,proportion=0,flag=wx.EXPAND)

        self.loginHostPanel=wx.Panel(self.loginFieldsPanel,name='loginHostPanel')
        self.loginHostPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.loginHostLabel = wx.StaticText(self.loginHostPanel, wx.ID_ANY, 'Server name or IP',name='label_loginHost')
        self.loginHostPanel.GetSizer().Add(self.loginHostLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.loginHostTextField = wx.TextCtrl(self.loginHostPanel, wx.ID_ANY, size=(widgetWidth2, -1),name='jobParams_loginHost')
        self.loginHostPanel.GetSizer().Add(self.loginHostTextField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.loginFieldsPanel.GetSizer().Add(self.loginHostPanel,proportion=0,flag=wx.EXPAND)


        self.usernamePanel=wx.Panel(self.loginFieldsPanel,name='usernamePanel')
        self.usernamePanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.usernameLabel = wx.StaticText(self.usernamePanel, wx.ID_ANY, 'Username',name='label_username')
        self.usernamePanel.GetSizer().Add(self.usernameLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.usernameTextField = wx.TextCtrl(self.usernamePanel, wx.ID_ANY, size=(widgetWidth2, -1),name='jobParams_username')
        self.usernamePanel.GetSizer().Add(self.usernameTextField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.loginFieldsPanel.GetSizer().Add(self.usernamePanel,proportion=0,flag=wx.EXPAND)

        self.projectPanel = wx.Panel(self.loginFieldsPanel,wx.ID_ANY,name="projectPanel")
        self.projectPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.projectLabel = wx.StaticText(self.projectPanel, wx.ID_ANY, 'Project')
        self.projectPanel.GetSizer().Add(self.projectLabel, proportion=1, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border=5)

        self.defaultProjectPlaceholder = '[Use my default project]'
        self.projects = ['[Use my default projec]']
        self.projectField = wx.ComboBox(self.projectPanel, wx.ID_ANY, value='', choices=self.projects, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN,name='jobParams_project')
        #self.projectComboBox.Bind(wx.EVT_TEXT, self.onProjectTextChanged)
        self.projectPanel.GetSizer().Add(self.projectField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.loginFieldsPanel.GetSizer().Add(self.projectPanel, proportion=0,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)

        self.resourcePanel = wx.Panel(self.loginFieldsPanel, wx.ID_ANY,name="resourcePanel")
        self.resourcePanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))

        self.hoursLabel = wx.StaticText(self.resourcePanel, wx.ID_ANY, 'Hours requested')
        self.resourcePanel.GetSizer().Add(self.hoursLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,border=5)
        # Maximum of 336 hours is 2 weeks:
        #self.massiveHoursField = wx.SpinCtrl(self.massiveLoginFieldsPanel, wx.ID_ANY, value=self.massiveHoursRequested, min=1,max=336)
        self.hoursField = wx.SpinCtrl(self.resourcePanel, wx.ID_ANY, size=(widgetWidth3,-1), min=1,max=336,name='jobParams_hours')
        self.resourcePanel.GetSizer().Add(self.hoursField, proportion=0,flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,border=5)
        self.nodesLabel = wx.StaticText(self.resourcePanel, wx.ID_ANY, 'Vis nodes')
        self.resourcePanel.GetSizer().Add(self.nodesLabel, proportion=0,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,border=5)
        self.nodesField = wx.SpinCtrl(self.resourcePanel, wx.ID_ANY, value="1", size=(widgetWidth3,-1), min=1,max=10,name='jobParams_nodes')
        self.resourcePanel.GetSizer().Add(self.nodesField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.loginFieldsPanel.GetSizer().Add(self.resourcePanel, proportion=0,border=0,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)


        self.resolutionPanel = wx.Panel(self.loginFieldsPanel,name="resolutionPanel")
        self.resolutionPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.resolutionLabel = wx.StaticText(self.resolutionPanel, wx.ID_ANY, 'Resolution',name='label_resolution')
        self.resolutionPanel.GetSizer().Add(self.resolutionLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

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
        self.resolutionField = wx.ComboBox(self.resolutionPanel, wx.ID_ANY, value=defaultResolution, choices=vncDisplayResolutions, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN,name='jobParams_resolution')
        self.resolutionPanel.GetSizer().Add(self.resolutionField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.loginFieldsPanel.GetSizer().Add(self.resolutionPanel,proportion=0,flag=wx.EXPAND)

        
        self.cipherPanel = wx.Panel(self.loginFieldsPanel,name="cipherPanel")
        self.cipherPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.sshTunnelCipherLabel = wx.StaticText(self.cipherPanel, wx.ID_ANY, 'SSH tunnel cipher',name='label_cipher')
        self.cipherPanel.GetSizer().Add(self.sshTunnelCipherLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        if sys.platform.startswith("win"):
            defaultCipher = "arcfour"
            sshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour"]
        else:
            defaultCipher = "arcfour128"
            sshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour128"]
        self.sshTunnelCipherComboBox = wx.ComboBox(self.cipherPanel, wx.ID_ANY, value=defaultCipher, choices=sshTunnelCiphers, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN,name='jobParams_cipher')
        self.cipherPanel.GetSizer().Add(self.sshTunnelCipherComboBox, proportion=0,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.loginFieldsPanel.GetSizer().Add(self.cipherPanel,proportion=0,flag=wx.EXPAND)
        self.checkBoxPanel = wx.Panel(self.loginFieldsPanel,name="checkBoxPanel")
        self.checkBoxPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        
        p = wx.Panel(self.checkBoxPanel,name="debugCheckBoxPanel")
        p.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        l = wx.StaticText(p, wx.ID_ANY, 'Show debug window')
        c = wx.CheckBox(p, wx.ID_ANY, "",name='debugCheckBox')
        c.Bind(wx.EVT_CHECKBOX, self.onDebugWindowCheckBoxStateChanged)
        p.GetSizer().Add(l,border=5,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        p.GetSizer().Add(c,border=5,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        self.checkBoxPanel.GetSizer().Add(p,flag=wx.ALIGN_LEFT)
    
        t=wx.StaticText(self.checkBoxPanel,label="")
        self.checkBoxPanel.GetSizer().Add(t,proportion=1,flag=wx.EXPAND)
  
        p = wx.Panel(self.checkBoxPanel,name="advancedCheckBoxPanel")
        p.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        l = wx.StaticText(p, wx.ID_ANY, 'Show Advanced Options')
        c = wx.CheckBox(p, wx.ID_ANY, "",name='advancedCheckBox')
        c.Bind(wx.EVT_CHECKBOX, self.onAdvancedVisibilityStateChanged)
        p.GetSizer().Add(l,border=5,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        p.GetSizer().Add(c,border=5,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        self.checkBoxPanel.GetSizer().Add(p,flag=wx.ALIGN_RIGHT)

        self.loginFieldsPanel.GetSizer().Add(self.checkBoxPanel,flag=wx.ALIGN_BOTTOM)

        #self.tabbedView.AddPage(self.loginFieldsPanel, "Login")

        #self.loginDialogPanelSizer.Add(self.tabbedView, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=10)

        #MASSIVE_TAB_INDEX = 0
        #self.tabbedView.ChangeSelection(MASSIVE_TAB_INDEX)

        # Buttons Panel

        self.buttonsPanel = wx.Panel(self.loginDialogPanel, wx.ID_ANY)
        #self.buttonsPanel.SetSizer(wx.FlexGridSizer(rows=1, cols=4, vgap=5, hgap=10))
        self.buttonsPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))

        self.preferencesButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Preferences')
        self.buttonsPanel.GetSizer().Add(self.preferencesButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.onOptions, id=self.preferencesButton.GetId())

        self.exitButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Exit')
        self.buttonsPanel.GetSizer().Add(self.exitButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.onExit,  id=self.exitButton.GetId())

        self.loginButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Login')
        self.buttonsPanel.GetSizer().Add(self.loginButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.loginButton.Bind(wx.EVT_BUTTON, self.savePrefsEventHandler)
        self.loginButton.Bind(wx.EVT_BUTTON, self.onLogin)
        self.loginButton.SetDefault()


        #self.preferencesButton.Show(False)

        self.loginDialogPanel.GetSizer().Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=15)

        self.loginDialogStatusBar = LauncherStatusBar(self)


        #self.Fit()
        #self.Layout()
        #self.menu_bar.Show(False)

        #self.Centre()

        self.logWindow = wx.Frame(self, title="MASSIVE/CVL Launcher Debug Log", name="MASSIVE/CVL Launcher Debug Log",pos=(200,150),size=(700,450))
        #self.logWindow.Bind(wx.EVT_CLOSE, self.onCloseDebugWindow)
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
        self.contacted_massive_website = False
        #self.loadPrefs()
#        self.checkVersionNumber()


    def loadSessionEvent(self,event):
        dlg=wx.FileDialog(self,"Load a session",style=wx.FD_OPEN)
        status=dlg.ShowModal()
        if status==wx.ID_CANCEL:
            logger.debug('loadSession cancled')
        f=open(dlg.GetPath(),'r')
        self.loadSession(f)
        f.close()

    def loadSession(self,f):
        import json
        saved=GenericJSONDecoder().decode(f.read())
        self.sites=saved
        cb=self.FindWindowByName('jobParams_configName')
        cbid=cb.GetId()
        size=cb.GetSize()
        pos=cb.GetPosition()
        si=self.siteConfigPanel.GetSizer().GetItem(cb)
        si.DeleteWindows()
        cb = wx.ComboBox(self.siteConfigPanel, cbid, choices=self.sites.keys(), value=self.sites.keys()[0], style=wx.CB_READONLY,name='jobParams_configName')
        cb.Bind(wx.EVT_TEXT, self.onSiteConfigChanged)
        cb.SetSize(size)
        cb.SetPosition(pos)
        si.SetWindow(cb)
        self.updateVisibility()

    def loadDefaultSessions(self):
        self.sites=self.defaultSites.copy()
        cb=self.FindWindowByName('jobParams_configName')
        cbid=cb.GetId()
        size=cb.GetSize()
        pos=cb.GetPosition()
        si=self.siteConfigPanel.GetSizer().GetItem(cb)
        si.DeleteWindows()
        cb = wx.ComboBox(self.siteConfigPanel, cbid, choices=self.sites.keys(), value='', style=wx.CB_READONLY,name='jobParams_configName')
        cb.Bind(wx.EVT_TEXT, self.onSiteConfigChanged)
        cb.SetSize(size)
        cb.SetPosition(pos)
        si.SetWindow(cb)
        self.updateVisibility(self.noneVisible)

    def loadDefaultSessionsEvent(self,event):
        self.loadDefaultSessions()

    def saveSessionEvent(self,event):
        self.saveSession()


    def saveSessionThreadTarget(self,q):
        filename = q.get(block=True)
        siteConfig = q.get(block=True)
        if siteConfig!=None and filename!=None:
            try:
                f=open(filename,'w')
                logger.debug('opened file %s to save the session to'%filename)
            except Exception as e:
                logger.debug('error opening file for saving')
                raise e
            logger.debug('retrieved the session configuration from the loginProcess')
        if siteConfig==None:
            siteConfig=q.get()
        if siteConfig==None:
            return
        mydict={}
        mydict['Saved Session']=siteConfig
        import json
        s=json.dumps(mydict,f,cls=GenericJSONEncoder,sort_keys=True,indent=4,separators=(',',': '))
        f.write(s)
        f.close()

        


    def saveSession(self):
        print "in Savesession"
        import Queue
        q=Queue.Queue()
        dlg=wx.FileDialog(self,"Save your desktop session",style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        status=dlg.ShowModal()
        if status==wx.ID_CANCEL:
            logger.debug('saveSession canceled')
            return
        filename=dlg.GetPath()
        q.put(filename)
        # Abuse of queue.get as a flow control mechanism.
        t=threading.Thread(target=self.loginProcess[0].getSharedSession,args=[q])
        t.start()
        t=threading.Thread(target=self.saveSessionThreadTarget,args=[q])
        t.start()

    def checkVersionNumber(self):
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
            newVersionAlertDialog = new_version_alert_dialog.NewVersionAlertDialog(self, wx.ID_ANY, "MASSIVE/CVL Launcher", latestVersionNumber, latestVersionChanges, LAUNCHER_URL)
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

    def buildJobParams(self,window):
        jobParams={}
        for item in window.GetChildren():
            name = item.GetName()
            if ('jobParam' in name):
                (prefix,keyname) = name.split('_') 
                jobParams[keyname]=item.GetValue()
            r = self.buildJobParams(item)
            jobParams.update(r)
        return jobParams

    def onSiteConfigChanged(self,event):
        self.Freeze()
        self.loadPrefs(site=event.GetEventObject().GetValue())
        self.updateVisibility()
        self.Thaw()
        self.configName=self.FindWindowByName('jobParams_configName').GetValue()


    def onAdvancedVisibilityStateChanged(self, event):
        self.updateVisibility()

    def showAll(self,window=None):
        if window==None:
            window=self
        for p in window.GetChildren():
            self.showAll(p)
        window.Show()

    def updateVisibility(self,visible=None):
        #self.showAll()
        advanced=self.FindWindowByName('advancedCheckBox').GetValue()
        if visible==None:
            try:
                visible = self.sites[self.FindWindowByName('jobParams_configName').GetValue()].visibility
            except Exception as e:
                logger.debug('updateVisibility: no visibility information associated with the siteConfig configName: %s'%self.FindWindowByName('jobParams_configName').GetValue())
                visible={}
        for key in visible.keys():
            try:
                window=self.FindWindowByName(key) #Panels and controls are all subclasses of windows
                if visible[key]==False:
                    window.Hide()
                if visible[key]==True:
                    window.Show()
                if visible[key]=='Advanced' and advanced==True:
                    window.Show()
                if visible[key]=='Advanced' and advanced==False:
                    window.Hide()
            except:
                pass # a value in the dictionary didn't correspond to a named component of the panel. Fail silently.
        if self.logWindow != None:
            self.logWindow.Show(self.FindWindowByName('debugCheckBox').GetValue())

    def onDebugWindowCheckBoxStateChanged(self, event):
        if self.logWindow!=None:
            self.logWindow.Show(event.GetEventObject().GetValue())

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
        for lp in self.loginProcess:
            logger.debug("LauncherMainFrame.onExit: calling shutdown on a loginprocess")
            lp.shutdown()
#        for lp in self.loginProcess:
#            while not lp.complete():
#                time.sleep(0.5)

        try:
            logger.dump_log(self)
        finally:
            os._exit(0)


    def onOptions(self, event, tabIndex=0):
        print "in onOptions"

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
        auth_mode=self.launcherOptionsDialog.FindWindowByName(var)
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
            authModeRadioBox = self.launcherOptionsDialog.FindWindowByName('auth_mode')
            authModeRadioBox.SetSelection(int(rv))
            self.identity_menu.setRadio()
            return int(rv)
        else:
            self.queryAuthMode()
    def loginComplete(self,lp,jobParams):
        try:
            self.loginProcess.remove(lp)
        except:
            logger.debug("launcher: Couldn't remove the loginprocess")
    def loginCancel(self,lp,jobParams):
        self.loginProcess.remove(lp)

    def onLoginProcessComplete(self, jobParams):
        logger.debug("launcher.py: onLogin: Enabling login button.")
        self.loginButton.Enable()

    def onLogin(self, event):

        logger.debug("launcher.py: onLogin: Disabling login button.")
        self.loginButton.Disable()

        MASSIVE_TAB_INDEX = 0
        CVL_TAB_INDEX =1
        configName=self.FindWindowByName('jobParams_configName').GetValue()
        if configName=="" or configName==None:
            dlg=LauncherMessageDialog(self,"Please select a site to log into first","Please select a site")
            dlg.ShowModal()
            return
        jobParams={}
        jobParams = self.buildJobParams(self)
        if jobParams['username'] == "":
            dlg = LauncherMessageDialog(self,
                    "Please enter your username.",
                    "MASSIVE/CVL Launcher", flags=wx.OK | wx.ICON_INFORMATION)
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

        dcb=self.FindWindowByName('debugCheckBox').GetValue()
        self.logWindow.Show(self.FindWindowByName('debugCheckBox').GetValue())


        logger.debug("Username: " + jobParams['username'])
        logger.debug("Config: " + configName)

        userCanAbort=True
        maximumProgressBarValue = 10

        try:
            os.mkdir(os.path.join(os.path.expanduser('~'), '.ssh'))
        except:
            logger.debug(traceback.format_exc())
            pass

        # project hours and nodes will be ignored for the CVL login, but they will be used for Massive.
        configName=self.FindWindowByName('jobParams_configName').GetValue()
        if not self.vncOptions.has_key('auth_mode'):
            mode=self.queryAuthMode()
            if mode==wx.ID_CANCEL:
                self.onLoginProcessComplete(None)
                return
            self.vncOptions['auth_mode']=mode
            self.launcherOptionsDialog.FindWindowByName('auth_mode').SetSelection(mode)
            self.identity_menu.disableItems()
            self.saveGlobalOptions()
        jobParams=self.buildJobParams(self)
        jobParams['wallseconds']=int(jobParams['hours'])*60*60
        if self.launcherOptionsDialog.FindWindowByName('auth_mode').GetSelection()==LauncherMainFrame.TEMP_SSH_KEY:
            logger.debug("launcherMainFrame.onLogin: using a temporary Key pair")
            try:
                if 'SSH_AUTH_SOCK' in os.environ:
                    os.environ['PREVIOUS_SSH_AUTH_SOCK'] = os.environ['SSH_AUTH_SOCK']
                del os.environ['SSH_AUTH_SOCK']
                logger.debug("launcherMainFrame.onLogin: spawning an ssh-agent (not using the existing agent)")
            except:
                logger.debug("launcherMainFrame.onLogin: spawning an ssh-agent (no existing agent found)")
                pass
            self.keyModel.setUseTemporaryKey(True)
            removeKeyOnExit = True
        else:
            logger.debug("launcherMainFrame.onLogin: using a permanent Key pair")
            self.keyModel=KeyModel(temporaryKey=False)
        jobParams=self.buildJobParams(self)
        jobParams['wallseconds']=int(jobParams['hours'])*60*60
        self.configName=self.FindWindowByName('jobParams_configName').GetValue()
        autoExit=False
        lp=LoginTasks.LoginProcess(self,jobParams,self.keyModel,siteConfig=self.sites[self.configName],displayStrings=self.sites[self.configName].displayStrings,autoExit=autoExit,vncOptions=self.vncOptions,removeKeyOnExit=self.vncOptions['public_mode'])
        lp.setCallback(lambda jobParams: self.loginComplete(lp,jobParams))
        lp.setCancelCallback(lambda jobParams: self.loginCancel(lp,jobParams))
        self.loginProcess.append(lp)
        lp.doLogin()
        event.Skip()

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

        global launcherPreferencesFilePath 
        launcherPreferencesFilePath = os.path.join(appUserDataDir,"Launcher Preferences.cfg")

        sys.modules[__name__].turboVncConfig = ConfigParser.RawConfigParser(allow_no_value=True)
        turboVncConfig = sys.modules[__name__].turboVncConfig
        sys.modules[__name__].turboVncPreferencesFilePath = os.path.join(appUserDataDir,"TurboVNC Preferences.cfg")
        turboVncPreferencesFilePath = sys.modules[__name__].turboVncPreferencesFilePath
        if os.path.exists(turboVncPreferencesFilePath):
            turboVncConfig.read(turboVncPreferencesFilePath)
        if not turboVncConfig.has_section("TurboVNC Preferences"):
            turboVncConfig.add_section("TurboVNC Preferences")

        if sys.platform.startswith("win"):
            os.environ['CYGWIN'] = "nodosfilewarning"
        sys.modules[__name__].launcherMainFrame = LauncherMainFrame(None, wx.ID_ANY, 'MASSIVE/CVL Launcher')
        launcherMainFrame = sys.modules[__name__].launcherMainFrame
        launcherMainFrame.SetStatusBar(launcherMainFrame.loginDialogStatusBar)
        launcherMainFrame.SetMenuBar(launcherMainFrame.menu_bar)
        launcherMainFrame.Show(True)
        launcherMainFrame.Fit()
        launcherMainFrame.Layout()
        launcherMainFrame.Center()
        def loadPrefsDelayed():
            time.sleep(0.1)
            wx.CallAfter(launcherMainFrame.loadPrefs)
            wx.CallAfter(launcherMainFrame.updateVisibility)
        t=threading.Thread(target=loadPrefsDelayed)
        t.start()

        return True

if __name__ == '__main__':
    app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
    app.MainLoop()
