import threading
import wx
import logging
from StringIO import StringIO
import HTMLParser
import os
import time
import subprocess
import sys
import requests
from SubmitDebugReportDialog import SubmitDebugReportDialog

class Logger():

    def __init__(self, name):
        self.name = name
        self.transport_logger = None
        self.loggerObject = None
        self.loggerOutput = None
        self.loggerFileHandler = None
        self.configureLogger()

    def setMassiveLauncherConfig(self, massiveLauncherConfig):
        self.massiveLauncherConfig = massiveLauncherConfig

    def setMassiveLauncherPreferencesFilePath(self, massiveLauncherPreferencesFilePath):
        self.massiveLauncherPreferencesFilePath = massiveLauncherPreferencesFilePath

    def sendLogMessagesToDebugWindowTextControl(self, logTextCtrl):
        # Send all log messages to the debug window, which may or may not be visible.
        log_window_handler = logging.StreamHandler(stream=logTextCtrl)
        log_window_handler.setLevel(logging.DEBUG)
        log_format_string = '%(asctime)s - %(name)s - %(module)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
        log_window_handler.setFormatter(logging.Formatter(log_format_string))
        self.loggerObject = logging.getLogger(self.name)
        self.loggerObject.addHandler(log_window_handler)
        # Don't send ssh.transport log messages to
        # the log window, because they won't be
        # wrapped in wx.CallAfter, unless we provide
        # our own customized version of the ssh module.
        #transport_logger.addHandler(log_window_handler)

    def configureLogger(self):
        # print "defining global logger"
        self.loggerObject = logging.getLogger(self.name)
        # print self.logger
        self.loggerObject.setLevel(logging.DEBUG)

        self.transport_logger = logging.getLogger('ssh.transport')
        self.transport_logger.setLevel(logging.DEBUG)

        log_format_string = '%(asctime)s - %(name)s - %(module)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'

        # Send all log messages to a string.
        self.loggerOutput = StringIO()
        string_handler = logging.StreamHandler(stream=self.loggerOutput)
        string_handler.setLevel(logging.DEBUG)
        string_handler.setFormatter(logging.Formatter(log_format_string))
        self.loggerObject.addHandler(string_handler)
        self.transport_logger.addHandler(string_handler)

        # Finally, send all log messages to a log file.
        from os.path import expanduser, join
        self.loggerFileHandler = logging.FileHandler(join(expanduser("~"), '.MASSIVE_Launcher_debug_log.txt'))
        self.loggerFileHandler.setLevel(logging.DEBUG)
        self.loggerFileHandler.setFormatter(logging.Formatter(log_format_string))
        self.loggerObject.addHandler(self.loggerFileHandler)
        self.transport_logger.addHandler(self.loggerFileHandler)

    def debug(self, message):
        if threading.current_thread().name=="MainThread":
            self.loggerObject.debug(message)
        else:
            wx.CallAfter(self.loggerObject.debug, message)

    def error(self, message):
        if threading.current_thread().name=="MainThread":
            self.loggerObject.error(message)
        else:
            wx.CallAfter(self.loggerObject.error, message)

    def warning(self, message):
        if threading.current_thread().name=="MainThread":
            self.loggerObject.warning(message)
        else:
            wx.CallAfter(self.loggerObject.warning, message)

    def dump_log(self, launcherMainFrame, submit_log=False, jobParams = None):
        # Commenting out logging.shutdown() for now,
        # because of concerns that logging could be used
        # after the call to logging.shutdown() which is
        # not allowed.
        # logging.shutdown()

        if launcherMainFrame==None:
            logger.debug("Logger.dump_log: Bailing out early, because launcherMainFrame is None.")
            return

        def showSubmitDebugLogDialog():
            dlg = SubmitDebugReportDialog(None,wx.ID_ANY,'MASSIVE/CVL Launcher',self.loggerOutput.getvalue(),self.massiveLauncherConfig,self.massiveLauncherPreferencesFilePath)
            try:
                try:
                    wx.EndBusyCursor()
                    stoppedBusyCursor = True
                except:
                    stoppedBusyCursor = False
                result = dlg.ShowModal()
                if stoppedBusyCursor:
                    wx.BeginBusyCursor()
                launcherMainFrame.submit_log = result == wx.ID_OK
                if launcherMainFrame.submit_log:
                    self.name = dlg.getName()
                    self.email = dlg.getEmail()
                    self.comments = dlg.getComments()
                    self.pleaseContactMe = dlg.getPleaseContactMe()
            finally:
                dlg.Destroy()
                launcherMainFrame.submitDebugLogDialogCompleted = True

        launcherMainFrame.submitDebugLogDialogCompleted = False

        if submit_log:
            if threading.current_thread().name=="MainThread":
                showSubmitDebugLogDialog()
            else:
                wx.CallAfter(showSubmitDebugLogDialog)
                while not launcherMainFrame.submitDebugLogDialogCompleted:
                    time.sleep(0.1)

        if submit_log and launcherMainFrame.submit_log:
            self.debug('about to send debug log')

            url       = 'https://cvl.massive.org.au/cgi-bin/log_drop.py'

            debugLog = "\n"
            if jobParams is not None:
                debugLog = debugLog + "Username: " + jobParams['username'] + "\n"
                debugLog = debugLog + "Config: " + jobParams['configName'] + "\n"
            debugLog = debugLog + "Name: " + self.name + "\n"
            debugLog = debugLog + "Email: " + self.email + "\n"
            debugLog = debugLog + "Contact me? "
            if self.pleaseContactMe:
                debugLog = debugLog + "Yes" + "\n"
            else:
                debugLog = debugLog + "No" + "\n"
            debugLog = debugLog + "Comments:\n\n" + self.comments + "\n\n"
            atLeastOneError = False
            for line in self.loggerOutput.getvalue().splitlines(True):
                if "ERROR" in line:
                    atLeastOneError = True
                    debugLog = debugLog + line
            if atLeastOneError:
                debugLog = debugLog + "\n"
            debugLog =  debugLog + self.loggerOutput.getvalue()
            file_info = {'logfile': debugLog}

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

logger = Logger("launcher")


