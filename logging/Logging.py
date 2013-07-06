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

class Logging():

    def __init__(self):
        self.transport_logger = None
        self.logger = None
        self.logger_debug = None
        self.logger_error = None
        self.logger_warning = None
        self.logger_output = None
        self.logger_fh = None

    def configureLogger(name):

        # print "defining global logger"
        self.logger = logging.getLogger(name)
        # print self.logger
        self.logger.setLevel(logging.DEBUG)

        self.transport_logger = logging.getLogger('ssh.transport')
        self.transport_logger.setLevel(logging.DEBUG)

        log_format_string = '%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'

        # Send all log messages to a string.
        logger_output = StringIO()
        string_handler = logging.StreamHandler(stream=logger_output)
        string_handler.setLevel(logging.DEBUG)
        string_handler.setFormatter(logging.Formatter(log_format_string))
        self.logger.addHandler(string_handler)
        self.transport_logger.addHandler(string_handler)

        # Finally, send all log messages to a log file.
        from os.path import expanduser, join
        self.logger_fh = logging.FileHandler(join(expanduser("~"), '.MASSIVE_Launcher_debug_log.txt'))
        self.logger_fh.setLevel(logging.DEBUG)
        self.logger_fh.setFormatter(logging.Formatter(log_format_string))
        self.logger.addHandler(self.logger_fh)
        self.transport_logger.addHandler(self.logger_fh)

    def logger_debug(self, message):
        if threading.current_thread().name=="MainThread":
            self.logger.debug(message)
        else:
            wx.CallAfter(self.logger.debug, message)
    def logger_error(self, message):
        if threading.current_thread().name=="MainThread":
            self.logger.error(message)
        else:
            wx.CallAfter(self.logger.error, message)
    def logger_warning(self, message):
        if threading.current_thread().name=="MainThread":
            self.logger.warning(message)
        else:
            wx.CallAfter(self.logger.warning, message)

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
            self.logger_debug('about to send debug log')

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

