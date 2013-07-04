import threading
import wx
import logging
from StringIO import StringIO
import HTMLParser
import os
import time
import subprocess
import inspect
import sys
import itertools


#LAUNCHER_URL = "https://www.massive.org.au/index.php?option=com_content&view=article&id=121"
global LAUNCHER_URL
LAUNCHER_URL = "https://www.massive.org.au/userguide/cluster-instructions/massive-launcher"

# TURBOVNC_BASE_URL = "http://www.virtualgl.org/DeveloperInfo/PreReleases"
global TURBOVNC_BASE_URL
TURBOVNC_BASE_URL = "http://sourceforge.net/projects/virtualgl/files/TurboVNC/"

def parseMessages(regexs,stdout,stderr):
    # compare each line of output against a list of regular expressions and build up a dictionary of messages to give the user
    messages={}
    for line  in itertools.chain(stdout.splitlines(True),stderr.splitlines(True)):
        for re in regexs:
            match = re.search(line)
            if (match):
                for key in match.groupdict().keys():
                    if messages.has_key(key):
                        messages[key]=messages[key]+match.group(key)
                    else:
                        messages[key]=match.group(key)
    return messages

class HelpDialog(wx.Dialog):
    def __init__(self, *args, **kw):
        super(HelpDialog, self).__init__(*args, **kw)

        self.callback=None
         
        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        iconPanel = wx.Panel(self)

        import MASSIVE_icon
        iconAsBitmap = MASSIVE_icon.getMASSIVElogoTransparent128x128Bitmap()
        wx.StaticBitmap(iconPanel, wx.ID_ANY,
            iconAsBitmap,
            (0, 25),
            (iconAsBitmap.GetWidth(), iconAsBitmap.GetHeight()))

        sizer = wx.FlexGridSizer(rows=2, cols=2, vgap=5, hgap=5)


        contactPanel = wx.Panel(self)
        contactPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=5, hgap=5)
        contactPanel.SetSizer(contactPanelSizer)
        contactQueriesContactLabel = wx.StaticText(contactPanel, label = "For queries, please contact:")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(9)
        contactQueriesContactLabel.SetFont(font)

        contactEmailHyperlink = wx.HyperlinkCtrl(contactPanel, id = wx.ID_ANY, label = "help@massive.org.au", url = "mailto:help@massive.org.au")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(8)
        contactEmailHyperlink.SetFont(font)

#        contactPanelSizer.Add(wx.StaticText(contactPanel, wx.ID_ANY, ""))
        contactPanelSizer.Add(contactQueriesContactLabel, border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BORDER)
        contactPanelSizer.Add(contactEmailHyperlink, border=20, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.BORDER)

        #contactPanelSizer.Add(wx.StaticText(contactPanel))
        contactPanelSizer.Fit(contactPanel)

        okButton = wx.Button(self, 1, ' OK ')
        okButton.SetDefault()
        okButton.Bind(wx.EVT_BUTTON, self.OnClose)

        sizer.Add(iconPanel, flag=wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_LEFT)
        sizer.Add(contactPanel)
        sizer.Add(okButton, flag=wx.RIGHT|wx.BOTTOM)
        #sizer.Add(wx.StaticText(self,label="       "))
        self.SetSizer(sizer)
        sizer.Fit(self)

    def setCallback(self,callback):
        self.callback=callback


    def addPanel(self,panel):
        self.GetSizer().Insert(1,panel,flag=wx.EXPAND)
        self.GetSizer().Fit(self)


    def OnClose(self, e):
        self.Destroy()
        if self.callback != None:
            self.callback()


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

def dump_log(launcherMainFrame,submit_log=False):
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
        elif os.path.exists('/opt/MassiveLauncher/cacert.pem'):
            r = requests.post(url, files=file_info, verify='/opt/MassiveLauncher/cacert.pem')
        elif os.path.exists('c:/program files/massive launcher/cacert.pem'):
            r = requests.post(url, files=file_info, verify='c:/program files/massive launcher/cacert.pem')
        elif os.path.exists('c:/program files (x86)/massive launcher/cacert.pem'):
            r = requests.post(url, files=file_info, verify='c:/program files (x86)/massive launcher/cacert.pem')
        else:
            r = requests.post(url, files=file_info)

    return

def seconds_to_hours_minutes(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return int(h), int(m)

def job_has_been_canceled(ssh_cmd, launcherMainFrame,job_id):
    """
    When a visnode job is canceled, a file of the form
    $HOME/.vnc/shutdown_${JOB_ID}.${NODE} is created, e.g.
    $HOME/.vnc/shutdown_1234567.m2-m. This function checks if
    a particular shutdown file exists.

    We do minimal error checking because this code is used just as
    the launcher exits.
    """

    try:
        return str(job_id) in run_ssh_command(ssh_cmd, 'ls ~/.vnc/shutdown_%d*' % (job_id,), launcherMainFrame,ignore_errors=True)[0]
    except:
        return None

def remaining_visnode_walltime(launcherMainFrame):
    """
    Get the remaining walltime for the user's visnode job. We do
    minimal error checking because this code is used just as the user
    is exiting the launcher.
    """

    try:

        job_id = int(launcherMainFrame.loginThread.massiveJobNumber)

        if job_has_been_canceled(sshCmd.format(username=launcherMainFrame.massiveUsername,host=launcherMainFrame.massiveLoginHost), launcherMainFrame,job_id):
            return
        else:
            return seconds_to_hours_minutes(float(run_ssh_command(sshCmd.format(username=launcherMainFrame.massiveUsername,host=launcherMainFrame.massiveLoginHost), 'qstat -f %d | grep Remaining' % (job_id,), launcherMainFrame,ignore_errors=True)[0].split()[-1]))
    except:
        return

def deleteMassiveJobIfNecessary(launcherMainFrame,write_debug_log=False, update_status_bar=True, update_main_progress_bar=False, ignore_errors=False):
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
            run_ssh_command(sshCmd.format(username=launcherMainFrame.massiveUsername,host=launcherMainFrame.massiveLoginHost),
                            "qdel -a " + launcherMainFrame.loginThread.massiveJobNumber, launcherMainFrame,ignore_errors=ignore_errors)
            launcherMainFrame.loginThread.deletedMassiveJob = True
            if update_status_bar:
                wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
    elif launcherMainFrame.massiveTabSelected and launcherMainFrame.massivePersistentMode:
        if write_debug_log:
            logger_debug('Not running qdel for massive visnode because persistent mode is active.')

        wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, 'Checking remaining visnode walltime...')
        wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_WAIT))

        try:
            remaining_hours, remaining_minutes = remaining_visnode_walltime(launcherMainFrame)
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


def die_from_login_thread(launcherMainFrame,error_message, display_error_dialog=True, submit_log=False):
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

    dump_log(launcherMainFrame,submit_log=submit_log)

def die_from_main_frame(launcherMainFrame,error_message):
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
#        launcherMainFrame.loginThread.die_from_main_frame_dialog_completed = True

#    launcherMainFrame.loginThread.die_from_main_frame_dialog_completed = False
    wx.CallAfter(error_dialog)
 
    while not launcherMainFrame.loginThread.die_from_main_frame_dialog_completed:
        time.sleep(0.1)
 
    dump_log(launcherMainFrame,submit_log=True)
    os._exit(1)

def run_ssh_command(sshCmd,command,ignore_errors=False,log_output=True,callback=None):
    logger_debug('run_ssh_command: %s' % sshCmd+command)
    logger_debug('   called from %s:%d' % inspect.stack()[1][1:3])
    ssh_process=subprocess.Popen(sshCmd+command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,universal_newlines=True)

    #(stdout,stderr) = ssh_process.communicate(command)
    (stdout,stderr) = ssh_process.communicate()
    ssh_process.wait()
    if log_output:
        logger_debug('command stdout: %s' % stdout)
        logger_debug('command stderr: %s' % stderr)
    if not ignore_errors and len(stderr) > 0:
        error_message = 'Error running command: "%s" at line %d' % (command, inspect.stack()[1][2])
        logger_error('Nonempty stderr and ignore_errors == False; exiting the launcher with error dialog: ' + error_message)
        if (callback != None):
            callback(error_message)

    return stdout, stderr


global transport_logger
global logger
global logger_debug
global logger_error
global logger_warning
global logger_output
global logger_fh





def configureLogger(name):

    global transport_logger
    global logger
    global logger_debug
    global logger_error
    global logger_warning
    global logger_output
    global logger_fh
    
    # print "defining global logger"
    logger = logging.getLogger(name)
    # print logger
    logger.setLevel(logging.DEBUG)

    transport_logger = logging.getLogger('ssh.transport')
    transport_logger.setLevel(logging.DEBUG)

    log_format_string = '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'

    # Send all log messages to a string.
    logger_output = StringIO()
    string_handler = logging.StreamHandler(stream=logger_output)
    string_handler.setLevel(logging.DEBUG)
    string_handler.setFormatter(logging.Formatter(log_format_string))
    logger.addHandler(string_handler)
    transport_logger.addHandler(string_handler)

    # Finally, send all log messages to a log file.
    from os.path import expanduser, join
    logger_fh = logging.FileHandler(join(expanduser("~"), '.MASSIVE_Launcher_debug_log.txt'))
    logger_fh.setLevel(logging.DEBUG)
    logger_fh.setFormatter(logging.Formatter(log_format_string))
    logger.addHandler(logger_fh)
    transport_logger.addHandler(logger_fh)

# variable logger is a global
def logger_debug(message):
    if threading.current_thread().name=="MainThread":
        logger.debug(message)
    else:
        wx.CallAfter(logger.debug, message)
def logger_error(message):
    if threading.current_thread().name=="MainThread":
        logger.error(message)
    else:
        wx.CallAfter(logger.error, message)
def logger_warning(message):
    if threading.current_thread().name=="MainThread":
        logger.warning(message)
    else:
        wx.CallAfter(logger.warning, message)
