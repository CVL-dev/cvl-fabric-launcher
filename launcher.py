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
# Enquires: James.Wettenhall@monash.edu or help@massive.org.au

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
import urllib
import launcher_version_number
import xmlrpclib
import appdirs
import ConfigParser
import datetime
#import logging
import shlex
import inspect
import requests
import ssh
from StringIO import StringIO
import logging
import json
import user_management
from os.path import expanduser, join

global transport_logger
global logger
global logger_output
global logger_fh

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

#LAUNCHER_URL = "https://www.massive.org.au/index.php?option=com_content&view=article&id=121"
LAUNCHER_URL = "https://www.massive.org.au/userguide/cluster-instructions/massive-launcher"

# TURBOVNC_BASE_URL = "http://www.virtualgl.org/DeveloperInfo/PreReleases"
TURBOVNC_BASE_URL = "http://sourceforge.net/projects/virtualgl/files/TurboVNC/"

class MyHtmlParser(HTMLParser.HTMLParser):
  def __init__(self, valueString):
    HTMLParser.HTMLParser.__init__(self)
    self.recording = 0
    self.data = []
    self.recordingLatestVersionNumber = 0
    self.latestVersionNumber = "0.0.0"
    self.htmlComments = ""
    self.valueString = valueString

  def handle_starttag(self, tag, attributes):
    if tag != 'span':
      return
    if tag == "span":
        if self.recordingLatestVersionNumber:
          self.recordingLatestVersionNumber += 1
          return
    foundLatestVersionNumberTag = False
    for name, value in attributes:
      if name == 'id' and value == self.valueString:
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

def destroy_dialog(dialog):
    wx.CallAfter(dialog.Hide)
    wx.CallAfter(dialog.Show, False)

    while True:
        try:
            if dialog is None: break

            time.sleep(0.01)
            wx.CallAfter(dialog.Destroy)
            wx.Yield()
        except AttributeError:
            break
        except wx._core.PyDeadObjectError:
            break

def dump_log(submit_log=False):
    logging.shutdown()

    def yes_no():
        dlg = wx.MessageDialog(launcherMainFrame, 'Submit error log to cvl.massive.org.au?', 'Submit log?', wx.YES | wx.NO | wx.ICON_INFORMATION)
        try:
            result = dlg.ShowModal()
            launcherMainFrame.submit_log = result == wx.ID_YES
        finally:
            dlg.Destroy()
            launcherMainFrame.yes_no_completed = True

    launcherMainFrame.yes_no_completed = False

    if submit_log:
        wx.CallAfter(yes_no)
        while not launcherMainFrame.yes_no_completed:
            time.sleep(0.1)

    if submit_log and launcherMainFrame.submit_log:
        logger_debug('about to send debug log')

        url       = 'https://cvl.massive.org.au/cgi-bin/log_drop.py'
        #file_info = {'logfile': launcherMainFrame.logger_output.getvalue()}
        file_info = {'logfile': logger_output.getvalue()}

        # If we are running in an installation then we have to use
        # our packaged cacert.pem file:
        if os.path.exists('cacert.pem'):
            r = requests.post(url, files=file_info, verify='cacert.pem')
        else:
            r = requests.post(url, files=file_info)

    return

def seconds_to_hours_minutes(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return int(h), int(m)

def job_has_been_canceled(ssh_client, job_id):
    """
    When a visnode job is canceled, a file of the form
    $HOME/.vnc/shutdown_${JOB_ID}.${NODE} is created, e.g.
    $HOME/.vnc/shutdown_1234567.m2-m. This function checks if
    a particular shutdown file exists.

    We do minimal error checking because this code is used just as
    the launcher exits.
    """

    try:
        return str(job_id) in run_ssh_command(ssh_client, 'ls ~/.vnc/shutdown_%d*' % (job_id,), ignore_errors=True)[0]
    except:
        return None

def remaining_visnode_walltime():
    """
    Get the remaining walltime for the user's visnode job. We do
    minimal error checking because this code is used just as the user
    is exiting the launcher.
    """

    ssh_client = ssh.SSHClient()
    ssh_client.set_missing_host_key_policy(ssh.AutoAddPolicy())

    try:
        ssh_client.connect(launcherMainFrame.massiveLoginHost, username=launcherMainFrame.massiveUsername, password=launcherMainFrame.massivePassword)
    except:
        return

    stdout, stderr = run_ssh_command(ssh_client, "showq -w class:vis -u " + launcherMainFrame.massiveUsername + " | grep " + launcherMainFrame.massiveUsername, ignore_errors=True)

    try:
        job_id = int(stdout.split()[0])
        if job_has_been_canceled(ssh_client, job_id):
            return
        else: 
            return seconds_to_hours_minutes(float(run_ssh_command(ssh_client, 'qstat -f %d | grep Remaining' % (job_id,), ignore_errors=True)[0].split()[-1]))
    except:
        return

def deleteMassiveJobIfNecessary(write_debug_log=False, update_status_bar=True, update_main_progress_bar=False, ignore_errors=False):
    if launcherMainFrame.loginThread.runningDeleteMassiveJobIfNecessary:
        return

    launcherMainFrame.loginThread.runningDeleteMassiveJobIfNecessary = True
    if launcherMainFrame.massiveTabSelected and launcherMainFrame.massivePersistentMode==False:
        if write_debug_log:
            logger_debug('Possibly running qdel for MASSIVE Vis node...')
        if launcherMainFrame.loginThread.massiveJobNumber != "0" and launcherMainFrame.loginThread.deletedMassiveJob == False:
            if update_status_bar:
                wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Deleting MASSIVE Vis node job.")
            if update_main_progress_bar:
                wx.CallAfter(launcherMainFrame.loginThread.updateProgressDialog, 6, "Deleting MASSIVE Vis node job...")
            if write_debug_log:
                logger_debug("qdel -a " + launcherMainFrame.loginThread.massiveJobNumber)
            run_ssh_command(launcherMainFrame.loginThread.sshClient,
                            "qdel -a " + launcherMainFrame.loginThread.massiveJobNumber, ignore_errors=ignore_errors)
            launcherMainFrame.loginThread.deletedMassiveJob = True
            if update_status_bar:
                wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
    elif launcherMainFrame.massiveTabSelected and launcherMainFrame.massivePersistentMode:
        if write_debug_log:
            logger_debug('Not running qdel for massive visnode because persistent mode is active.')

        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, 'Checking remaining visnode walltime...')
        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_WAIT))

        try:
            remaining_hours, remaining_minutes = remaining_visnode_walltime()
            launcherMainFrame.loginThread.warnedUserAboutNotDeletingJob = False
        except:
            launcherMainFrame.loginThread.warnedUserAboutNotDeletingJob = True

        if not launcherMainFrame.loginThread.warnedUserAboutNotDeletingJob:
            def showNotDeletingMassiveJobWarning():
                launcherMainFrame.loginThread.warnedUserAboutNotDeletingJob = True
                dlg = wx.MessageDialog(launcherMainFrame, "MASSIVE job will not be deleted because persistent mode is active.\n\nRemaining walltime %d hours %d minutes." % (remaining_hours, remaining_minutes,), "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
                launcherMainFrame.loginThread.showNotDeletingMassiveJobWarningCompleted = True
            launcherMainFrame.loginThread.showNotDeletingMassiveJobWarningCompleted = False

            logger_debug('About to run showNotDeletingMassiveJobWarning()')
            wx.CallAfter(showNotDeletingMassiveJobWarning)
            while not launcherMainFrame.loginThread.showNotDeletingMassiveJobWarningCompleted:
                time.sleep(0.1)

            logger_debug('User clicked ok on showNotDeletingMassiveJobWarning()')
    else:
        if write_debug_log:
            logger_debug('Not running qdel for massive visnode.')
    launcherMainFrame.loginThread.runningDeleteMassiveJobIfNecessary = False


def die_from_login_thread(error_message, display_error_dialog=True, submit_log=False):
    if (launcherMainFrame.progressDialog != None):
        wx.CallAfter(launcherMainFrame.progressDialog.Hide)
        wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
        wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
        launcherMainFrame.progressDialog = None

        while True:
            try:
                if launcherMainFrame.progressDialog is None: break

                time.sleep(0.01)
                wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                wx.Yield()
            except AttributeError:
                break
            except wx._core.PyDeadObjectError:
                break

    launcherMainFrame.progressDialog = None
    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
    wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))

    if display_error_dialog:
        def error_dialog():
            dlg = wx.MessageDialog(launcherMainFrame, error_message,
                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            launcherMainFrame.loginThread.die_from_login_thread_completed = True

        launcherMainFrame.loginThread.die_from_login_thread_completed = False
        wx.CallAfter(error_dialog)
        while not launcherMainFrame.loginThread.die_from_login_thread_completed:
            time.sleep(0.1)

    wx.CallAfter(launcherMainFrame.logWindow.Show, False)
    wx.CallAfter(launcherMainFrame.logTextCtrl.Clear)
    wx.CallAfter(launcherMainFrame.massiveShowDebugWindowCheckBox.SetValue, False)
    wx.CallAfter(launcherMainFrame.cvlShowDebugWindowCheckBox.SetValue, False)

    dump_log(submit_log=submit_log)

def die_from_main_frame(error_message):
    if (launcherMainFrame.progressDialog != None):
        wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
        launcherMainFrame.progressDialog = None
    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
    wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))

    def error_dialog():
        dlg = wx.MessageDialog(launcherMainFrame, "Error: " + error_message + "\n\n" + "The launcher cannot continue.\n",
                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
        launcherMainFrame.loginThread.die_from_main_frame_dialog_completed = True

    launcherMainFrame.loginThread.die_from_main_frame_dialog_completed = False
    wx.CallAfter(error_dialog)

    while not launcherMainFrame.loginThread.die_from_main_frame_dialog_completed:
        time.sleep(0.1)

    dump_log(submit_log=True)
    os._exit(1)

def is_managed_session():
    return launcherMainFrame.cvlLoginHostComboBox.GetValue() in cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_vm_ip') and \
           cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_username') == launcherMainFrame.cvlUsername

def run_ssh_command(ssh_client, command, ignore_errors=False, log_output=True):
    logger_debug('run_ssh_command: "%s"' % command)
    logger_debug('   called from %s:%d' % inspect.stack()[1][1:3])

    stdin, stdout, stderr = ssh_client.exec_command(command)
    stdout, stderr = stdout.read(), stderr.read()

    if log_output:
        logger_debug('command stdout: %s' % stdout)
        logger_debug('command stderr: %s' % stderr)

    if not ignore_errors and len(stderr) > 0:
        error_message = 'Error running command: "%s" at line %d' % (command, inspect.stack()[1][2])
        logger_error('Nonempty stderr and ignore_errors == False; exiting the launcher with error dialog: ' + error_message)
        die_from_main_frame(error_message)

    return stdout, stderr

class LauncherMainFrame(wx.Frame):

    def __init__(self, parent, id, title):

        global launcherMainFrame
        launcherMainFrame = self

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

        self.CVL_UM_username            = None
        self.CVL_UM_password            = None
        self.CVL_UM_massive_account     = None
        self.CVL_UM_private_key         = None
        self.CVL_UM_private_key_name    = None
        self.CVL_UM_vm_ip               = None
        self.CVL_UM_private_key_file    = None

        if not cvlLauncherConfig.has_option("CVL Launcher Preferences", 'CVL_UM_server_URL'):
            from user_management import DEFAULT_USER_MANAGEMENT_URL
            cvlLauncherConfig.set("CVL Launcher Preferences", 'CVL_UM_server_URL', DEFAULT_USER_MANAGEMENT_URL)

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.menu_bar  = wx.MenuBar()

        self.file_menu = wx.Menu()
        self.file_menu.Append(wx.ID_ANY, "Forget private key", "Forget private key.")
        self.Bind(wx.EVT_MENU, self.forget_private_key, id=wx.ID_ANY)

        if sys.platform.startswith("win") or sys.platform.startswith("linux"):
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

        if self.massiveLoginHost.startswith("m1"):
            self.massivePersistentMode = True
        else:
            self.massivePersistentMode = False
            if massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
                if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_persistent_mode"):
                    self.massivePersistentMode = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_persistent_mode")
                    if self.massivePersistentMode.strip() == "":
                        self.massivePersistentMode = True
                    else:
                        if self.massivePersistentMode==True or self.massivePersistentMode=='True':
                            self.massivePersistentMode = True
                        else:
                            self.massivePersistentMode = False
                else:
                    massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_persistent_mode","False")
                    with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                        massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
            else:
                massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        self.massivePersistentModeLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Persistent mode')
        self.massiveLoginFieldsPanelSizer.Add(self.massivePersistentModeLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.massivePersistentModeCheckBox = wx.CheckBox(self.massiveLoginFieldsPanel, wx.ID_ANY, "")
        self.massivePersistentModeCheckBox.SetValue(self.massivePersistentMode)
        self.massiveLoginFieldsPanelSizer.Add(self.massivePersistentModeCheckBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

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

        self.massiveShowDebugWindowLabel = wx.StaticText(self.massiveLoginFieldsPanel, wx.ID_ANY, 'Show debug window')
        self.massiveLoginFieldsPanelSizer.Add(self.massiveShowDebugWindowLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.massiveShowDebugWindowCheckBox = wx.CheckBox(self.massiveLoginFieldsPanel, wx.ID_ANY, "")
        self.massiveShowDebugWindowCheckBox.SetValue(False)
        self.massiveShowDebugWindowCheckBox.Bind(wx.EVT_CHECKBOX, self.onMassiveDebugWindowCheckBoxStateChanged)
        self.massiveLoginFieldsPanelSizer.Add(self.massiveShowDebugWindowCheckBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

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
        self.cvlUserVMLatestLookup = None
        self.cvlUserVMList         = None

        self.cvlLoginFieldsPanelSizer.Add(self.cvlUsernameTextField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=8)
        if self.cvlUsername.strip()!="":
            self.cvlUsernameTextField.SelectAll()

        self.cvlPasswordLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Password')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlPasswordLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlPassword = ""
        self.cvlPasswordField = wx.TextCtrl(self.cvlLoginFieldsPanel, wx.ID_ANY, self.cvlPassword, size=(widgetWidth1, -1), style=wx.TE_PASSWORD)
        self.cvlLoginFieldsPanelSizer.Add(self.cvlPasswordField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=8)



        self.cvlLoginHostLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Host')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlLoginHostLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlLoginHost = ""
        #self.cvlLoginHosts = ["115.146.93.128","115.146.94.0"]
        self.cvlLoginHosts = []
        #self.defaultCvlHost = "115.146.93.128"
        self.defaultCvlHost = ""
        self.cvlLoginHostComboBox = wx.ComboBox(self.cvlLoginFieldsPanel, wx.ID_ANY, value=self.defaultCvlHost, choices=self.cvlLoginHosts, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN)

        self.cvlLoginHostComboBox.Bind(wx.EVT_MOUSE_EVENTS, self.onCvlLoginHostComboClick)
        self.cvlLoginHostComboBox.Bind(wx.EVT_SET_FOCUS,    self.onCvlLoginHostComboClick)

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
        self.cvlLoginHost = self.cvlLoginHost.strip()
        if self.cvlLoginHost!="":
            if self.cvlLoginHost in self.cvlLoginHosts:
                self.cvlLoginHostComboBox.SetSelection(self.cvlLoginHosts.index(self.cvlLoginHost))
            else:
                # Hostname was not found in combo-box.
                self.cvlLoginHostComboBox.SetSelection(-1)
            self.cvlLoginHostComboBox.SetValue(self.cvlLoginHost)

            # Add the user's managed VM IPs if available.
            if cvlLauncherConfig.has_option("CVL Launcher Preferences", 'CVL_UM_vm_ip'):
                try:
                    # Might fail if user has old-format preferences data.
                    #self.cvlLoginHostComboBox.SetItems(self.cvlLoginHosts + eval(cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_vm_ip')))
                    self.cvlLoginHostComboBox.SetItems(eval(cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_vm_ip')))
                except:
                    try:
                        #self.cvlLoginHostComboBox.SetItems(self.cvlLoginHosts + [cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_vm_ip')])
                        self.cvlLoginHostComboBox.SetItems([cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_vm_ip')])
                    except:
                        self.cvlLoginHostComboBox.SetItems(self.cvlLoginHosts)

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

        if self.cvlVncDisplayNumberAutomatic==False:
            self.cvlVncDisplayResolutionComboBox.Disable()
            self.cvlVncDisplayResolutionLabel.Disable()

        self.cvlSshTunnelCipherLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'SSH tunnel cipher')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlSshTunnelCipherLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        defaultCipher = ""
        self.cvlSshTunnelCipher = ""
        cvlSshTunnelCiphers = [""]
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

        self.cvlPasswordField.MoveAfterInTabOrder(self.cvlUsernameTextField)
        self.cvlLoginHostComboBox.MoveAfterInTabOrder(self.cvlPasswordField)
        self.cvlVncDisplayNumberPanel.MoveAfterInTabOrder(self.cvlLoginHostComboBox)
        self.cvlVncDisplayResolutionComboBox.MoveAfterInTabOrder(self.cvlVncDisplayNumberPanel)
        self.cvlSshTunnelCipherComboBox.MoveAfterInTabOrder(self.cvlVncDisplayResolutionComboBox)

        self.cvlShowDebugWindowLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Show debug window')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlShowDebugWindowLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.cvlShowDebugWindowCheckBox = wx.CheckBox(self.cvlLoginFieldsPanel, wx.ID_ANY, "")
        self.cvlShowDebugWindowCheckBox.SetValue(False)
        self.cvlShowDebugWindowCheckBox.Bind(wx.EVT_CHECKBOX, self.onCvlDebugWindowCheckBoxStateChanged)
        self.cvlLoginFieldsPanelSizer.Add(self.cvlShowDebugWindowCheckBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlSpacerLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, '')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlSpacerLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.cvlSpacerLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, '')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlSpacerLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlShowAdvancedOptionsLabel = wx.StaticText(self.cvlLoginFieldsPanel, wx.ID_ANY, 'Show advanced options')
        self.cvlLoginFieldsPanelSizer.Add(self.cvlShowAdvancedOptionsLabel, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.cvlShowAdvancedOptions = False
        if cvlLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if cvlLauncherConfig.has_option("MASSIVE Launcher Preferences", "cvl_show_advanced_options"):
                self.cvlShowAdvancedOptions = cvlLauncherConfig.get("MASSIVE Launcher Preferences", "cvl_show_advanced_options")
                if self.cvlShowAdvancedOptions.strip() == "":
                    self.cvlShowAdvancedOptions = False
                else:
                    if self.cvlShowAdvancedOptions==True or self.cvlShowAdvancedOptions=='True':
                        self.cvlShowAdvancedOptions = True
                    else:
                        self.cvlShowAdvancedOptions = False
            else:
                cvlLauncherConfig.set("MASSIVE Launcher Preferences", "cvl_show_advanced_options","False")
                with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                    cvlLauncherConfig.write(massiveLauncherPreferencesFileObject)
        else:
            cvlLauncherConfig.add_section("MASSIVE Launcher Preferences")
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                cvlLauncherConfig.write(massiveLauncherPreferencesFileObject)
        self.cvlShowAdvancedOptionsCheckBox = wx.CheckBox(self.cvlLoginFieldsPanel, wx.ID_ANY, "")
        self.cvlShowAdvancedOptionsCheckBox.SetValue(self.cvlShowAdvancedOptions)
        self.cvlShowAdvancedOptionsCheckBox.Bind(wx.EVT_CHECKBOX, self.onCvlAdvancedOptionsCheckBoxStateChanged)
        self.cvlLoginFieldsPanelSizer.Add(self.cvlShowAdvancedOptionsCheckBox, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)

        self.cvlLoginFieldsPanel.SetSizerAndFit(self.cvlLoginFieldsPanelSizer)

        self.cvlLoginDialogPanelSizer.Add(self.cvlLoginFieldsPanel, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=15)

        self.cvlLoginDialogPanel.SetSizerAndFit(self.cvlLoginDialogPanelSizer)
        self.cvlLoginDialogPanel.Layout()

        self.onCvlAdvancedOptionsCheckBoxStateChanged(event=None)

        # End CVL tab

        self.loginDialogPanelSizer.Add(self.tabbedView, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=10)

        CVL_TAB_INDEX = 1
        self.tabbedView.ChangeSelection(CVL_TAB_INDEX)
        self.massiveTabSelected = False
        self.cvlTabSelected = True

        # Buttons Panel

        self.buttonsPanel = wx.Panel(self.loginDialogPanel, wx.ID_ANY)

        self.buttonsPanelSizer = wx.FlexGridSizer(rows=1, cols=4, vgap=5, hgap=10)
        self.buttonsPanel.SetSizer(self.buttonsPanelSizer)

        IDENTITY_SETUP_BUTTON_ID = 4
        self.identityButton = wx.Button(self.buttonsPanel, IDENTITY_SETUP_BUTTON_ID, 'Identity...')
        self.buttonsPanelSizer.Add(self.identityButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.setup_identity, id=IDENTITY_SETUP_BUTTON_ID)

        OPTIONS_BUTTON_ID = 1
        self.optionsButton = wx.Button(self.buttonsPanel, OPTIONS_BUTTON_ID, 'Options...')
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

        # Moved logger definitions to earlier in the code,
        # before the first call to dump_log()

        global transport_logger
        global logger
        global logger_debug
        global logger_error
        global logger_warning
        global logger_output
        global logger_fh

        transport_logger = logging.getLogger('ssh.transport')
        transport_logger.setLevel(logging.DEBUG)

        logger = logging.getLogger('launcher')
        logger.setLevel(logging.DEBUG)
        def logger_debug(message):
            wx.CallAfter(logger.debug, message)
        def logger_error(message):
            wx.CallAfter(logger.error, message)
        def logger_warning(message):
            wx.CallAfter(logger.warning, message)

        log_format_string = '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'

        # Send all log messages to a string.
        logger_output = StringIO()
        string_handler = logging.StreamHandler(stream=logger_output)
        string_handler.setLevel(logging.DEBUG)
        string_handler.setFormatter(logging.Formatter(log_format_string))
        logger.addHandler(string_handler)
        transport_logger.addHandler(string_handler)

        # Finally, send all log messages to a log file.
        logger_fh = logging.FileHandler(join(expanduser("~"), '.MASSIVE_Launcher_debug_log.txt'))
        logger_fh.setLevel(logging.DEBUG)
        logger_fh.setFormatter(logging.Formatter(log_format_string))
        logger.addHandler(logger_fh)
        transport_logger.addHandler(logger_fh)

        # Check for the latest version of the launcher:
        try:
            myHtmlParser = MyHtmlParser('MassiveLauncherLatestVersionNumber')
            feed = urllib.urlopen(LAUNCHER_URL)
            html = feed.read()
            myHtmlParser.feed(html)
            myHtmlParser.close()
        except:
            dlg = wx.MessageDialog(self, "Error: Unable to contact MASSIVE website to check version number.\n\n" +
                                        "The launcher cannot continue.\n",
                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            # If we can't contact the MASSIVE website, it's probably because
            # there's no active network connection, so don't try to submit
            # the log to cvl.massive.org.au
            dump_log(submit_log=False)
            sys.exit(1)

        latestVersionNumber = myHtmlParser.latestVersionNumber
        htmlComments = myHtmlParser.htmlComments
        htmlCommentsSplit1 = htmlComments.split("<pre id=\"CHANGES\">")
        htmlCommentsSplit2 = htmlCommentsSplit1[1].split("</pre>")
        latestVersionChanges = htmlCommentsSplit2[0].strip()

        if latestVersionNumber!=launcher_version_number.version_number:
            import new_version_alert_dialog
            newVersionAlertDialog = new_version_alert_dialog.NewVersionAlertDialog(launcherMainFrame, wx.ID_ANY, "MASSIVE/CVL Launcher", latestVersionNumber, latestVersionChanges, LAUNCHER_URL)
            newVersionAlertDialog.ShowModal()

            # Tried submit_log=True, but it didn't work.
            # Maybe the requests stuff hasn't been initialized yet.
            logger_debug("Failed version number check.")
            dump_log(submit_log=False)
            sys.exit(1)

    def onMassiveLoginHostNameChanged(self, event):
        event.Skip()
        selectedMassiveLoginHost = self.massiveLoginHostComboBox.GetValue()
        if selectedMassiveLoginHost.startswith("m1"):
            self.massivePersistentModeCheckBox.SetValue(True)
        #if selectedMassiveLoginHost.startswith("m2"):
            #self.massivePersistentModeCheckBox.SetValue(False)

    def onMassiveDebugWindowCheckBoxStateChanged(self, event):
        if launcherMainFrame.logWindow!=None:
            if launcherMainFrame.massiveTabSelected:
                launcherMainFrame.logWindow.Show(self.massiveShowDebugWindowCheckBox.GetValue())

    def onCvlDebugWindowCheckBoxStateChanged(self, event):
        if launcherMainFrame.logWindow!=None:
            if launcherMainFrame.cvlTabSelected:
                launcherMainFrame.logWindow.Show(self.cvlShowDebugWindowCheckBox.GetValue())

    def onCvlAdvancedOptionsCheckBoxStateChanged(self, event):
        if launcherMainFrame.cvlShowAdvancedOptionsCheckBox.GetValue()==True:
            launcherMainFrame.cvlLoginHostLabel.Show()
            launcherMainFrame.cvlLoginHostComboBox.Show()
            launcherMainFrame.cvlVncDisplayNumberLabel.Show()
            launcherMainFrame.cvlVncDisplayNumberAutomaticCheckBox.Show()
            launcherMainFrame.cvlVncDisplayNumberSpinCtrl.Show()
            launcherMainFrame.cvlVncDisplayResolutionLabel.Show()
            launcherMainFrame.cvlVncDisplayResolutionComboBox.Show()
            launcherMainFrame.cvlSshTunnelCipherLabel.Show()
            launcherMainFrame.cvlSshTunnelCipherComboBox.Show()
            launcherMainFrame.cvlShowDebugWindowLabel.Show()
            launcherMainFrame.cvlShowDebugWindowCheckBox.Show()
        else:
            launcherMainFrame.cvlLoginHostLabel.Hide()
            launcherMainFrame.cvlLoginHostComboBox.Hide()
            launcherMainFrame.cvlVncDisplayNumberLabel.Hide()
            launcherMainFrame.cvlVncDisplayNumberAutomaticCheckBox.Hide()
            launcherMainFrame.cvlVncDisplayNumberSpinCtrl.Hide()
            launcherMainFrame.cvlVncDisplayResolutionLabel.Hide()
            launcherMainFrame.cvlVncDisplayResolutionComboBox.Hide()
            launcherMainFrame.cvlSshTunnelCipherLabel.Hide()
            launcherMainFrame.cvlSshTunnelCipherComboBox.Hide()
            launcherMainFrame.cvlShowDebugWindowLabel.Hide()
            launcherMainFrame.cvlShowDebugWindowCheckBox.Hide()

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

    def onAbout(self, event):
        import commit_def
        dlg = wx.MessageDialog(self, "Version " + launcher_version_number.version_number + "\n"
                                   + 'Commit: ' + commit_def.LATEST_COMMIT + '\n',
                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onExit(self, event):
        dump_log()
        self.onCancel(event)

    def forget_private_key(self, event):
        if cvlLauncherConfig.has_option("CVL Launcher Preferences", 'CVL_UM_private_key_name'):
            try:
                os.unlink(join(expanduser("~"), '.MASSIVE_keys', cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_private_key_name')))

                dlg = wx.MessageDialog(launcherMainFrame, 'Removed the private key.', "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
            except:
                dlg = wx.MessageDialog(launcherMainFrame, 'Error removing the private key.', "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
        else:
            dlg = wx.MessageDialog(launcherMainFrame, 'You don\'t have a private key. Nothing to do.', "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()

        cvlLauncherConfig.remove_option("CVL Launcher Preferences", 'CVL_UM_username')
        cvlLauncherConfig.remove_option("CVL Launcher Preferences", 'CVL_UM_massive_account')
        cvlLauncherConfig.remove_option("CVL Launcher Preferences", 'CVL_UM_private_key_name')
        cvlLauncherConfig.remove_option("CVL Launcher Preferences", 'CVL_UM_vm_ip')
        cvlLauncherConfig.remove_option("CVL Launcher Preferences", 'CVL_UM_vnc_password')
        with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
            cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)

    def setup_identity(self, event):
        self.CVL_UM_username = self.cvlUsernameTextField.GetValue().lstrip().rstrip()
        self.CVL_UM_password = self.cvlPasswordField.GetValue()

        if self.CVL_UM_username == '':
            dlg = wx.MessageDialog(launcherMainFrame, 'Please enter your CVL username.', "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return

        if self.CVL_UM_password == '':
            dlg = wx.MessageDialog(launcherMainFrame, 'Please enter your CVL password.', "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return

        try:
            payload = user_management.get_key(cvlLauncherConfig, self.CVL_UM_username, self.CVL_UM_password)
        except:
            logger_debug("Error from key_key()")
            logger_debug(traceback.format_exc())

            dlg = wx.MessageDialog(launcherMainFrame, 'Error contacting CVL user management system', "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return

        try:
            self.CVL_UM_massive_account  = payload['massive_account']
            self.CVL_UM_private_key      = payload['private_key']
            self.CVL_UM_private_key_name = payload['private_key_name']
            self.CVL_UM_vm_ip            = payload['vm_ip']
        except:
            dlg = wx.MessageDialog(launcherMainFrame, 'Error parsing CVL user info', "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return

        os.system('mkdir -p ' + join(expanduser("~"), '.MASSIVE_keys'))
        f = open(join(expanduser("~"), '.MASSIVE_keys', self.CVL_UM_private_key_name), 'w')
        f.write(self.CVL_UM_private_key)
        f.close()

        """
        # FIXME this will not be needed because we do passwordless VNC login with TurboVNC?

        try:
            self.CVL_UM_vnc_password  = user_management.set_vnc_password(self.CVL_UM_vm_ip, self.CVL_UM_username, join(expanduser("~"), '.MASSIVE_keys', self.CVL_UM_private_key_name))
        except:
            dlg = wx.MessageDialog(launcherMainFrame, 'Could not set VNC password on host %s for user %s' % (self.CVL_UM_vm_ip, self.CVL_UM_username,), "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            return
        """

        if len(self.CVL_UM_vm_ip) == 0:
            dlg = wx.MessageDialog(launcherMainFrame, 'Warning: CVL VM list is empty!', "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()

        #self.cvlLoginHostComboBox.SetItems(self.cvlLoginHosts + self.CVL_UM_vm_ip)
        self.cvlLoginHostComboBox.SetItems(self.CVL_UM_vm_ip)
        #self.cvlLoginHostComboBox.SetValue((self.CVL_UM_vm_ip + self.cvlLoginHosts + [''])[0]) # If no VM IPs available, use the first default, or the empty string.
        self.cvlLoginHostComboBox.SetValue((self.CVL_UM_vm_ip + [''])[0]) # If no VM IPs available, use the first default, or the empty string.

        cvlLauncherConfig.set("CVL Launcher Preferences", 'CVL_UM_username',            self.CVL_UM_username)
        cvlLauncherConfig.set("CVL Launcher Preferences", 'CVL_UM_massive_account',     self.CVL_UM_massive_account)
        cvlLauncherConfig.set("CVL Launcher Preferences", 'CVL_UM_private_key_name',    self.CVL_UM_private_key_name)
        cvlLauncherConfig.set("CVL Launcher Preferences", 'CVL_UM_vm_ip',               self.CVL_UM_vm_ip)
        # cvlLauncherConfig.set("CVL Launcher Preferences", 'CVL_UM_vnc_password',        self.CVL_UM_vnc_password)
        with open(cvlLauncherPreferencesFilePath, 'wb') as cvlLauncherPreferencesFileObject:
            cvlLauncherConfig.write(cvlLauncherPreferencesFileObject)

    def onToggleCvlVncDisplayNumberAutomaticCheckBox(self, event):
        if self.cvlVncDisplayNumberAutomaticCheckBox.GetValue()==True:
            self.cvlVncDisplayNumberSpinCtrl.Disable()
            self.cvlVncDisplayResolutionComboBox.Enable()
            self.cvlVncDisplayResolutionLabel.Enable()
        else:
            self.cvlVncDisplayNumberSpinCtrl.Enable()
            self.cvlVncDisplayResolutionComboBox.Disable()
            self.cvlVncDisplayResolutionLabel.Disable()

    def onCvlLoginHostComboClick(self, event):
        event.Skip()

        # Not sure how to deal with the UI at the moment, so disabling this.
        # User will have to click the Identity button to get things going.
        """
        username = self.cvlUsernameTextField.GetValue()

        do_lookup = False

        if self.cvlUserVMLatestLookup is None:
            do_lookup = True
            self.cvlUserVMLatestLookup = username

        if do_lookup or username != self.cvlUserVMLatestLookup:
            self.cvlUserVMLatestLookup = username

            if os.path.exists('cacert.pem'):
                r = requests.post('https://cvl.massive.org.au/usermanagement/query.php', {'queryMessage': 'username="%s"' % self.cvlUsernameTextField.GetValue(), 'query': 'Send to user management'}, verify='cacert.pem')
            else:
                r = requests.post('https://cvl.massive.org.au/usermanagement/query.php', {'queryMessage': 'username="%s"' % self.cvlUsernameTextField.GetValue(), 'query': 'Send to user management'})

            print r.text

            if r.ok and not 'error' in r.text:
                self.cvlUserVMList = json.loads(r.text)['VM_IPs']
                new_host_list = self.cvlLoginHostComboBox.GetItems() + [x for x in self.cvlUserVMList if x not in self.cvlLoginHostComboBox.GetItems()]
                self.cvlLoginHostComboBox.SetItems(new_host_list)
            else:
                self.cvlLoginHostComboBox.SetItems(self.cvlLoginHosts)
        """

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

        launcherOptionsDialog = optionsDialog.LauncherOptionsDialog(launcherMainFrame, wx.ID_ANY, "MASSIVE/CVL Launcher Options", self.vncOptions, cvlLauncherConfig, cvlLauncherPreferencesFilePath)
        launcherOptionsDialog.ShowModal()

        if launcherOptionsDialog.okClicked:
            self.vncOptions = launcherOptionsDialog.getVncOptions()

            for key in self.vncOptions:
                turboVncConfig.set("TurboVNC Preferences", key, self.vncOptions[key])

            with open(turboVncPreferencesFilePath, 'wb') as turboVncPreferencesFileObject:
                turboVncConfig.write(turboVncPreferencesFileObject)

    def onCancel(self, event):
        try:
            try:
                if os.path.isfile(launcherMainFrame.loginThread.privateKeyFile.name):
                    os.unlink(launcherMainFrame.loginThread.privateKeyFile.name)
            except:
                #logger_debug("MASSIVE/CVL Launcher v" + launcher_version_number.version_number)
                #logger_debug(traceback.format_exc())
                pass

            # Now using ignore_errors=True, because of CVLFAB-449
            deleteMassiveJobIfNecessary(write_debug_log=False,update_status_bar=True,update_main_progress_bar=False,ignore_errors=True)

            launcherMainFrame.loginThread.sshClient.close()

        except:
            #logger_debug("MASSIVE/CVL Launcher v" + launcher_version_number.version_number)
            #logger_debug(traceback.format_exc())
            pass

        finally:
            dump_log()
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

        if self.progressDialog!=None:
            self.progressDialog.SetCursor(cursor)

        super(LauncherMainFrame, self).SetCursor(cursor)

    def onLogin(self, event):
        class LoginThread(threading.Thread):
            """Login Thread Class."""
            def __init__(self, notify_window):
                """Init Worker Thread Class."""
                threading.Thread.__init__(self)
                self._notify_window = notify_window

            def updateProgressDialog(self, value, message):
                self.updatingProgressDialog = True
                if launcherMainFrame.progressDialog!=None:
                    launcherMainFrame.progressDialog.Update(value, message)
                    self.shouldAbort = launcherMainFrame.progressDialog.shouldAbort()
                self.updatingProgressDialog = False

            def run(self):
                """Run Worker Thread."""

                try:

                    self.runningDeleteMassiveJobIfNecessary = False

                    wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_WAIT))

                    wx.CallAfter(launcherMainFrame.logTextCtrl.Clear)

                    MASSIVE_TAB_INDEX = 0
                    CVL_TAB_INDEX =1

                    if launcherMainFrame.tabbedView.GetSelection()==MASSIVE_TAB_INDEX:
                        launcherMainFrame.massiveTabSelected = True
                        launcherMainFrame.cvlTabSelected = False

                    if launcherMainFrame.tabbedView.GetSelection()==CVL_TAB_INDEX:
                        launcherMainFrame.massiveTabSelected = False
                        launcherMainFrame.cvlTabSelected = True

                    import launcher_progress_dialog
                    maximumProgressBarValue = 10
                    userCanAbort = True
                    if launcherMainFrame.massiveTabSelected:
                        def initializeProgressDialog():
                            launcherMainFrame.progressDialog = launcher_progress_dialog.LauncherProgressDialog(launcherMainFrame, wx.ID_ANY, "Connecting to MASSIVE...", "Checking installed version of TurboVNC...", maximumProgressBarValue, userCanAbort)
                    else:
                        def initializeProgressDialog():
                            launcherMainFrame.progressDialog = launcher_progress_dialog.LauncherProgressDialog(launcherMainFrame, wx.ID_ANY, "Connecting to CVL...", "Checking installed version of TurboVNC...", maximumProgressBarValue, userCanAbort)

                    wx.CallAfter(initializeProgressDialog)
                    self.shouldAbort = False

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

                    self.host       = self.host.lstrip().rstrip()
                    self.resolution = self.resolution.lstrip().rstrip()
                    self.cipher     = self.cipher.lstrip().rstrip()
                    self.username   = self.username.lstrip().rstrip()

                    logger_debug('host: ' + self.host)
                    logger_debug('resolution: ' + self.resolution)
                    logger_debug('cipher: ' + self.cipher)
                    logger_debug('username: ' + self.username)
                    logger_debug('sys.platform: ' + sys.platform)

                    logger_debug('host: ' + self.host)
                    logger_debug('resolution: ' + self.resolution)
                    logger_debug('cipher: ' + self.cipher)
                    logger_debug('username: ' + self.username)
                    logger_debug('sys.platform: ' + sys.platform)

                    import platform

                    logger_debug('platform.architecture: '  + str(platform.architecture()))
                    logger_debug('platform.machine: '       + str(platform.machine()))
                    logger_debug('platform.node: '          + str(platform.node()))
                    logger_debug('platform.platform: '      + str(platform.platform()))
                    logger_debug('platform.processor: '     + str(platform.processor()))
                    logger_debug('platform.release: '       + str(platform.release()))
                    logger_debug('platform.system: '        + str(platform.system()))
                    logger_debug('platform.version: '       + str(platform.version()))
                    logger_debug('platform.uname: '         + str(platform.uname()))

                    if sys.platform.startswith("win"):
                        logger_debug('platform.win32_ver: ' + str(platform.win32_ver()))

                    if sys.platform.startswith("darwin"):
                        logger_debug('platform.mac_ver: ' + str(platform.mac_ver()))

                    if sys.platform.startswith("linux"):
                        logger_debug('platform.linux_distribution: ' + str(platform.linux_distribution()))
                        logger_debug('platform.libc_ver: ' + str(platform.libc_ver()))

                    # Check for TurboVNC

                    # Check for the latest version of TurboVNC on the launcher web page:
                    try:
                        myHtmlParser = MyHtmlParser('TurboVncLatestVersionNumber')
                        feed = urllib.urlopen(LAUNCHER_URL)
                        html = feed.read()
                        myHtmlParser.feed(html)
                        myHtmlParser.close()
                    except:
                        logger_debug("Exception while checking TurboVNC version number.")

                        def error_dialog():
                            dlg = wx.MessageDialog(self, "Error: Unable to contact MASSIVE website to check the TurboVNC version number.\n\n" +
                                                    "The launcher cannot continue.\n",
                                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                            dlg.ShowModal()
                            dlg.Destroy()
                            # If we can't contact the MASSIVE website, it's probably because
                            # there's no active network connection, so don't try to submit
                            # the log to cvl.massive.org.au
                            dump_log(submit_log=False)
                            sys.exit(1)
                        wx.CallAfter(error_dialog)

                    turboVncLatestVersion = myHtmlParser.latestVersionNumber

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
                                launcherMainFrame.loginThread.turboVncVersionNumber = queryResult[0]
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
                                launcherMainFrame.loginThread.turboVncVersionNumber = queryResult[0]
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
                                launcherMainFrame.loginThread.turboVncVersionNumber = queryResult[0]
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
                                launcherMainFrame.loginThread.turboVncVersionNumber = queryResult[0]
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
                                launcherMainFrame.loginThread.turboVncVersionNumber = queryResult[0]
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
                                launcherMainFrame.loginThread.turboVncVersionNumber = queryResult[0]
                                foundTurboVncInRegistry = True
                            except:
                                foundTurboVncInRegistry = False
                                #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                                #wx.CallAfter(sys.stdout.write, traceback.format_exc())

                    if os.path.exists(vnc):
                        logger_debug("TurboVNC was found in " + vnc)
                        #if sys.platform.startswith("darwin"):
                            ## Need to determine whether we have the X11 version of TurboVNC or the Java version.

                    else:
                        def showTurboVncNotFoundMessageDialog():
                            turboVncNotFoundDialog = wx.Dialog(launcherMainFrame, title="MASSIVE/CVL Launcher", name="MASSIVE/CVL Launcher",pos=(200,150),size=(680,290))

                            if sys.platform.startswith("win"):
                                _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
                                turboVncNotFoundDialog.SetIcon(_icon)

                            if sys.platform.startswith("linux"):
                                import MASSIVE_icon
                                turboVncNotFoundDialog.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

                            massiveIconPanel = wx.Panel(turboVncNotFoundDialog)

                            import MASSIVE_icon
                            massiveIconAsBitmap = MASSIVE_icon.getMASSIVElogoTransparent128x128Bitmap()
                            wx.StaticBitmap(massiveIconPanel, wx.ID_ANY,
                                massiveIconAsBitmap,
                                (0, 50),
                                (massiveIconAsBitmap.GetWidth(), massiveIconAsBitmap.GetHeight()))

                            turboVncNotFoundPanel = wx.Panel(turboVncNotFoundDialog)

                            turboVncNotFoundPanelSizer = wx.FlexGridSizer(rows=8, cols=1, vgap=5, hgap=5)
                            turboVncNotFoundPanel.SetSizer(turboVncNotFoundPanelSizer)

                            turboVncNotFoundTitleLabel = wx.StaticText(turboVncNotFoundPanel,
                                label = "MASSIVE/CVL Launcher")
                            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                            font.SetPointSize(14)
                            font.SetWeight(wx.BOLD)
                            turboVncNotFoundTitleLabel.SetFont(font)
                            turboVncNotFoundPanelSizer.Add(wx.StaticText(turboVncNotFoundPanel))
                            turboVncNotFoundPanelSizer.Add(turboVncNotFoundTitleLabel, flag=wx.EXPAND)
                            turboVncNotFoundPanelSizer.Add(wx.StaticText(turboVncNotFoundPanel))

                            turboVncNotFoundTextLabel1 = wx.StaticText(turboVncNotFoundPanel,
                                label = "TurboVNC not found.\n" +
                                        "Please download from:\n")
                            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                            if sys.platform.startswith("darwin"):
                                font.SetPointSize(11)
                            else:
                                font.SetPointSize(9)
                            turboVncNotFoundTextLabel1.SetFont(font)
                            turboVncNotFoundPanelSizer.Add(turboVncNotFoundTextLabel1, flag=wx.EXPAND)

                            turboVncNotFoundHyperlink = wx.HyperlinkCtrl(turboVncNotFoundPanel,
                                id = wx.ID_ANY,
                                label = TURBOVNC_BASE_URL + turboVncLatestVersion,
                                url = TURBOVNC_BASE_URL + turboVncLatestVersion)
                            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                            if sys.platform.startswith("darwin"):
                                font.SetPointSize(11)
                            else:
                                font.SetPointSize(8)
                            turboVncNotFoundHyperlink.SetFont(font)
                            turboVncNotFoundPanelSizer.Add(turboVncNotFoundHyperlink, border=10, flag=wx.LEFT|wx.BORDER)
                            turboVncNotFoundPanelSizer.Add(wx.StaticText(turboVncNotFoundPanel))

                            turboVncNotFoundPanelSizer.Add(wx.StaticText(turboVncNotFoundPanel, wx.ID_ANY, ""))
                            turboVncNotFoundQueriesContactLabel = wx.StaticText(turboVncNotFoundPanel,
                                label = "For queries, please contact:")
                            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                            if sys.platform.startswith("darwin"):
                                font.SetPointSize(11)
                            else:
                                font.SetPointSize(9)
                            turboVncNotFoundQueriesContactLabel.SetFont(font)
                            turboVncNotFoundPanelSizer.Add(turboVncNotFoundQueriesContactLabel, border=10, flag=wx.EXPAND|wx.BORDER)

                            contactEmailHyperlink = wx.HyperlinkCtrl(turboVncNotFoundPanel,
                                id = wx.ID_ANY,
                                label = "help@massive.org.au",
                                url = "mailto:help@massive.org.au")
                            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                            if sys.platform.startswith("darwin"):
                                font.SetPointSize(11)
                            else:
                                font.SetPointSize(8)
                            contactEmailHyperlink.SetFont(font)
                            turboVncNotFoundPanelSizer.Add(contactEmailHyperlink, border=20, flag=wx.LEFT|wx.BORDER)

                            contactEmail2Hyperlink = wx.HyperlinkCtrl(turboVncNotFoundPanel,
                                id = wx.ID_ANY,
                                label = "James.Wettenhall@monash.edu",
                                url = "mailto:James.Wettenhall@monash.edu")
                            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                            if sys.platform.startswith("darwin"):
                                font.SetPointSize(11)
                            else:
                                font.SetPointSize(8)
                            contactEmail2Hyperlink.SetFont(font)
                            turboVncNotFoundPanelSizer.Add(contactEmail2Hyperlink, border=20, flag=wx.LEFT|wx.BORDER)

                            def onOK(event):
                                launcherMainFrame.loginThread.showTurboVncNotFoundMessageDialogCompleted = True
                                turboVncNotFoundDialog.Show(False)

                            okButton = wx.Button(turboVncNotFoundPanel, 1, ' OK ')
                            okButton.SetDefault()
                            turboVncNotFoundPanelSizer.Add(okButton, flag=wx.ALIGN_RIGHT)
                            turboVncNotFoundPanelSizer.Add(wx.StaticText(turboVncNotFoundPanel))
                            turboVncNotFoundPanelSizer.Fit(turboVncNotFoundPanel)

                            turboVncNotFoundDialog.Bind(wx.EVT_BUTTON, onOK, id=1)

                            turboVncNotFoundDialogSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=5, hgap=5)
                            turboVncNotFoundDialogSizer.Add(massiveIconPanel, flag=wx.EXPAND)
                            turboVncNotFoundDialogSizer.Add(turboVncNotFoundPanel, flag=wx.EXPAND)
                            turboVncNotFoundDialogSizer.Add(wx.StaticText(turboVncNotFoundDialog,label="       "))
                            turboVncNotFoundDialog.SetSizer(turboVncNotFoundDialogSizer)
                            turboVncNotFoundDialogSizer.Fit(turboVncNotFoundDialog)

                            turboVncNotFoundDialog.ShowModal()
                            turboVncNotFoundDialog.Destroy()

                        if (launcherMainFrame.progressDialog != None):
                            wx.CallAfter(launcherMainFrame.progressDialog.Hide)
                            wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                            wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                            launcherMainFrame.progressDialog = None
                        launcherMainFrame.loginThread.showTurboVncNotFoundMessageDialogCompleted = False
                        wx.CallAfter(showTurboVncNotFoundMessageDialog)
                        while launcherMainFrame.loginThread.showTurboVncNotFoundMessageDialogCompleted == False:
                            time.sleep(0.1)

                        try:
                            if os.path.isfile(launcherMainFrame.loginThread.privateKeyFile.name):
                                os.unlink(self.privateKeyFile.name)
                            launcherMainFrame.loginThread.sshTunnelProcess.terminate()
                            self.sshClient.close()
                        finally:
                            dump_log(submit_log=True)
                            os._exit(1)

                    if not sys.platform.startswith("win"):
                        # Check TurboVNC version number and flavour (X11 or Java)

                        # Check TurboVNC version number
                        # For Windows, this has already been determined using the Registry.
                        self.turboVncVersionNumber = "0.0"

                        def getTurboVncVersionNumber():
                            turboVncVersionNumberCommandString = vnc + " -help"
                            proc = subprocess.Popen(turboVncVersionNumberCommandString,
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                universal_newlines=True)
                            turboVncStdout, turboVncStderr = proc.communicate(input="\n")
                            if turboVncStderr != None:
                                logger_debug("turboVncStderr: " + turboVncStderr)
                            turboVncVersionNumberComponents = turboVncStdout.split(" v")
                            turboVncVersionNumberComponents = turboVncVersionNumberComponents[1].split(" (build")
                            launcherMainFrame.loginThread.turboVncVersionNumber = turboVncVersionNumberComponents[0].strip()
                        wx.CallAfter(getTurboVncVersionNumber)
                        while self.turboVncVersionNumber=="0.0":
                            time.sleep(0.5)

                        def getTurboVncFlavour():
                            # Check TurboVNC flavour (X11 or Java) for non-Windows platforms:
                            turboVncFlavourTestCommandString = "file /opt/TurboVNC/bin/vncviewer | grep -q ASCII"
                            proc = subprocess.Popen(turboVncFlavourTestCommandString,
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                universal_newlines=True)
                            stdout, stderr = proc.communicate(input="\n")
                            if stderr != None:
                                logger_debug('turboVncFlavour stderr: ' + stderr)
                            if proc.returncode==0:
                                logger_debug("Java version of TurboVNC Viewer is installed.")
                                turboVncFlavour = "Java"
                            else:
                                logger_debug("X11 version of TurboVNC Viewer is installed.")
                                turboVncFlavour = "X11"
                            return turboVncFlavour

                        # No need to run this with wx.CallAfter, because the "file" command doesn't launch a GUI application.
                        self.turboVncFlavour = getTurboVncFlavour()

                    logger_debug("TurboVNC viewer version number = " + launcherMainFrame.loginThread.turboVncVersionNumber)

                    if launcherMainFrame.loginThread.turboVncVersionNumber.startswith("0.") or launcherMainFrame.loginThread.turboVncVersionNumber.startswith("1.0"):
                        def showOldTurboVncWarningMessageDialog():
                            dlg = wx.MessageDialog(launcherMainFrame, "Warning: Using a TurboVNC viewer earlier than v1.1 means that you will need to enter your password twice.\n",
                                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                            dlg.ShowModal()
                            dlg.Destroy()
                            launcherMainFrame.loginThread.showOldTurboVncWarningMessageDialogCompleted = True
                        launcherMainFrame.loginThread.showOldTurboVncWarningMessageDialogCompleted = False
                        wx.CallAfter(showOldTurboVncWarningMessageDialog)
                        while launcherMainFrame.loginThread.showOldTurboVncWarningMessageDialogCompleted==False:
                            time.sleep(0.1)

                    if launcherMainFrame.progressDialog is not None:
                        self.shouldAbort = launcherMainFrame.progressDialog.shouldAbort()
                    if self.shouldAbort:
                        if (launcherMainFrame.progressDialog != None):
                            wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                            wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                            launcherMainFrame.progressDialog = None
                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                        die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                        return

                    # Initial SSH login

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Logging in to " + self.host)

                    self.updatingProgressDialog = False
                    wx.CallAfter(self.updateProgressDialog, 1, "Logging in to " + self.host)
                    time.sleep(0.1)
                    while self.updatingProgressDialog:
                        time.sleep(0.1)
                    while (self.updatingProgressDialog):
                        sleep(0.1)
                    if self.shouldAbort:
                        if (launcherMainFrame.progressDialog != None):
                            wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                            wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                            launcherMainFrame.progressDialog = None
                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                        die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                        return

                    logger_debug("Attempting to log in to " + self.host)

                    self.sshClient = ssh.SSHClient()
                    self.sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())

                    try:
                        if is_managed_session():
                            logger_debug('Using CVL UM private key file')
                            self.sshClient.connect(self.host, username=self.username, key_filename=join(expanduser("~"), '.MASSIVE_keys', cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_private_key_name')))
                        else:
                            logger_debug('Using plain username/password authentication.')
                            self.sshClient.connect(self.host, username=self.username, password=self.password, look_for_keys=False)
                    except ssh.AuthenticationException, e:
                        logger_error("Failed to authenticate with user's username/password credentials: " + str(e))
                        die_from_login_thread('Authentication error with user %s on server %s' % (self.username, self.host), submit_log=False)
                        return

                    logger_debug("First login done.")

                    logger_debug('Calling "module load massive"')
                    run_ssh_command(self.sshClient, 'module load massive', ignore_errors=True)

                    # Create SSH key pair for tunnel.

                    logger_debug("Generating SSH key-pair for tunnel.")

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Generating SSH key-pair for tunnel...")

                    wx.CallAfter(self.updateProgressDialog, 2, "Generating SSH key-pair for tunnel...")
                    time.sleep(0.1)
                    while (self.updatingProgressDialog):
                        time.sleep(0.1)
                    if self.shouldAbort:
                        if (launcherMainFrame.progressDialog != None):
                            wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                            wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                            launcherMainFrame.progressDialog = None
                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                        die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                        return

                    run_ssh_command(self.sshClient, "/bin/rm -f ~/MassiveLauncherKeyPair*")
                    run_ssh_command(self.sshClient, "/usr/bin/ssh-keygen -C \"MASSIVE Launcher\" -N \"\" -t rsa -f ~/MassiveLauncherKeyPair")
                    run_ssh_command(self.sshClient, "/bin/mkdir -p ~/.ssh")
                    run_ssh_command(self.sshClient, "/bin/chmod 700 ~/.ssh")
                    run_ssh_command(self.sshClient, "/bin/touch ~/.ssh/authorized_keys")
                    run_ssh_command(self.sshClient, "/bin/chmod 600 ~/.ssh/authorized_keys")
                    run_ssh_command(self.sshClient, "/bin/sed -i -e \"/MASSIVE Launcher/d\" ~/.ssh/authorized_keys")
                    run_ssh_command(self.sshClient, "/bin/cat MassiveLauncherKeyPair.pub >> ~/.ssh/authorized_keys", log_output=False)
                    run_ssh_command(self.sshClient, "/bin/rm -f ~/MassiveLauncherKeyPair.pub")
                    privateKeyString, _ = run_ssh_command(self.sshClient, "/bin/cat MassiveLauncherKeyPair", log_output=False)

                    run_ssh_command(self.sshClient, "/bin/rm -f ~/MassiveLauncherKeyPair")

                    import tempfile
                    self.privateKeyFile = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
                    self.privateKeyFile.write(privateKeyString)
                    self.privateKeyFile.flush()
                    self.privateKeyFile.close()

                    if launcherMainFrame.progressDialog is not None:
                        self.shouldAbort = launcherMainFrame.progressDialog.shouldAbort()
                    if self.shouldAbort:
                        if (launcherMainFrame.progressDialog != None):
                            wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                            wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                            launcherMainFrame.progressDialog = None
                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                        die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                        return

                    # Define method to create SSH tunnel.
                    # We won't actually create the VNC over SSH tunnel to MASSIVE/CVL yet,
                    # but we will test the Launcher's ability to create a simple tunnel.

                    def createTunnel(localPortNumber,remoteHost,remotePortNumber,tunnelServer,tunnelUsername,tunnelPrivateKeyFileName,testRun):
                        logger_debug("Starting tunnelled SSH session.")

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

                            if sys.platform.startswith("win"):
                                # On Windows Vista/7, the private key file,
                                # will initially be created without any owner.
                                # We must set the file's owner before we
                                # can change the permissions to -rw------.
                                import getpass
                                chown_cmd = chownBinary + " \"" + getpass.getuser() + "\" " + tunnelPrivateKeyFileName
                                logger_debug('chown_cmd: ' + chown_cmd)
                                chownProcess = subprocess.Popen(chown_cmd,
                                    stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                    universal_newlines=True)
                                chownStdout, chownStderr = chownProcess.communicate(input="\r\n")
                                if chownStderr != None and chownStderr.strip()!="":
                                    logger_debug('stderr from chown_cmd: ' + chownStderr)
                                if chownStdout != None and chownStdout.strip()!="":
                                    logger_debug('stdout from chown_cmd: ' + chownStdout)

                            chmod_cmd = chmodBinary + " 600 " + tunnelPrivateKeyFileName
                            logger_debug('chmod_cmd: ' + chmod_cmd)
                            chmodProcess = subprocess.Popen(chmod_cmd,
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                universal_newlines=True)
                            chmodStdout, chmodStderr = chmodProcess.communicate(input="\r\n")
                            if chmodStderr != None and chmodStderr.strip()!="":
                                logger_debug('chmod_cmd stderr: ' + chmodStderr)
                            if chmodStdout != None and chmodStdout.strip()!="":
                                logger_debug('chmod_cmd stdout: ' + chmodStdout)

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

                            if launcherMainFrame.progressDialog is not None:
                                launcherMainFrame.loginThread.shouldAbort = launcherMainFrame.progressDialog.shouldAbort()
                            if launcherMainFrame.loginThread.shouldAbort:
                                # Don't do the usual clean up, because we are in the SSH tunnel thread.
                                # We will leave the clean up to the login thread when it detects
                                # the abort request within the while loop which waits for the tunnel
                                # to be established.
                                return

                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Creating secure tunnel...")

                            remotePortNumber = str(remotePortNumber)

                            tunnel_cmd = sshBinary + " -i " + tunnelPrivateKeyFileName + " -c " + self.cipher + " " \
                                "-t -t " \
                                "-oStrictHostKeyChecking=no " \
                                "-L " + localPortNumber + ":" + remoteHost + ":" + remotePortNumber + " -l " + tunnelUsername + " " + tunnelServer + ' "echo tunnel_hello; bash "'

                            logger_debug('tunnel_cmd: ' + tunnel_cmd)

                            # Not 100% sure if this is necessary on Windows vs Linux. Seems to break the
                            # Windows version of the launcher, but leaving in for Linux/OSX.
                            if sys.platform.startswith("win"):
                                pass
                            else:
                                tunnel_cmd = shlex.split(tunnel_cmd)

                            launcherMainFrame.loginThread.sshTunnelProcess = subprocess.Popen(tunnel_cmd,
                                universal_newlines=True,shell=False,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)

                            logger_debug('pid of ssh tunnel process: ' + str(launcherMainFrame.loginThread.sshTunnelProcess.pid))

                            launcherMainFrame.loginThread.sshTunnelReady = False
                            launcherMainFrame.loginThread.sshTunnelExceptionOccurred = False
                            while True:
                                time.sleep(0.1)
                                line = launcherMainFrame.loginThread.sshTunnelProcess.stdout.readline()
                                if "tunnel_hello" in line:
                                    logger_debug('Received tunnel_hello so ssh tunnel appears to be ok.')
                                    launcherMainFrame.loginThread.sshTunnelReady = True
                                    break
                                if line.strip()!="":
                                    logger_debug('Spurious stdout from tunnel command: ' + line)
                                if "No such file" in line:
                                    logger_error('Tunnel command reported "No such file"')
                                    launcherMainFrame.loginThread.sshTunnelExceptionOccurred = True
                                    break
                                if "is not recognized" in line:
                                    logger_error('Tunnel command reported "is not recognized"')
                                    launcherMainFrame.loginThread.sshTunnelExceptionOccurred = True
                                    break
                            if testRun:
                                launcherMainFrame.loginThread.sshTunnelProcess.terminate()

                        except:
                            logger_debug("MASSIVE/CVL Launcher v" + launcher_version_number.version_number)
                            logger_debug(traceback.format_exc())
                            launcherMainFrame.loginThread.sshTunnelExceptionOccurred = True

                    self.sshTunnelReady = False
                    self.sshTunnelExceptionOccurred = False
                    testLocalPortNumber = "0" # Request ephemeral port.
                    testTunnelServer = self.host
                    testTunnelUsername = self.username
                    testTunnelPrivateKeyFileName = self.privateKeyFile.name
                    if launcherMainFrame.massiveTabSelected:
                        #testRemoteHost = self.massiveVisNodes[0] + "-ib"
                        testRemoteHost = "localhost"
                        testRemotePortNumber = "5901"
                    else:
                        testRemoteHost = "localhost"
                        #testRemotePortNumber = str(5900+self.cvlVncDisplayNumber)
                        testRemotePortNumber = "5901"

                    testRun = True
                    testTunnelThread = threading.Thread(target=createTunnel, args=(testLocalPortNumber,testRemoteHost,testRemotePortNumber,testTunnelServer,testTunnelUsername,testTunnelPrivateKeyFileName,testRun))

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Testing SSH tunnelling...")
                    wx.CallAfter(self.updateProgressDialog, 3, "Testing SSH tunnelling...")
                    while (self.updatingProgressDialog):
                        time.sleep(0.1)
                    if self.shouldAbort:
                        if (launcherMainFrame.progressDialog != None):
                            wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                            wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                            launcherMainFrame.progressDialog = None
                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                        die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                        return

                    logger_debug("Testing SSH tunnelling.")

                    testTunnelThread.start()

                    count = 1
                    while not self.sshTunnelReady and not self.sshTunnelExceptionOccurred and count < 15:
                        if launcherMainFrame.progressDialog is not None:
                            self.shouldAbort = launcherMainFrame.progressDialog.shouldAbort()
                        if self.shouldAbort:
                            if (launcherMainFrame.progressDialog != None):
                                wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                                wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                                launcherMainFrame.progressDialog = None
                            wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                            die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                            return

                        time.sleep(1)
                        count = count + 1

                    if self.sshTunnelReady:
                        logger_debug("SSH tunnelling appears to be working correctly.")
                    else:
                        logger_error("Cannot create an SSH tunnel to " + testTunnelServer)
                        def showCantCreateSshTunnelMessageDialog():
                            dlg = wx.MessageDialog(launcherMainFrame, "Error: Cannot create an SSH tunnel to\n\n" +
                                                    "    " + testTunnelServer + "\n\n" +
                                                    "The launcher cannot continue.\n",
                                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                            dlg.ShowModal()
                            dlg.Destroy()
                            launcherMainFrame.loginThread.showCantCreateSshTunnelMessageDialogCompleted = True
                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                        if (launcherMainFrame.progressDialog != None):
                            wx.CallAfter(launcherMainFrame.progressDialog.Hide)
                            wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                            wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                            launcherMainFrame.progressDialog = None
                        wx.CallAfter(launcherMainFrame.logWindow.Show, True)
                        launcherMainFrame.loginThread.showCantCreateSshTunnelMessageDialogCompleted = False
                        wx.CallAfter(showCantCreateSshTunnelMessageDialog)
                        while launcherMainFrame.loginThread.showCantCreateSshTunnelMessageDialogCompleted==False:
                            time.sleep(0.1)
                        try:
                            if os.path.isfile(self.privateKeyFile.name):
                                os.unlink(self.privateKeyFile.name)
                            launcherMainFrame.loginThread.sshTunnelProcess.terminate()
                            self.sshClient.close()
                        finally:
                            dump_log(submit_log=True)
                            os._exit(1)

                    if launcherMainFrame.massiveTabSelected:

                        # Begin if launcherMainFrame.massiveTabSelected:

                        # Run sanity check script
                        run_ssh_command(self.sshClient, "/usr/local/desktop/sanity_check.sh")

                        self.massiveVisNodes = []
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Setting display resolution...")
                        wx.CallAfter(self.updateProgressDialog, 4, "Setting display resolution...")
                        while (self.updatingProgressDialog):
                            time.sleep(0.1)
                        if self.shouldAbort:
                            if (launcherMainFrame.progressDialog != None):
                                wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                                wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                                launcherMainFrame.progressDialog = None
                            wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                            die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                            return

                        set_display_resolution_cmd = "/usr/local/desktop/set_display_resolution.sh " + self.resolution
                        run_ssh_command(self.sshClient, set_display_resolution_cmd)

                        if self.host.startswith("m2"):
                            logger_debug("Checking whether you have any existing jobs in the Vis node queue.")
                            logger_debug("showq -w class:vis -u " + self.username + " | grep " + self.username)
                            # Using ignore_errors=True, because if we run "showq" for a new user, before they
                            # have submitted any jobs, we can get the following error:
                            # ERROR:    unknown user specified
                            stdoutRead, stderrRead = run_ssh_command(self.sshClient, "showq -w class:vis -u " + self.username + " | grep " + self.username, ignore_errors=True)
                            if stdoutRead.strip()!="" and launcherMainFrame.massivePersistentMode==False:
                                stdoutReadSplit = stdoutRead.split(" ")
                                jobNumber = stdoutReadSplit[0] # e.g. 3050965
                                if (launcherMainFrame.progressDialog != None):
                                    wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                                    launcherMainFrame.progressDialog = None
                                wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                                wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                                logger_error("MASSIVE Launcher only allows you to have one job in the Vis node queue.")
                                def showExistingJobFoundInVisNodeQueueMessageDialog():
                                    dlg = wx.MessageDialog(launcherMainFrame, "Error: MASSIVE Launcher only allows you to have one job in the Vis node queue.\n\n" +
                                                                            "You already have at least one job in the Vis node queue:\n\n" +
                                                                            stdoutRead.strip() + "\n\n" +
                                                                            "To delete existing Vis node job(s), SSH to\n" +
                                                                            self.host + " and run:\n\n" +
                                                                            "qdel <jobNumber>\n\n" +
                                                                            "e.g. qdel " + jobNumber + "\n\n" +
                                                            "The launcher cannot continue.\n",
                                                    "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                                    dlg.ShowModal()
                                    dlg.Destroy()
                                    launcherMainFrame.loginThread.showExistingJobFoundInVisNodeQueueMessageDialogCompleted = True
                                launcherMainFrame.loginThread.showExistingJobFoundInVisNodeQueueMessageDialogCompleted = False
                                wx.CallAfter(showExistingJobFoundInVisNodeQueueMessageDialog)
                                while launcherMainFrame.loginThread.showExistingJobFoundInVisNodeQueueMessageDialogCompleted==False:
                                    time.sleep(0.1)
                                try:
                                    if os.path.isfile(self.privateKeyFile.name):
                                        os.unlink(self.privateKeyFile.name)
                                    self.sshClient.close()
                                finally:
                                    dump_log(submit_log=True)
                                    os._exit(1)
                            if stdoutRead.strip()=="":
                                logger_debug("You don't have any jobs already in the Vis node queue, which is good.")

                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Checking quota...")
                        wx.CallAfter(self.updateProgressDialog, 5, "Checking quota...")
                        while (self.updatingProgressDialog):
                            time.sleep(0.1)
                        if self.shouldAbort:
                            if (launcherMainFrame.progressDialog != None):
                                wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                                wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                                launcherMainFrame.progressDialog = None
                            wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                            die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                            return

                        # Get list of user's MASSIVE projects from Karaage:
                        try:
                            xmlrpcServer = xmlrpclib.Server("https://m2-web.massive.org.au/kgadmin/xmlrpc/")
                            xmlrpcQueryResult = xmlrpcServer.get_users_projects(self.username, self.password)
                            logger_debug("xmlrpcQueryResult = <%s>" % (xmlrpcQueryResult,))

                            self.massive_projects_of_current_user = xmlrpcQueryResult[1]
                        except:
                            error_string = 'Error contacting Massive to retrieve user projects list'
                            logger_error(error_string)
                            die_from_login_thread(error_string)
                            return

                        if not launcherMainFrame.massiveProject in self.massive_projects_of_current_user:
                            error_string = ("You have requested use of project \"" + launcherMainFrame.massiveProject + "\",\n"
                                             "but you don't have access to that project.")
                            logger_error(error_string)
                            die_from_login_thread(error_string)
                            return

                        gbalance_stdout, gbalance_stderr = run_ssh_command(self.sshClient, "gbalance -u %s -p %s --hours --total" % (self.username, launcherMainFrame.massiveProject,))
                        if gbalance_stdout is None: gbalance_stdout = ''
                        if gbalance_stderr is None: gbalance_stderr = ''

                        gbalance_stdout = gbalance_stdout.splitlines()

                        try:
                            if gbalance_stdout[0].rstrip() == 'Balance' and gbalance_stdout[1].rstrip() == '-------':
                                cpuHoursRemaining = float(gbalance_stdout[2])
                            else:
                                raise ValueError, 'Could not parse gbalance output.'
                        except:
                            error_string = "Could not determine balance for user <%s> in project <%s>" % (self.username, launcherMainFrame.massiveProject,)
                            logger_error(error_string)
                            die_from_login_thread(error_string)

                        cpusPerVisNode = 12
                        cpuHoursRequested = int(launcherMainFrame.massiveHoursRequested) * int(launcherMainFrame.massiveVisNodesRequested) * cpusPerVisNode
                        if cpuHoursRemaining < cpuHoursRequested:
                            error_string = ("You have requested " + str(cpuHoursRequested) + " CPU hours,\n"
                                            "but you only have " + str(cpuHoursRemaining) + " CPU hours remaining\n"
                                            "in your quota for project \"" + launcherMainFrame.massiveProject + "\".")
                            logger_error(error_string)
                            die_from_login_thread(error_string)
                            return

                        if self.host.startswith("m2"):
                            numberOfBusyVisNodesStdout, _ = run_ssh_command(self.sshClient, "echo `showq -w class:vis | grep \"processors in use by local jobs\" | awk '{print $1}'` of 10 nodes in use")

                            def showAllVisnodesBusyWarningDialog():
                                dlg = wx.MessageDialog(launcherMainFrame,
                                        "All MASSIVE Vis nodes are currently busy.\n" +
                                        "Your job will not begin immediately.",
                                                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                                dlg.ShowModal()
                                dlg.Destroy()

                            if "10 of 10" in numberOfBusyVisNodesStdout:
                                logger_warning("All MASSIVE Vis nodes are currently busy.  Your job will not begin immediately.")
                                showAllVisnodesBusyWarningDialog()


                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Requesting remote desktop...")
                        wx.CallAfter(self.updateProgressDialog, 6, "Requesting remote desktop...")
                        while (self.updatingProgressDialog):
                            time.sleep(0.1)
                        if self.shouldAbort:
                            if (launcherMainFrame.progressDialog != None):
                                wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                                wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                                launcherMainFrame.progressDialog = None
                            wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                            die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                            return

                        # There are two new options added to the request_visnode.sh script, 
                        # which can be used to disable the server-side qstat and qpeek,
                        # both of which require running sleep on the server side.
                        # However neither option is used in this version of the wxPython
                        # Launcher.  They are needed more for the Java Launcher.

                        #whetherServerSideScriptShouldRunQstat = False
                        #whetherServerSideScriptShouldRunQpeek = False
                        #qsubcmd = "/usr/local/desktop/request_visnode.sh " + launcherMainFrame.massiveProject + " " + launcherMainFrame.massiveHoursRequested + " " + launcherMainFrame.massiveVisNodesRequested + " " + str(launcherMainFrame.massivePersistentMode) + " " + str(whetherServerSideScriptShouldRunQstat) + " " + str(whetherServerSideScriptShouldRunQpeek)

                        qsubcmd = "/usr/local/desktop/request_visnode.sh " + launcherMainFrame.massiveProject + " " + launcherMainFrame.massiveHoursRequested + " " + launcherMainFrame.massiveVisNodesRequested + " " + str(launcherMainFrame.massivePersistentMode)

                        logger_debug('qsubcmd: ' + qsubcmd)

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
                        jobIdFullLineNumber = -1
                        breakOutOfMainLoop = False
                        lineFragment = ""
                        checkedShowStart = False
                        self.massiveJobNumber = "0"
                        self.deletedMassiveJob = False
                        self.warnedUserAboutNotDeletingJob = False

                        while True:
                            tCheck = 0

                            if launcherMainFrame.progressDialog is not None:
                                self.shouldAbort = launcherMainFrame.progressDialog.shouldAbort()

                            if self.shouldAbort:
                                # Now using ignore_errors=True, because of CVLFAB-449
                                deleteMassiveJobIfNecessary(write_debug_log=True,update_status_bar=True,update_main_progress_bar=True,ignore_errors=True)
                                if launcherMainFrame.progressDialog != None:
                                    wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                                    wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                                    launcherMainFrame.progressDialog = None
                                wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                                wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                                die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                                return

                            while not channel.recv_ready() and not channel.recv_stderr_ready():
                                #Use asterisks to simulate progress bar:
                                #wx.CallAfter(sys.stdout.write, "*")
                                time.sleep(1)
                                tCheck+=1
                                if tCheck >= 5:
                                    # After 5 seconds, we still haven't obtained a visnode...
                                    if (not checkedShowStart) and self.massiveJobNumber!="0":
                                        checkedShowStart = True
                                        def showStart():
                                            sshClient2 = ssh.SSHClient()
                                            sshClient2.set_missing_host_key_policy(ssh.AutoAddPolicy())
                                            sshClient2.connect(self.host,username=self.username,password=self.password)

                                            stdoutRead, stderrRead = run_ssh_command(sshClient2, "showstart " + self.massiveJobNumber, ignore_errors=True)
                                            if not "00:00:00" in stdoutRead:
                                                logger_debug("showstart " + self.massiveJobNumber + "...")
                                                logger_debug('showstart stderr: ' + stderrRead)
                                                logger_debug('showstart stdout: ' + stdoutRead)

                                                showstartLines = stdoutRead.split("\n")
                                                for showstartLine in showstartLines:
                                                    if showstartLine.startswith("Estimated Rsv based start"):
                                                        showstartLineComponents = showstartLine.split(" on ")
                                                        if not showstartLineComponents[1].startswith("-"):
                                                            wx.CallAfter(self.updateProgressDialog, 6, "Estimated start: " + showstartLineComponents[1])
                                            sshClient2.close()

                                        showStartThread = threading.Thread(target=showStart)
                                        showStartThread.start()
                                    break
                            if (channel.recv_stderr_ready()):
                                out = channel.recv_stderr(1024)
                                buff = StringIO(out)
                                line = lineFragment + buff.readline()
                                while line != "":
                                    logger_error('channel.recv_stderr_ready(): ' + line)
                                    wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                            if (channel.recv_ready()):
                                out = channel.recv(1024)
                                buff = StringIO(out)
                                line = lineFragment + buff.readline()
                                while line != "":
                                    lineNumber += 1
                                    if not line.endswith("\n") and not line.endswith("\r"):
                                        lineFragment = line
                                        break
                                    else:
                                        lineFragment = ""
                                        logger_debug("request_visnode.sh: " + line)
                                    if "ERROR" in line or "Error" in line or "error" in line:
                                        logger_error('error in line: ' + line)
                                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                                    if "waiting for job" in line:
                                        logger_debug('waiting for job in line: ' + line)
                                        lineSplit = line.split(" ")
                                        jobNumberString = lineSplit[4] # e.g. 3050965.m2-m
                                        jobNumberSplit = jobNumberString.split(".")
                                        self.massiveJobNumber = jobNumberSplit[0]
                                    # This is for batch mode:
                                    if "jobid_full" in line:
                                        logger_debug("Found jobid_full in request_visnode.sh output.")
                                        jobIdFullLineNumber = lineNumber
                                    if jobIdFullLineNumber!=-1 and lineNumber == (jobIdFullLineNumber+1):
                                        logger_debug("Parsing the line following \"jobid_full\" for job number.")
                                        jobNumberSplit = line.split(".")
                                        self.massiveJobNumber = jobNumberSplit[0]
                                        logger_debug("Batch mode self.massiveJobNumber = " + self.massiveJobNumber)
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

                        if len(self.massiveVisNodes)==0:
                            if int(launcherMainFrame.massiveVisNodesRequested) > 1:
                                error_string = "Couldn't get the requested number of MASSIVE Vis nodes."
                            else:
                                error_string = "Couldn't get a MASSIVE Vis node."
                            # Now using ignore_errors=True, because of CVLFAB-449
                            deleteMassiveJobIfNecessary(write_debug_log=True,update_status_bar=False,update_main_progress_bar=False,ignore_errors=True)
                            logger_error(error_string)
                            die_from_login_thread(error_string)
                            return

                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Acquired desktop node:" + self.massiveVisNodes[0])
                        wx.CallAfter(self.updateProgressDialog, 7, "Acquired desktop node: " + self.massiveVisNodes[0])
                        while (self.updatingProgressDialog):
                            time.sleep(0.1)
                        if self.shouldAbort:
                            if (launcherMainFrame.progressDialog != None):
                                wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                                wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                                launcherMainFrame.progressDialog = None
                            wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                            die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                            return

                        visnode_id = ''

                        if int(launcherMainFrame.massiveVisNodesRequested)>1:
                            visnode_id += 's: '
                        else:
                            visnode_id += ': '

                        for visNodeNumber in range(0,int(launcherMainFrame.massiveVisNodesRequested)):
                            visnode_id += self.massiveVisNodes[visNodeNumber] + " "

                        logger_debug("Massive Desktop visnode" + visnode_id)

                        # End if launcherMainFrame.massiveTabSelected:
                    else:
                        if launcherMainFrame.cvlVncDisplayNumberAutomatic==True:
                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Requesting remote desktop...")
                            wx.CallAfter(self.updateProgressDialog, 6, "Requesting remote desktop...")
                        else:
                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Connecting to remote desktop...")
                            wx.CallAfter(self.updateProgressDialog, 6, "Connecting to remote desktop...")
                        while (self.updatingProgressDialog):
                            time.sleep(0.1)
                        if self.shouldAbort:
                            if (launcherMainFrame.progressDialog != None):
                                wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                                wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                                launcherMainFrame.progressDialog = None
                            wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                            die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                            return

                        self.cvlVncDisplayNumber = launcherMainFrame.cvlVncDisplayNumber
                        if launcherMainFrame.cvlVncDisplayNumberAutomatic==True:
                            cvlVncServerCommand = "vncsession --vnc turbovnc --geometry \"" + launcherMainFrame.cvlVncDisplayResolution + "\""
                            if launcherMainFrame.cvlVncDisplayNumberAutomatic==False:
                                cvlVncServerCommand = cvlVncServerCommand + " --display " + str(self.cvlVncDisplayNumber)
                            logger_debug('cvlVncServerCommand: ' + cvlVncServerCommand)
                            stdoutRead, stderrRead = run_ssh_command(self.sshClient, cvlVncServerCommand, ignore_errors=True) # vncsession sends output to stderr? Really?
                            lines = stderrRead.split("\n")
                            foundDisplayNumber = False
                            for line in lines:
                                if "desktop is" in line or "started on display" in line:
                                    lineComponents = line.split(":")
                                    self.cvlVncDisplayNumber = int(lineComponents[-1])
                                    foundDisplayNumber = True

                        if launcherMainFrame.cvlVncDisplayNumberAutomatic==False:
                            logger_debug("CVL VNC Display Number is " + str(self.cvlVncDisplayNumber))
                        if launcherMainFrame.cvlVncDisplayNumberAutomatic==True:
                            if foundDisplayNumber:
                                logger_debug("CVL VNC Display Number is " + str(self.cvlVncDisplayNumber))
                                wx.CallAfter(launcherMainFrame.cvlVncDisplayNumberSpinCtrl.SetValue, int(self.cvlVncDisplayNumber))
                            else:
                                logger_error("Failed to parse vncserver output for display number.")
                                die_from_login_thread("Failed to parse vncserver output for display number.", submit_log=True)
                                return

                    self.sshTunnelReady = False
                    self.sshTunnelExceptionOccurred = False
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
                    testRun = False
                    tunnelThread = threading.Thread(target=createTunnel, args=(localPortNumber,remoteHost,remotePortNumber,tunnelServer,tunnelUsername,tunnelPrivateKeyFileName,testRun))

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Creating secure tunnel...")

                    if launcherMainFrame.massiveTabSelected:
                        wx.CallAfter(self.updateProgressDialog, 8, "Creating secure tunnel...")
                    else:
                        wx.CallAfter(self.updateProgressDialog, 7, "Creating secure tunnel...")
                    while (self.updatingProgressDialog):
                        time.sleep(0.1)
                    if self.shouldAbort:
                        if (launcherMainFrame.progressDialog != None):
                            wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                            wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                            launcherMainFrame.progressDialog = None
                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                        die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                        return

                    tunnelThread.start()

                    count = 1
                    while not self.sshTunnelReady and not self.sshTunnelExceptionOccurred and count < 30:
                        if launcherMainFrame.progressDialog is not None:
                            self.shouldAbort = launcherMainFrame.progressDialog.shouldAbort()
                        if self.shouldAbort:
                            if (launcherMainFrame.progressDialog != None):
                                wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                                wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                                launcherMainFrame.progressDialog = None
                            wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                            die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                            return

                        time.sleep(1)
                        count = count + 1

                    if count < 5:
                        time.sleep(5-count)

                    self.turboVncStartTime = datetime.datetime.now()

                    # TurboVNC

                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Launching TurboVNC...")

                    wx.CallAfter(self.updateProgressDialog, 9, "Launching TurboVNC...")
                    while (self.updatingProgressDialog):
                        time.sleep(0.1)
                    if self.shouldAbort:
                        if (launcherMainFrame.progressDialog != None):
                            wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
                            wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                            launcherMainFrame.progressDialog = None
                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                        die_from_login_thread("User aborted from progress dialog.", display_error_dialog=False)
                        return

                    if launcherMainFrame.massiveTabSelected:
                        logger_debug("Starting MASSIVE VNC.")
                    if launcherMainFrame.cvlTabSelected:
                        logger_debug("Starting CVL VNC...")

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
                            if self.turboVncFlavour == "X11":
                                vncOptionsString = "-encodings \"tight copyrect\""
                            else:
                                vncOptionsString = "-encoding \"Tight\""

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

                        def destroyProgressDialog():
                            self.updateProgressDialog(10, "Launching TurboVNC...")
                            launcherMainFrame.progressDialog.Show(False)
                            if (launcherMainFrame.progressDialog != None):
                                wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                                launcherMainFrame.progressDialog = None

                        wx.CallAfter(destroyProgressDialog)

                        self.turboVncProcess = None
                        self.turboVncStdout = None
                        self.turboVncStderr = None
                        self.turboVncCompleted = False

                        if is_managed_session() and cvlLauncherConfig.has_option("CVL Launcher Preferences", 'CVL_UM_vnc_password'):
                            self.password = cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_vnc_password')

                        def launchTurboVNC():
                            if sys.platform.startswith("win"):
                                vncCommandString = "\""+vnc+"\" /user "+self.username+" /autopass " + vncOptionsString + " localhost::" + launcherMainFrame.loginThread.localPortNumber
                                logger_debug('vncCommandString windows: ' +  vncCommandString)
                                self.turboVncProcess = subprocess.Popen(vncCommandString,
                                    stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                    universal_newlines=True)
                                self.turboVncStdout, self.turboVncStderr = self.turboVncProcess.communicate(input=self.password + "\r\n")
                            else:
                                vncCommandString = vnc + " -user " + self.username + " -autopass " + vncOptionsString + " localhost::" + launcherMainFrame.loginThread.localPortNumber
                                logger_debug('vncCommandString linux/darwin: ' + vncCommandString)
                                self.turboVncProcess = subprocess.Popen(vncCommandString,
                                    stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                                    universal_newlines=True)
                                self.turboVncStdout, self.turboVncStderr = self.turboVncProcess.communicate(input=self.password + "\n")
                            self.turboVncCompleted = True
                        launchTurboVNC()
                        while self.turboVncCompleted==False:
                            time.sleep(0.1)

                        # Remove "Launching TurboVNC..." from status bar:
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")

                        # The original method used to grab the focus back from
                        # TurboVNC viewer failed rather ungracefully a few
                        # times recently, so it was commented out.
                        # A new method is now being trialed, using a slightly
                        # different Apple Script and using wx.CallAfter
                        # to prevent GUI threading problems.

                        if sys.platform.startswith("darwin") and launcherMainFrame.cvlTabSelected:
                            def grabFocusBackFromTurboVNC():
                                subprocess.Popen(['osascript', '-e',
                                    #"tell application \"System Events\"\r" +
                                    #"  set procName to name of first process whose unix id is " + str(os.getpid()) + "\r" +
                                    #"end tell\r" +
                                    #"tell application procName to activate\r"])
                                    "tell application \"System Events\"\r" +
                                    "  set launcherApps to every process whose name contains \"Launcher\"\r" +
                                    "  try\r" +
                                    "    set launcherApp to item 1 of launcherApps\r" +
                                    "    set frontmost of launcherApp to true\r" +
                                    "    tell application launcherApp to activate\r" +
                                    "  end try\r" +
                                    "end tell\r"])
                            wx.CallAfter(grabFocusBackFromTurboVNC)

                        self.turboVncFinishTime = datetime.datetime.now()

                        logger_debug('turboVncFinishTime = ' + str(self.turboVncFinishTime))

                        if self.turboVncStderr != None and self.turboVncStderr.strip()!="":
                            logger_debug('self.turboVncStderr: ' + self.turboVncStderr)

                        if self.turboVncProcess.returncode != 0:
                            logger_debug('self.turboVncStdout: ' + self.turboVncStdout)

                        try:
                            logger_debug('at start of try... clause when TurboVNC has exited')

                            if launcherMainFrame.cvlTabSelected:
                                logger_debug('launcherMainFrame.cvlTabSelected == True')

                                def askCvlUserWhetherTheyWantToKeepOrDiscardTheirVncSession(sshClient2):
                                    import questionDialog
                                    result = questionDialog.questionDialog("Do you want to keep your VNC session (Display #" + str(self.cvlVncDisplayNumber) + ") running for future use?",
                                        #buttons=["Discard VNC Session", wx.ID_CANCEL, "Save VNC Session"])
                                        buttons=["Discard VNC Session", "Save VNC Session"],
                                        caption="MASSIVE/CVL Launcher")
                                    if result == "Discard VNC Session":
                                        cvlVncSessionStopCommand = "vncsession stop " + str(self.cvlVncDisplayNumber)
                                        logger_debug('cvlVncSessionStopCommand: ' + cvlVncSessionStopCommand)

                                        logger_debug('Running cvlVncSessionStopCommand')
                                        run_ssh_command(sshClient2, cvlVncSessionStopCommand, ignore_errors=True, log_output=True) # yet another command that sends output to stderr FIXME we should parse this and check for real errors

                                        logger_debug('Closing sshClient2.')
                                        # sshClient2.close()
                                        logger_debug('Closed sshClient2 connection.')

                                    launcherMainFrame.loginThread.askCvlUserWhetherTheyWantToKeepOrDiscardTheirVncSessionCompleted = True

                                logger_debug('About to ask user if they want to keep or kill their VNC session...')

                                wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Checking if user wants to terminate or keep the VNC session...")

                                launcherMainFrame.loginThread.askCvlUserWhetherTheyWantToKeepOrDiscardTheirVncSessionCompleted = False

                                # Earlier sshClient connection may have timed out by now.
                                logger_debug('Creating sshClient2')
                                sshClient2 = ssh.SSHClient()

                                logger_debug('Setting missing host policy.')
                                sshClient2.set_missing_host_key_policy(ssh.AutoAddPolicy())

                                logger_debug('Logging in')

                                if is_managed_session():
                                    logger_debug('Using CVL UM private key file')
                                    sshClient2.connect(self.host,username=self.username, key_filename=join(expanduser("~"), '.MASSIVE_keys', cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_private_key_name')))
                                else:
                                    logger_debug('Using plain username/password authentication.')
                                    sshClient2.connect(self.host,username=self.username,password=self.password)

                                wx.CallAfter(askCvlUserWhetherTheyWantToKeepOrDiscardTheirVncSession, sshClient2)

                                logger_debug('Now waiting for the user to click keep or discard...')
                                while launcherMainFrame.loginThread.askCvlUserWhetherTheyWantToKeepOrDiscardTheirVncSessionCompleted==False:
                                    #logger_debug('launcherMainFrame.loginThread.askCvlUserWhetherTheyWantToKeepOrDiscardTheirVncSessionCompleted == False, sleeping for one second...')
                                    time.sleep(0.1)

                                sshClient2.close()
                                self.turboVncFinishTime = datetime.datetime.now()
                                logger_debug('self.turboVncFinishTime = ' + str(self.turboVncFinishTime))
                            else:
                                logger_debug("launcherMainFrame.cvlTabSelected == False, so we don't need to stop the VNC session.")

                            wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_WAIT))
                            logger_debug('Now tidying up the environment.')

                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Removing the private key file.")

                            try:
                                logger_debug('Removing the private key file')
                                if os.path.isfile(launcherMainFrame.loginThread.privateKeyFile.name):
                                    os.unlink(launcherMainFrame.loginThread.privateKeyFile.name)
                            except:
                                logger_debug('Error while unlinking private key file...')
                                logger_debug(traceback.format_exc())

                            # Now using ignore_errors=True, because of CVLFAB-449
                            deleteMassiveJobIfNecessary(write_debug_log=True,update_status_bar=True,update_main_progress_bar=False,ignore_errors=True)

                            wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "Terminating the SSH tunnel process.")

                            logger_debug('Now terminating the ssh tunnel process.')
                            launcherMainFrame.loginThread.sshTunnelProcess.terminate()

                        finally:
                            logger_debug('In the "finally" clause for tidying up TurboVNC.')
                            # If the TurboVNC process completed less than 3 seconds after it started,
                            # then the Launcher assumes that something went wrong, so it will
                            # remain open to display any STDERR from TurboVNC in its Log window,
                            # rather than automatically exiting. This technique is most useful for
                            # the Mac / Linux (X11) version of TurboVNC.  On Windows, the TurboVNC
                            # viewer may display an error message in a message dialog for longer
                            # than 3 seconds.
                            turboVncElapsedTime = self.turboVncFinishTime - self.turboVncStartTime
                            turboVncElapsedTimeInSeconds = turboVncElapsedTime.total_seconds()
                            if turboVncElapsedTimeInSeconds>=3 and (self.turboVncStderr==None or self.turboVncStderr.strip()==""):
                                logger_debug('Elapsed time at least 3 seconds and return code ok, so exiting.')
                                dump_log()
                                os._exit(0)
                            elif turboVncElapsedTimeInSeconds<3:
                                logger_debug("Disabling auto-quit because TurboVNC's elapsed time is less than 3 seconds.")
                                if launcherMainFrame.massiveTabSelected:
                                    wx.CallAfter(launcherMainFrame.massiveShowDebugWindowCheckBox.SetValue, True)
                                else:
                                    wx.CallAfter(launcherMainFrame.cvlShowDebugWindowCheckBox.SetValue, True)
                                if launcherMainFrame.logWindow!=None:
                                    wx.CallAfter(launcherMainFrame.logWindow.Show, True)
                                    def disabling_auto_quit_because_TurboVNC_exited_abruptly():
                                        dlg = wx.MessageDialog(launcherMainFrame,
                                                        "Disabling auto-quit because TurboVNC exited abruptly.",
                                                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                                        dlg.ShowModal()
                                        dlg.Destroy()
                                    wx.CallAfter(disabling_auto_quit_because_TurboVNC_exited_abruptly)
                            elif self.turboVncStderr!=None and self.turboVncStderr.strip()!="":
                                logger_debug("Disabling auto-quit because TurboVNC returned an error message.")
                                if launcherMainFrame.massiveTabSelected:
                                    wx.CallAfter(launcherMainFrame.massiveShowDebugWindowCheckBox.SetValue, True)
                                else:
                                    wx.CallAfter(launcherMainFrame.cvlShowDebugWindowCheckBox.SetValue, True)
                                if launcherMainFrame.logWindow!=None:
                                    wx.CallAfter(launcherMainFrame.logWindow.Show, True)
                                    def disabling_auto_quit_because_TurboVNC_returned_an_error_message():
                                        dlg = wx.MessageDialog(launcherMainFrame,
                                                        "Disabling auto-quit because TurboVNC returned an error message.",
                                                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                                        dlg.ShowModal()
                                        dlg.Destroy()
                                    wx.CallAfter(disabling_auto_quit_because_TurboVNC_returned_an_error_message)

                        logger_debug('Setting the cursor back to CURSOR_ARROW.')
                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))

                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                    except:
                        logger_debug('Exception (a)')
                        logger_debug(traceback.format_exc())

                        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                        if (launcherMainFrame.progressDialog != None):
                            wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                            launcherMainFrame.progressDialog = None
                        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                        if launcherMainFrame.massiveTabSelected:
                            wx.CallAfter(launcherMainFrame.massiveShowDebugWindowCheckBox.SetValue, True)
                        else:
                            wx.CallAfter(launcherMainFrame.cvlShowDebugWindowCheckBox.SetValue, True)
                        if launcherMainFrame.logWindow!=None:
                            wx.CallAfter(launcherMainFrame.logWindow.Show, True)

                except:
                    logger_debug('Exception (b)')
                    logger_debug(traceback.format_exc())

                    wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
                    if (launcherMainFrame.progressDialog != None):
                        wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                        launcherMainFrame.progressDialog = None
                    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
                    if launcherMainFrame.massiveTabSelected:
                        wx.CallAfter(launcherMainFrame.massiveShowDebugWindowCheckBox.SetValue, True)
                    else:
                        wx.CallAfter(launcherMainFrame.cvlShowDebugWindowCheckBox.SetValue, True)
                    if launcherMainFrame.logWindow!=None:
                        wx.CallAfter(launcherMainFrame.logWindow.Show, True)

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
            self.massivePersistentMode = self.massivePersistentModeCheckBox.GetValue()
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
                    error_string = "Error contacting Massive to retrieve user's default project"
                    logger_error(error_string)
                    die_from_main_frame(error_string)
                    return

                if self.massiveProject in self.massiveProjects:
                    self.massiveProjectComboBox.SetSelection(self.massiveProjects.index(self.massiveProject))
                else:
                    # Project was not found in combo-box.
                    self.massiveProjectComboBox.SetSelection(-1)
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
            cvlLauncherConfig.set("CVL Launcher Preferences", "cvl_show_advanced_options", self.cvlShowAdvancedOptions)

        if launcherMainFrame.massiveTabSelected:
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_project", self.massiveProject)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_hours_requested", self.massiveHoursRequested)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_visnodes_requested", self.massiveVisNodesRequested)
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_persistent_mode", self.massivePersistentMode)

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

        # Send all log messages to the debug window, which may or may not be visible.
        log_window_handler = logging.StreamHandler(stream=self.logTextCtrl)
        log_window_handler.setLevel(logging.DEBUG)
        log_format_string = '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'
        log_window_handler.setFormatter(logging.Formatter(log_format_string))
        logger.addHandler(log_window_handler)
        # Don't send ssh.transport log messages to
        # the log window, because they won't be
        # wrapped in wx.CallAfter, unless we provide
        # our own customized version of the ssh module.
        #transport_logger.addHandler(log_window_handler)

        if launcherMainFrame.massiveTabSelected:
            self.logWindow.Show(self.massiveShowDebugWindowCheckBox.GetValue())
        else:
            self.logWindow.Show(self.cvlShowDebugWindowCheckBox.GetValue())

        self.loginThread = LoginThread(self)
        self.loginThread.start()

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

if __name__ == '__main__':
    app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
    app.MainLoop()

