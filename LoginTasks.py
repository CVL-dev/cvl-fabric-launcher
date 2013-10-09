from threading import *
import cvlsshutils.sshKeyDist
from utilityFunctions import *
import traceback
import sys
import platform
import launcher_version_number
import shlex
import xmlrpclib
import re
import urllib2
import datetime
import os
if sys.platform.startswith("darwin"):
    from MacMessageDialog import LauncherMessageDialog
if sys.platform.startswith("win"):
    from WindowsMessageDialog import LauncherMessageDialog
from utilityFunctions import LAUNCHER_URL,TURBOVNC_BASE_URL
from logger.Logger import logger
import inspect

def showModal(dialog,loginprocess):
    try:
        wx.EndBusyCursor()
        stoppedBusyCursor = True
    except:
        stoppedBusyCursor = False
    dialog.ShowModal()
    if stoppedBusyCursor and not loginprocess.canceled() and not loginprocess._shutdown.is_set():
        wx.BeginBusyCursor()

class LoginProcess():
    """LoginProcess Class."""
            
    class runAsyncServerCommandThread(Thread):
        # Execute a command (might be start tunnel, or forward agent) wait for a regex to match and post an event. 
        # The command will continue to execute (e.g. the tunnel will remain open) but processing will continue on other tasks

        def __init__(self,loginprocess,cmdRegex,nextevent,errormessage):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.cmdRegex=cmdRegex
            self.nextevent=nextevent
            self.errormessage=errormessage
            self.process=None
    
        def stop(self):
            self._stop.set()
            if self.process!=None:
                self.process.stdin.write("exit\n")
                self.process.kill()
                self.process=None
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            if (self.cmdRegex.cmd==None):
                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextevent)
                return
            try:

                # Not 100% sure if this is necessary on Windows vs Linux. Seems to break the
                # Windows version of the launcher, but leaving in for Linux/OSX.
                logger.debug("runAsyncServerCommandThread: self.cmdRegex.cmd = " + self.cmdRegex.cmd)
                cmd=self.cmdRegex.cmd.format(**self.loginprocess.jobParams)
                logger.debug("runAsyncServerCommandThread: running %s"%cmd)
                if sys.platform.startswith("win"):
                    pass
                else:
                    cmd = shlex.split(cmd)
                
                self.process = subprocess.Popen(cmd, universal_newlines=True,shell=False,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, startupinfo=self.loginprocess.startupinfo, creationflags=self.loginprocess.creationflags)
                lastNonEmptyLine = None
                while (not self.stopped()):
                    self.process.poll()
                    if self.process.returncode is not None and (line is None or line==""):
                        exceptionMessage = "Process exited prematurely:\n\n" + " ".join(cmd)
                        if lastNonEmptyLine is not None:
                            exceptionMessage = exceptionMessage + "\n\n" + lastNonEmptyLine
                        if (not self.stopped()):
                            raise Exception(exceptionMessage)
                    time.sleep(0.1)
                    line = self.process.stdout.readline()
                    if (line != None):
                        logger.debug("runAsyncServerCommandThread: line: " + line)
                        if line!="":
                            lastNonEmptyLine = line
                        for regex in self.cmdRegex.regex:
                            match = re.search(regex.format(**self.loginprocess.jobParams),line)
                            if (match and not self.stopped() and not self.loginprocess.canceled() and not self.loginprocess._shutdown.is_set()):
                                logger.debug("runAsyncServerCommandThread: Found match for " + regex.format(**self.loginprocess.jobParams))
                                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextevent)
                    else:
                        logger.debug("runAsyncServerCommandThread: Didn't find match for " + regex.format(**self.loginprocess.jobParams))
                        if (not success and not self.loginprocess._shutdown.is_set()):
                            self.loginprocess.cancel(errormessage)
                    if self.stopped():
                        return
            except AttributeError:
                # Attribute errors occur if we try to read stdout after the process has completed.
                pass
            except Exception as e:
                error_message = "%s"%e
                logger.error('async server command failure: '+ error_message)
                self.loginprocess.cancel(error_message)
                return

    class runServerCommandThread(Thread):
        def __init__(self, loginprocess, cmdRegex, nextevent,errormessage, requireMatch=True):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.cmdRegex=cmdRegex
            self.nextevent=nextevent
            self.errormessage=errormessage
            self.requireMatch=requireMatch
            if (self.cmdRegex.regex==None or self.cmdRegex.regex[0]==None or self.cmdRegex.requireMatch==False):
                self.requireMatch=False
                self.loginprocess.matchlist=[]

            if self.cmdRegex.cmd is None:
                logger.debug("runServerCommandThread: WARNING: cmdRegex.cmd is None. Skipping server command.")
                try:
                    frameTuple = inspect.getouterframes(inspect.currentframe())[1]
                    logger.debug("runServerCommandThread: frameTuple:" + str(frameTuple))
                    logger.debug("runServerCommandThread: Calling function name: " + frameTuple[3])
                    logger.debug("runServerCommandThread: Calling code's line number in LoginTasks.py: " + str(frameTuple[2]))
                    logger.debug("runServerCommandThread: Line of code calling runServerCommandThread: " + "".join(frameTuple[4]))
                except:
                    logger.debug('runServerCommandThread exception: ' + str(traceback.format_exc()))
    
        def stop(self):
            if (self.cmdRegex.cmd!= None):
                logger.debug("Stopping the runServerCommandThread cmd %s"%self.cmdRegex.cmd.format(**self.loginprocess.jobParams))
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            if self.cmdRegex.cmd==None:
                if (not self.stopped() and self.nextevent!=None and not self.loginprocess.canceled() and not self.loginprocess._shutdown.is_set()):
                    wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextevent)
                return
            logger.debug("runServerCommandThread: self.cmd = " + self.cmdRegex.cmd)
            try:
                logger.debug("runServerCommandThread: self.cmd.format(**self.loginprocess.jobParams) = " + self.cmdRegex.cmd.format(**self.loginprocess.jobParams))
            except:
                logger.debug("runServerCommandThread: self.cmd.format(**self.loginprocess.jobParams) gives an exception. Why wasn't this picked up earlier?")
    
            self.loginprocess.matchlist=[]
            try:
                (stdout, stderr) = run_command(self.cmdRegex.getCmd(self.loginprocess.jobParams),ignore_errors=True, callback=self.loginprocess.cancel, startupinfo=self.loginprocess.startupinfo, creationflags=self.loginprocess.creationflags)
                logger.debug("runServerCommandThread: stderr = " + stderr)
                logger.debug("runServerCommandThread: stdout = " + stdout)
            except Exception as e:
                logger.error("could not format the command in runServerCommandThread %s)"%self.cmdRegex.cmd)
                logger.error("the error returned was %s"%e)
                if (not self.loginprocess._shutdown.is_set()):
                    self.loginprocess.cancel("An error occured. I'm sorry I can't give any more detailed information")
                return


            import itertools
            messages=parseMessages(self.loginprocess.siteConfig.messageRegexs,stdout,stderr)
            concat=""
            for key in messages.keys():
                concat=concat+messages[key]
            event=None
            oneMatchFound=False
            if (messages.has_key('error')):
                logger.error("canceling the loginprocess due to errors in the output of the command: %s %s"%(self.cmdRegex.cmd.format(**self.loginprocess.jobParams),messages))
                self.loginprocess.cancel(concat)
            elif (messages.has_key('warn') or messages.has_key('info')):
                def showMessageWindow(concat):
                    if sys.platform.startswith("linux"):
                        dlg=HelpDialog(self.loginprocess.notify_window, title="MASSIVE/CVL Launcher", name="MASSIVE/CVL Launcher",size=(680,290),style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)
                        panel=wx.Panel(dlg)
                        sizer=wx.BoxSizer()
                        panel.SetSizer(sizer)
                        text=wx.StaticText(panel,wx.ID_ANY,label=concat)
                        sizer.Add(text,0,wx.ALL,15)
                        dlg.addPanel(panel)
                    else:
                        dlg = LauncherMessageDialog(self.loginprocess.notify_window,title="MASSIVE/CVL Launcher",message=concat,helpEmailAddress=self.loginprocess.displayStrings.helpEmailAddress)
                    dlg.Show()
                wx.CallAfter(showMessageWindow,concat)
            for line  in itertools.chain(stdout.splitlines(False),stderr.splitlines(False)):
                for regex in self.cmdRegex.regex:
                    if (regex != None):
                        match=re.search(regex.format(**self.loginprocess.jobParams),line)
                        if (match):
                            oneMatchFound=True
                            logger.debug('runServerCommand matched the regex %s %s' % (regex.format(**self.loginprocess.jobParams),line))
                            self.loginprocess.jobParams.update(match.groupdict())
                            self.loginprocess.matchlist.append(match.groupdict())
                        else:
                            logger.debug('runServerCommand did not match the regex %s %s' % (regex.format(**self.loginprocess.jobParams),line))
            if (not oneMatchFound and self.requireMatch and not self.loginprocess._shutdown.is_set()):
                    for regex in self.cmdRegex.regex:
                        logger.error("no match found for the regex %s"%regex.format(**self.loginprocess.jobParams))
                    self.loginprocess.cancel(self.errormessage)
            if (not self.stopped() and self.nextevent!=None and not self.loginprocess.canceled() and not self.loginprocess._shutdown.is_set()):
                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextevent)

    class SimpleOptionDialog(wx.Dialog):
        def __init__(self, parent, id, title, text, okString, cancelString, OKCallback, CancelCallback):
            wx.Dialog.__init__(self, parent, id, title, style=wx.DEFAULT_DIALOG_STYLE ^ wx.RESIZE_BORDER | wx.STAY_ON_TOP)
            self.SetTitle(title)
            self.panel = wx.Panel(self,-1)
            self.label = wx.StaticText(self.panel, -1, text)
            self.Cancel = wx.Button(self.panel,-1,label=cancelString)
            self.OK = wx.Button(self.panel,-1,label=okString)
            self.OKCallback=OKCallback
            self.CancelCallback=CancelCallback

            self.sizer = wx.FlexGridSizer(3, 1)
            self.buttonRow = wx.FlexGridSizer(1, 2, hgap=10)
            self.sizer.Add(self.label)
            self.sizer.Add(wx.StaticText(self.panel, -1, ""))
            self.sizer.Add(self.buttonRow, flag=wx.ALIGN_RIGHT)
            self.buttonRow.Add(self.Cancel)
            self.buttonRow.Add(self.OK)

            self.OK.Bind(wx.EVT_BUTTON,self.onOK)
            self.Cancel.Bind(wx.EVT_BUTTON,self.onCancel)

            self.CenterOnParent()

            self.border = wx.BoxSizer()
            self.border.Add(self.sizer, 0, wx.ALL, 15)
            self.panel.SetSizerAndFit(self.border)
            self.Fit()
            self.password = None
        
        def onOK(self,event):
            self.Close()
            self.Destroy()
            logger.debug('SimpleOptionDialog, calling OK Callback')
            self.OKCallback()

        def onCancel(self,event):
            self.Close()
            self.Destroy()
            logger.debug('SimpleOptionDialog, calling Cancel Callback')
            self.CancelCallback()

    class startWebDavServerThread(Thread):
        def __init__(self,loginprocess,nextevent):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.nextevent=nextevent
    
        def stop(self):
            logger.debug("stopping the thread that starts the WebDAV server")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            import wsgidav.version
            import wsgidav.wsgidav_app
            from wsgidav.wsgidav_app import DEFAULT_CONFIG
            from wsgidav.server.run_server import SUPPORTED_SERVERS
            from wsgidav.server.run_server import _runCherryPy
            # lxml is not strictly required, but it makes WsgiDAV run faster.
            import lxml

            logger.debug("startWebDavServer: WsgiDAV version = " + wsgidav.version.__version__)

            wsgidavConfig = DEFAULT_CONFIG.copy()
            wsgidavConfig["host"] = "localhost"
            wsgidavConfig["port"] = int(self.loginprocess.jobParams['localWebDavPortNumber'])
            wsgidavConfig["root"] = os.path.expanduser('~')

            wsgidavConfig["provider_mapping"] = {}
            wsgidavConfig["user_mapping"] = {}

            def addShare(shareName, davProvider):
                wsgidavConfig["provider_mapping"][shareName] = davProvider

            def addUser(realmName, user, password, description, roles=[]):
                realmName = "/" + realmName.strip(r"\/")
                userDict = wsgidavConfig["user_mapping"].setdefault(realmName, {}).setdefault(user, {})
                userDict["password"] = password
                userDict["description"] = description
                userDict["roles"] = roles

            if (not self.loginprocess.jobParams.has_key('localUsername')):
                import getpass
                self.loginprocess.jobParams['localUsername'] = getpass.getuser()

            if (not self.loginprocess.jobParams.has_key('homeDirectoryWebDavShareName')):
                self.loginprocess.jobParams['homeDirectoryWebDavShareName'] = self.loginprocess.jobParams['localUsername']

            from wsgidav.fs_dav_provider import FilesystemProvider
            addShare(self.loginprocess.jobParams['homeDirectoryWebDavShareName'], FilesystemProvider(os.path.expanduser('~'), readonly=False))

            addUser(self.loginprocess.jobParams['homeDirectoryWebDavShareName'], self.loginprocess.jobParams['localUsername'], self.loginprocess.jobParams['vncPasswd'], "", roles=[])

            for k, v in wsgidavConfig.iteritems():
                logger.debug('startWebDavServer: wsgidavConfig properties: %s = %s' % (str(k), str(v),))
            wsgidavApp = wsgidav.wsgidav_app.WsgiDAVApp(wsgidavConfig)
            wsgidavServer = "cherrypy-bundled"
            # From def startWebDavServer(event):
            #        nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_WEBDAV_INTERMEDIATE_PORT,event.loginprocess)
            if (not self.stopped() and self.nextevent!=None and not self.loginprocess.canceled() and not self.loginprocess._shutdown.is_set()):
                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextevent)
            _runCherryPy(wsgidavApp, wsgidavConfig, wsgidavServer)


    class startVNCViewer(Thread):
        def __init__(self,loginprocess,nextevent):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.nextevent=nextevent
    
        def stop(self):
            logger.debug("stopping the thread that starts the VNC Viewer")
            self._stop.set()
            try:
                self.loginprocess.turboVncProcess.kill()
            except:
                pass
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            wx.CallAfter(self.loginprocess.progressDialog.Show, False)
            
            if (self.loginprocess.jobParams.has_key('vncPasswd')):

                try:
                    if sys.platform.startswith("win"):
                        vncCommandString = "\"{vnc}\" /user {username} /autopass /nounixlogin {vncOptionsString} localhost::{localPortNumber}".format(**self.loginprocess.jobParams)
                    else:
                        vncCommandString = "{vnc} -user {username} -autopass -nounixlogin {vncOptionsString} localhost::{localPortNumber}".format(**self.loginprocess.jobParams)
                    logger.debug('vncCommandString = ' + vncCommandString)
                    logger.debug('vncCommandString.format(**self.loginprocess.jobParams) = ' + vncCommandString.format(**self.loginprocess.jobParams))
                    self.loginprocess.turboVncStartTime = datetime.datetime.now()
                    logger.debug('turboVncStartTime = ' + str(self.loginprocess.turboVncStartTime))

                    self.loginprocess.turboVncProcess = subprocess.Popen(vncCommandString,
                        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                        universal_newlines=True,startupinfo=self.loginprocess.startupinfo,creationflags=self.loginprocess.creationflags)
                    self.loginprocess.vncviewerStarted.set()
                    self.loginprocess.turboVncStdout, self.loginprocess.turboVncStderr = self.loginprocess.turboVncProcess.communicate(input=self.loginprocess.jobParams['vncPasswd'] + "\n")

                    self.loginprocess.turboVncFinishTime = datetime.datetime.now()
                    logger.debug('turboVncFinishTime = ' + str(self.loginprocess.turboVncFinishTime))

                    self.loginprocess.turboVncElapsedTime = self.loginprocess.turboVncFinishTime - self.loginprocess.turboVncStartTime
                    self.loginprocess.turboVncElapsedTimeInSeconds = self.loginprocess.turboVncElapsedTime.total_seconds()

                    if self.loginprocess.turboVncStderr != None and self.loginprocess.turboVncStderr.strip()!="":
                        logger.debug('self.loginprocess.turboVncStderr: ' + self.loginprocess.turboVncStderr)

                    if self.loginprocess.turboVncProcess.returncode != 0:
                        logger.debug('self.loginprocess.turboVncStdout: ' + self.loginprocess.turboVncStdout)

                    if (not self.stopped() and not self.loginprocess.canceled() and not self.loginprocess._shutdown.is_set()):
                        wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextevent)

                except Exception as e:
                    self.loginprocess.cancel("Couldn't start the vnc viewer: %s"%e)
            else:
                    self.loginprocess.cancel("Couldn't start the vnc viewer. There was no password set")



    class runLoopServerCommandThread(Thread):
        def __init__(self,loginprocess,cmdRegex,nextEvent,errorstring,timeout=None):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.nextEvent = nextEvent
            self.cmdRegex=cmdRegex
            self.errorstring=errorstring
            self.timeout=timeout
            for k, v in self.__dict__.iteritems():
                logger.debug('runLoopServerCommandThread properties: %s = %s' % (str(k), str(v),))
    
        def stop(self):
            logger.debug("runLoopServerCommandThread: stopping")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            if self.cmdRegex.cmd==None:
                if (not self.stopped() and self.nextEvent!=None and not self.loginprocess.canceled() and not self.loginprocess._shutdown.is_set()):
                    wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextEvent)
                return
            notStarted=True
            tsleep=0
            sleepperiod=1
            # Make local copies, just because I tired of typing "self.loginprocess."
            jobParams=self.loginprocess.jobParams
            matched=False
            matchedDict={}
            for regex in self.cmdRegex.regex:
                matchedDict[regex]=False
            logger.debug("runLoopServerCommandThread: self.cmd = " + self.cmdRegex.cmd)
            logger.debug("runLoopServerCommandThread: self.cmd.format(**jobParams) = " + self.cmdRegex.cmd.format(**jobParams))
            while (not matched and not self.stopped()):
                tsleep+=sleepperiod
                if (not self.stopped()):
                    time.sleep(sleepperiod)
                try:
                    (stdout,stderr) = run_command(self.cmdRegex.getCmd(jobParams),ignore_errors=True, startupinfo=self.loginprocess.startupinfo, creationflags=self.loginprocess.creationflags)
                    logger.debug("runLoopServerCommandThread: stderr = " + stderr)
                    logger.debug("runLoopServerCommandThread: stdout = " + stdout)
                except KeyError as e:
                    self.loginprocess.cancel("Trying to run a command but I was missing a parameter %s"%(e))
                    return
                
            
                for line in stdout.splitlines(False):
                    for regexUnformatted in self.cmdRegex.regex:
                        if regexUnformatted != None:
                            if (not self.stopped()):
                                try:
                                    regex=regexUnformatted.format(**jobParams)
                                    logger.debug("searching the output of %s using regex %s"%(self.cmdRegex.cmd.format(**jobParams),regex))
                                except KeyError as e:
                                    logger.error("Trying to run %s, unable to formulate regex, missing parameter %s"%(regexUnformatted,e))
                                    self.loginprocess.cancel("Sorry, a catastropic error occured and I was unable to connect to your VNC session")
                                    return
                                match = re.search(regex,line)
                                if (match):
                                    logger.debug("runLoopServerCommandThread: Found match in line: " + line)
                                    logger.debug("runLoopServerCommandThread: match.groupdict() = " + str(match.groupdict()))
                                    self.loginprocess.jobParams.update(match.groupdict())
                                    self.loginprocess.matchlist.append(match.groupdict())
                                    matchedDict[regexUnformatted]=True
                                    matched=True
                                    for oneMatch in matchedDict.values():
                                        matched=(matched and oneMatch)
                if (not matched and self.timeout is not None and tsleep >= self.timeout):
                    logger.debug("runLoopServerCommandThread was called with a timeout of %d seconds, which has been reached. So giving up on matching and posting the next event." % (self.timeout))
                    wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextEvent)
                    return
                if (not matched and tsleep > 15):
                    sleepperiod=15
                if (not matched and tsleep > 15 and not self.loginprocess.canceled() and not self.loginprocess._shutdown.is_set()):
                    logger.error('runLoopServerCommandThread: no match, slept for more than 15 seconds, posting EVT_LOGINPROCESS_GET_ESTIMATED_START')
                    newevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_ESTIMATED_START,self.loginprocess)
                    wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),newevent)
                    sleepperiod=30
            if (not self.stopped() and not self.loginprocess.canceled() and not self.loginprocess._shutdown.is_set()):
                logger.error('runLoopServerCommandThread: not stopped, not canceled, so posting the next event')
                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextEvent)
        
    class CheckVNCVerThread(Thread):
        def __init__(self,loginprocess):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
    
        def stop(self):
            logger.debug("CheckVNCVerThread: stop called on CheckVNCVerThread") 
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()
                
        def getTurboVncVersionNumber_Windows(self):
            if sys.platform.startswith("win"):
                key = None
                queryResult = None
                foundTurboVncInRegistry = False
                vnc = r"C:\Program Files\TurboVNC\vncviewer.exe"

                import _winreg

                turboVncVersionNumber = None

                if not foundTurboVncInRegistry:
                    try:
                        # 64-bit Windows installation, 64-bit TurboVNC, HKEY_CURRENT_USER
                        key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC 64-bit_is1", 0,  _winreg.KEY_WOW64_64KEY | _winreg.KEY_READ)
                        queryResult = _winreg.QueryValueEx(key, "InstallLocation")
                        vnc = os.path.join(queryResult[0], "vncviewer.exe")
                        queryResult = _winreg.QueryValueEx(key, "DisplayVersion")
                        turboVncVersionNumber = queryResult[0]
                        foundTurboVncInRegistry = True
                    except:
                        foundTurboVncInRegistry = False
                if not foundTurboVncInRegistry:
                    try:
                        # 64-bit Windows installation, 64-bit TurboVNC, HKEY_LOCAL_MACHINE
                        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC 64-bit_is1", 0,  _winreg.KEY_WOW64_64KEY | _winreg.KEY_READ)
                        queryResult = _winreg.QueryValueEx(key, "InstallLocation")
                        vnc = os.path.join(queryResult[0], "vncviewer.exe")
                        queryResult = _winreg.QueryValueEx(key, "DisplayVersion")
                        turboVncVersionNumber = queryResult[0]
                        foundTurboVncInRegistry = True
                    except:
                        foundTurboVncInRegistry = False
                if not foundTurboVncInRegistry:
                    try:
                        # 32-bit Windows installation, 32-bit TurboVNC, HKEY_CURRENT_USER
                        key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_READ)
                        queryResult = _winreg.QueryValueEx(key, "InstallLocation")
                        vnc = os.path.join(queryResult[0], "vncviewer.exe")
                        queryResult = _winreg.QueryValueEx(key, "DisplayVersion")
                        turboVncVersionNumber = queryResult[0]
                        foundTurboVncInRegistry = True
                    except:
                        foundTurboVncInRegistry = False
                if not foundTurboVncInRegistry:
                    try:
                        # 32-bit Windows installation, 32-bit TurboVNC, HKEY_LOCAL_MACHINE
                        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_READ)
                        queryResult = _winreg.QueryValueEx(key, "InstallLocation")
                        vnc = os.path.join(queryResult[0], "vncviewer.exe")
                        queryResult = _winreg.QueryValueEx(key, "DisplayVersion")
                        turboVncVersionNumber = queryResult[0]
                        foundTurboVncInRegistry = True
                    except:
                        foundTurboVncInRegistry = False
                if not foundTurboVncInRegistry:
                    try:
                        # 64-bit Windows installation, 32-bit TurboVNC, HKEY_CURRENT_USER
                        key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_WOW64_32KEY | _winreg.KEY_READ)
                        queryResult = _winreg.QueryValueEx(key, "InstallLocation")
                        vnc = os.path.join(queryResult[0], "vncviewer.exe")
                        queryResult = _winreg.QueryValueEx(key, "DisplayVersion")
                        turboVncVersionNumber = queryResult[0]
                        foundTurboVncInRegistry = True
                    except:
                        foundTurboVncInRegistry = False
                if not foundTurboVncInRegistry:
                    try:
                        # 64-bit Windows installation, 32-bit TurboVNC, HKEY_LOCAL_MACHINE
                        key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_WOW64_32KEY | _winreg.KEY_READ)
                        queryResult = _winreg.QueryValueEx(key, "InstallLocation")
                        vnc = os.path.join(queryResult[0], "vncviewer.exe")
                        queryResult = _winreg.QueryValueEx(key, "DisplayVersion")
                        turboVncVersionNumber = queryResult[0]
                        foundTurboVncInRegistry = True
                    except:
                        foundTurboVncInRegistry = False

            logger.debug('CheckVNCVerThread: vnc = %s, turboVncVersionNumber = %s' % (str(vnc), str(turboVncVersionNumber),))

            return (vnc, turboVncVersionNumber)

        def getTurboVncVersionNumber(self,vnc):

            # Check TurboVNC flavour (X11 or Java) for non-Windows platforms:
            turboVncFlavourTestCommandString = "file /opt/TurboVNC/bin/vncviewer | grep -q ASCII"
            proc = subprocess.Popen(turboVncFlavourTestCommandString,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                universal_newlines=True,startupinfo=self.loginprocess.startupinfo, creationflags=self.loginprocess.creationflags)
            stdout, stderr = proc.communicate(input="\n")
            if stderr != None:
                logger.debug('turboVncFlavour stderr: ' + stderr)
            if proc.returncode==0:
                logger.debug("Java version of TurboVNC Viewer is installed.")
                turboVncFlavour = "Java"
            else:
                logger.debug("X11 version of TurboVNC Viewer is installed.")
                turboVncFlavour = "X11"
            
            self.turboVncVersionNumber = "0.0"

            if sys.platform.startswith("darwin") and turboVncFlavour=="Java":
                import plistlib
                turboVncInfoPlistFilePath = "/Applications/TurboVNC/TurboVNC Viewer.app/Contents/Info.plist"
                turboVncInfoPlist = plistlib.readPlist(turboVncInfoPlistFilePath)
                self.turboVncVersionNumber = turboVncInfoPlist['CFBundleShortVersionString']
                return (vnc,self.turboVncVersionNumber,turboVncFlavour)

            turboVncVersionNumberCommandString = vnc + " -help"
            proc = subprocess.Popen(turboVncVersionNumberCommandString,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                universal_newlines=True,startupinfo=self.loginprocess.startupinfo, creationflags=self.loginprocess.creationflags)
            turboVncStdout, turboVncStderr = proc.communicate(input="\n")
            if turboVncStderr != None:
                logger.debug("turboVncStderr: " + turboVncStderr)
            turboVncVersionNumberComponents = turboVncStdout.split(" v")
            turboVncVersionNumberComponents = turboVncVersionNumberComponents[1].split(" (build")
            turboVncVersionNumber = turboVncVersionNumberComponents[0].strip()

            return (vnc,turboVncVersionNumber,turboVncFlavour)

        def showTurboVncNotFoundMessageDialog(self,turboVncLatestVersion):

            turboVncNotFoundDialog = HelpDialog(self.loginprocess.notify_window, title="MASSIVE/CVL Launcher", name="MASSIVE/CVL Launcher",size=(680,290),style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)

            turboVncNotFoundPanel = wx.Panel(turboVncNotFoundDialog)
            turboVncNotFoundPanelSizer = wx.FlexGridSizer(rows=6, cols=1, vgap=5, hgap=5)
            turboVncNotFoundPanel.SetSizer(turboVncNotFoundPanelSizer)
            turboVncNotFoundTitleLabel = wx.StaticText(turboVncNotFoundPanel,
                label = "MASSIVE/CVL Launcher")
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetPointSize(14)
            font.SetWeight(wx.BOLD)
            turboVncNotFoundTitleLabel.SetFont(font)
            turboVncNotFoundPanelSizer.Add(turboVncNotFoundTitleLabel, flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=15)
            turboVncNotFoundTextLabel1 = wx.StaticText(turboVncNotFoundPanel,
                label = "TurboVNC (>= 1.1) was not found.\n\n" +
                        "Please download it from:\n")
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
            turboVncNotFoundPanelSizer.Add(turboVncNotFoundHyperlink, border=10, flag=wx.LEFT|wx.RIGHT|wx.BORDER)
            if sys.platform.startswith("darwin"):
                from distutils.version import StrictVersion
                if StrictVersion(platform.mac_ver()[0]) >= StrictVersion("10.8.0"):
                    messageLabel = wx.StaticText(turboVncNotFoundPanel,
                        label= "TurboVNC's Mac OS X installer is not digitally signed, \n" + \
                               "so you will need to right-click or control-click on it \n" + \
                               "to avoid being told that it can't be opened because it \n" + \
                               "is from an unidentified developer.")
                    font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                    if sys.platform.startswith("darwin"):
                        font.SetPointSize(11)
                    else:
                        font.SetPointSize(9)
                    messageLabel.SetFont(font)
                    turboVncNotFoundPanelSizer.Add(messageLabel, flag=wx.TOP,border=10)

                    appleGateKeeperSupportUrl = "http://support.apple.com/kb/HT5290"
                    appleGateKeeperSupportHyperlink = wx.HyperlinkCtrl(turboVncNotFoundPanel,
                        id = wx.ID_ANY,
                        label = appleGateKeeperSupportUrl,
                        url = appleGateKeeperSupportUrl)
                    font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                    if sys.platform.startswith("darwin"):
                        font.SetPointSize(11)
                    else:
                        font.SetPointSize(8)
                    appleGateKeeperSupportHyperlink.SetFont(font)
                    turboVncNotFoundPanelSizer.Add(appleGateKeeperSupportHyperlink, border=10, flag=wx.LEFT|wx.RIGHT|wx.BORDER)

            turboVncNotFoundPanelSizer.Add(wx.StaticText(turboVncNotFoundPanel))

            turboVncNotFoundDialog.addPanel(turboVncNotFoundPanel)
            turboVncNotFoundDialog.Centre()
            showModal(turboVncNotFoundDialog,self.loginprocess)

            self.loginprocess.cancel()
    
        def run(self):
            # Check for TurboVNC

            # Check for the latest version of TurboVNC on the launcher web page.
            # Don't bother to do this if we couldn't get to the Massive website earlier.
            # Somewhat strangely, if the earlier check to Massive failed due to a 404 (or similar)
            # then we get wxPython problems here:
            # Traceback (most recent call last):
            #   File "/opt/sw/32bit/debian/python/2.7.3/lib/python2.7/site-packages/wx-2.8-gtk2-unicode/wx/_core.py", line 14665, in <lambda>
            #     lambda event: event.callable(*event.args, **event.kw) )
            #   File "launcher.py", line 1549, in error_dialog
            #     "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            #   File "/opt/sw/32bit/debian/python/2.7.3/lib/python2.7/site-packages/wx-2.8-gtk2-unicode/wx/_windows.py", line 2914, in __init__
            #     _windows_.MessageDialog_swiginit(self,_windows_.new_MessageDialog(*args, **kwargs))
            # TypeError: in method 'new_MessageDialog', expected argument 1 of type 'wxWindow *'

            if self.loginprocess.contacted_massive_website:
                try:
                    myHtmlParser = MyHtmlParser('TurboVncLatestVersionNumber')
                    feed = urllib2.urlopen(LAUNCHER_URL, timeout=10)
                    html = feed.read()
                    myHtmlParser.feed(html)
                    myHtmlParser.close()
                except Exception as e:
                    logger.debug("Exception while checking TurboVNC version number: " + str(e))

                    def error_dialog():
                        dlg = wx.MessageDialog(self.loginprocess.notify_window, "Error: Unable to contact MASSIVE website to check the TurboVNC version number.\n\n" +
                                                "The launcher cannot continue.\n",
                                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                        showModal(dlg,self.loginprocess)
                        dlg.Destroy()
                        # If we can't contact the MASSIVE website, it's probably because
                        # there's no active network connection, so don't try to submit
                        # the log to cvl.massive.org.au
                        logger.dump_log(self.notify_window,submit_log=False)
                        sys.exit(1)
                    wx.CallAfter(error_dialog)

                turboVncLatestVersion = myHtmlParser.latestVersionNumber
            else:
                turboVncLatestVersion = ''
            turboVncLatestVersion = ''

            turboVncVersionNumber = None

            if sys.platform.startswith("win"):
                (vnc, turboVncVersionNumber) = self.getTurboVncVersionNumber_Windows()
                if os.path.exists(vnc):
                    if not turboVncVersionNumber.startswith("0.") and not turboVncVersionNumber.startswith("1.0"):
                        logger.debug("TurboVNC (>=1.1) was found in " + vnc)
                    else:
                        wx.CallAfter(self.showTurboVncNotFoundMessageDialog,turboVncLatestVersion)
                        return
                else:
                    wx.CallAfter(self.showTurboVncNotFoundMessageDialog,turboVncLatestVersion)
                    return
                turboVncFlavour = None
            else:
                vnc = "/opt/TurboVNC/bin/vncviewer"
                if os.path.exists(vnc):
                    (vnc,turboVncVersionNumber,turboVncFlavour) = self.getTurboVncVersionNumber(vnc)
                    if not turboVncVersionNumber.startswith("0.") and not turboVncVersionNumber.startswith("1.0"):
                        logger.debug("TurboVNC (>=1.1) was found in " + vnc)
                    else:
                        wx.CallAfter(self.showTurboVncNotFoundMessageDialog,turboVncLatestVersion)
                        return
                else:
                    wx.CallAfter(self.showTurboVncNotFoundMessageDialog,turboVncLatestVersion)
                    return

            if turboVncVersionNumber is None:
                def error_dialog():
                    dlg = wx.MessageDialog(self.loginprocess.notify_window, "Error: Could not determine TurboVNC version number.\n\n" +
                                            "The launcher cannot continue.\n",
                                    "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                    showModal(dlg,self.loginprocess)
                    dlg.Destroy()
                    logger.dump_log(self.loginprocess.notify_window)
                    sys.exit(1)

                if (self.loginprocess.progressDialog != None):
                    wx.CallAfter(self.loginprocess.progressDialog.Hide)
                    wx.CallAfter(self.loginprocess.progressDialog.Show, False)
                    wx.CallAfter(self.loginprocess.progressDialog.Destroy)
                    self.loginprocess.progressDialog = None

                wx.CallAfter(error_dialog)
                return


            logger.debug("TurboVNC viewer version number = " + turboVncVersionNumber)
            
            self.loginprocess.jobParams['vnc'] = vnc
            self.loginprocess.jobParams['turboVncFlavour'] = turboVncFlavour
            self.loginprocess.jobParams['vncOptionsString'] = self.loginprocess.buildVNCOptionsString()

            if (not self.stopped() and not self.loginprocess.canceled() and not self.loginprocess._shutdown.is_set()):
                event=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_DISTRIBUTE_KEY,self.loginprocess)
                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),event)

    class loginProcessEvent(wx.PyCommandEvent):
        def __init__(self,id,loginprocess,string=""):
            wx.PyCommandEvent.__init__(self,LoginProcess.myEVT_CUSTOM_LOGINPROCESS,id)
            self.loginprocess = loginprocess
            self.string = string

            for k, v in self.__dict__.iteritems():
                logger.debug('loginProcessEvent properties: %s = %s' % (str(k), str(v),))

        def checkVNCVer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_CHECK_VNC_VER):
                logger.debug("loginProcessEvent: caught EVT_LOGINPROCESS_CHECK_VNC_VER")
                wx.CallAfter(event.loginprocess.updateProgressDialog, 1,"Checking VNC version")
                t = LoginProcess.CheckVNCVerThread(event.loginprocess)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
                logger.debug("starting a thread to find the VNC Viewer")
            else:
                event.Skip()

        def distributeKey(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_DISTRIBUTE_KEY):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_DISTRIBUTE_KEY')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 2,"Configuring authorisation")
                event.loginprocess.skd = cvlsshutils.sshKeyDist.KeyDist(event.loginprocess.parentWindow,event.loginprocess.progressDialog,event.loginprocess.jobParams['username'],event.loginprocess.jobParams['loginHost'],event.loginprocess.jobParams['configName'],event.loginprocess.notify_window,event.loginprocess.keyModel,event.loginprocess.displayStrings,removeKeyOnExit=event.loginprocess.removeKeyOnExit,startupinfo=event.loginprocess.startupinfo,creationflags=event.loginprocess.creationflags)
                successevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_RUN_SANITY_CHECK,event.loginprocess)
                event.loginprocess.skd.distributeKey(callback_success=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),successevent),
                                                     callback_fail=event.loginprocess.cancel)
            else:
                event.Skip()

        def runSanityCheck(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RUN_SANITY_CHECK):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_RUN_SANITY_CHECK')
                event.loginprocess.updateProgressDialog( 8, "Running the sanity check script")
                nextevent = LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CHECK_RUNNING_SERVER,event.loginprocess)

                logger.debug('Running server-side sanity check.')
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.runSanityCheck,nextevent,'Error reported by server-side sanity check.')
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def checkRunningServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_CHECK_RUNNING_SERVER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_CHECK_RUNNING_SERVER')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 3,"Looking for an existing desktop to connect to")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_RECONNECT_DIALOG,event.loginprocess)
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.listAll,nextevent,"Error determining if you have any existing jobs running")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def showReconnectDialog(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RECONNECT_DIALOG):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_RECONNECT_DIALOG')
                if (len(event.loginprocess.matchlist)<1):
                    if (not event.loginprocess.canceled()):
                        wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_PROJECTS,event.loginprocess))
                    return
                event.loginprocess.job=event.loginprocess.matchlist[0]
                event.loginprocess.updateProgressDialog( 4,"Do you want to reconnect to an existing desktop?")
                ReconnectCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_WAIT_FOR_SERVER,event.loginprocess))
                NewDesktopCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER,event.loginprocess))
                timeRemaining=event.loginprocess.timeRemaining()
                logger.debug('loginProcessEvent: timeRemaining = ' + str(timeRemaining))

                if (timeRemaining != None):
                    hours, remainder = divmod(timeRemaining, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    if (hours > 1):
                        timestring = "%s hours and %s minutes"%(hours,minutes)
                    elif (hours) == 1:
                        timestring = "%s hour and %s minutes"%(hours,minutes)
                    elif (minutes > 1):
                        timestring = "%s minutes"%minutes
                    elif (minutes == 1):
                        timestring = "%s minute"%minutes
                    else:
                        timestring = "%s minutes"%minutes
                    dialog=LoginProcess.SimpleOptionDialog(event.loginprocess.notify_window,-1,"Reconnect to Existing Desktop",event.loginprocess.displayStrings.reconnectMessage.format(timestring=timestring),event.loginprocess.displayStrings.reconnectMessageNo,event.loginprocess.displayStrings.reconnectMessageYes,NewDesktopCallback,ReconnectCallback)
                else:
                    dialog=LoginProcess.SimpleOptionDialog(event.loginprocess.notify_window,-1,"Reconnect to Existing Desktop",event.loginprocess.displayStrings.reconnectMessage,event.loginprocess.displayStrings.reconnectMessageNo,event.loginprocess.displayStrings.reconnectMessageYes,NewDesktopCallback,ReconnectCallback)
                showModal(dialog,event.loginprocess)
            else:
                event.Skip()

        def getProjects(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_PROJECTS):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_PROJECTS')

                event.loginprocess.updateProgressDialog( 5,"Getting a list of your valid projects")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SELECT_PROJECT,event.loginprocess)
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.getProjects,nextevent,"I couldn't find any projects that you were a member of.")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def selectProject(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_SELECT_PROJECT):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_SELECT_PROJECT')

                event.loginprocess.updateProgressDialog( 5,"Getting a list of your valid projects")
                grouplist=[]
                groups=[]
                showDialog=False
                msg=""
                for match in event.loginprocess.matchlist:
                    grouplist = grouplist + match.values()
                    groups.append(match.values())
                
                logger.debug('selectProject: groups = ' + str(groups))

                if event.loginprocess.siteConfig.startServer.cmd!=None:
                    try:
                        event.loginprocess.siteConfig.startServer.cmd.format(**event.loginprocess.jobParams) # check if we actually need the project to format the startServerCmd
                        if (event.loginprocess.jobParams.has_key('project') and not (event.loginprocess.jobParams['project'] in grouplist)):
                            logger.debug("we have a value for project, but the user is not a member of that project")
                            msg='You don\'t appear to be a member of the project {project}.\n\nPlease select from one of the following:'.format(**event.loginprocess.jobParams)
                            event.loginprocess.jobParams.pop('project',None)
                            try: # check again if we really need the project field.
                                logger.debug("trying to format the startServerCmd")
                                event.loginprocess.siteConfig.startServer.cmd.format(**event.loginprocess.jobParams)
                                logger.debug("trying to format the startServerCmd, project is not necessary")
                                showDialog=False
                            except KeyError as e:
                                if ('project' in e.__str__()):
                                    logger.debug("trying to format the startServerCmd, project is necessary")
                                    showDialog=True
                                else:
                                    logger.debug("trying to format the startServerCmd, some other key is missing %s"%e)
                        elif (event.loginprocess.jobParams.has_key('project') and (event.loginprocess.jobParams['project'] in grouplist)):
                            logger.debug("we have a value for project, and the user is a member of that project")
                        else:
                            logger.debug("we don't have a value for project, but it isn't needed to start the VNC server")
                    except KeyError as e:
                        if e.args == 'project':
                            logger.debug("we need a value for project but it isn't set yet")
                            msg="Please select your project"
                            showDialog=True
                if (not showDialog):
                    logger.debug("don't need to show the dialog, either the project was set correctly, or it was not set, but also not required")
                else:
                    logger.debug("creating a list dialog for the user to select their project from")
                    #okCallback=lambda x: event.loginprocess.jobParams.update([('project',"%s"%x.GetText())])
                    def okCallback(listSelectionItem):
                        project = listSelectionItem.GetText()
                        event.loginprocess.jobParams.update([('project',"%s"%project)])
                        parentWindow = event.loginprocess.notify_window
                    cancelCallback=lambda x: event.loginprocess.cancel(x)
                    dlg=ListSelectionDialog(parent=event.loginprocess.notify_window, progressDialog=event.loginprocess.progressDialog, title='MASSIVE/CVL Launcher', headers=None, message=msg, noSelectionMessage="Please select a valid MASSIVE project from the list.", items=grouplist, okCallback=okCallback, cancelCallback = cancelCallback, style=wx.DEFAULT_DIALOG_STYLE, helpEmailAddress=event.loginprocess.displayStrings.helpEmailAddress)
                    showModal(dlg,event.loginprocess)
                if (not event.loginprocess.canceled()):
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_SERVER,event.loginprocess)
                    wx.PostEvent(event.loginprocess.notify_window,nextevent)
            else:
                event.Skip()

        def startServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_SERVER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_START_SERVER')
                event.loginprocess.updateProgressDialog( 5,"Starting a new desktop session")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_WAIT_FOR_SERVER,event.loginprocess)
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.startServer,nextevent,"Error starting the VNC server. This could occur")
                t.setDaemon(False)
                logger.debug('setting queued_job so that we can ask about qdel in the event of a cancel event')
                event.loginprocess.queued_job.set()
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def waitForServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_WAIT_FOR_SERVER):
                event.loginprocess.queued_job.set()
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_WAIT_FOR_SERVER')
                event.loginprocess.updateProgressDialog( 6,"Waiting for the VNC server to start")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_EXECUTION_HOST,event.loginprocess)
                t = LoginProcess.runLoopServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.running,nextevent,"")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def getEstimatedStart(event):
            # runLoopServerCommand can generate GET_ESTIMATED_START events. Most other threads can only post events that were given to them when they were initialised
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_ESTIMATED_START):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_ESTIMATED_START')
                if (event.loginprocess.siteConfig.showStart.cmd!=None):
                    logger.debug('loginProcessEvent: event.loginprocess.showStartCmd is not None, so posting EVT_LOGINPROCESS_SHOW_ESTIMATED_START')
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHOW_ESTIMATED_START,event.loginprocess)
                    t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.showStart,nextevent,"Error estimating the start time")
                    t.setDaemon(False)
                    t.start()
                    event.loginprocess.threads.append(t)
                else:
                    logger.debug('loginProcessEvent: event.loginprocess.showStartCmd is None, doing nothing')
            else:
                event.Skip()

        def showEstimatedStart(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_SHOW_ESTIMATED_START):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_SHOW_ESTIMATED_START')
                try:
                    string='Estimated start : {estimatedStart}'.format(**event.loginprocess.jobParams)
                    event.loginprocess.updateProgressDialog( 6, string )
                    logger.debug('loginProcessEvent: showEstimatedStart: ' + string)
                except Exception as e:
                    logger.debug('loginProcessEvent: showEstimatedStart: exception: ' + str(traceback.format_exc()))
                    pass
            else:
                event.Skip()


        def getExecutionHost(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_EXECUTION_HOST):
                event.loginprocess.started_job.set()
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_EXECUTION_HOST')
                event.loginprocess.updateProgressDialog( 6,"Getting execution host")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_VNCDISPLAY,event.loginprocess)
                logger.debug('loginProcessEvent: getExecutionHost: posting EVT_LOGINPROCESS_GET_VNCDISPLAY')
                t = LoginProcess.runLoopServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.execHost,nextevent,"")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def getVNCDisplay(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_VNCDISPLAY):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_VNCDISPLAY')
                event.loginprocess.updateProgressDialog( 6,"Getting the display number")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_TUNNEL,event.loginprocess)
                logger.debug('loginProcessEvent: getVNCDisplay: posting EVT_LOGINPROCESS_START_TUNNEL')
                t = LoginProcess.runLoopServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.vncDisplay,nextevent,"Unable to get the VNC display")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()
    
        def startTunnel(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_TUNNEL):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_START_TUNNEL')
                event.loginprocess.updateProgressDialog( 7,"Starting the tunnel")
                event.loginprocess.localPortNumber = "0" # Request ephemeral port.


                # Dodgyness ... I can't think of how to determine the remotePortNumber except by adding 5900 to the vnc Display number.
                # I can't think of an easy way to get the vncDisplay number when executing via qsub, but on MASSIVE it will always ben display :1
                if (not event.loginprocess.jobParams.has_key('localPortNumber')):
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.bind(('localhost', 0))
                    localPortNumber = sock.getsockname()[1]
                    sock.close()
                    event.loginprocess.localPortNumber = str(localPortNumber)
                    event.loginprocess.jobParams['localPortNumber'] = str(localPortNumber)
                    logger.debug('loginProcessEvent: startTunnel: set localPortNumber to ' + str(localPortNumber))

                if (not event.loginprocess.jobParams.has_key('vncDisplay')):
                    event.loginprocess.jobParams['vncDisplay']=":1"
                    logger.debug('loginProcessEvent: startTunnel: event.loginprocess.jobParams does not have vncDisplay, so setting to ":1"')

                event.loginprocess.jobParams['remotePortNumber'] = str(5900+int(event.loginprocess.jobParams['vncDisplay'].lstrip(':')))
                logger.debug('loginProcessEvent: startTunnel: set remotePortNumber to ' + str(event.loginprocess.jobParams['remotePortNumber']))


                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_FORWARD_AGENT,event.loginprocess)
                t = LoginProcess.runAsyncServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.tunnel,nextevent,"Unable to start the tunnel for some reason")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)

            else:
                event.Skip()

        def forwardAgent(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_FORWARD_AGENT):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_FORWARD_AGENT')
                event.loginprocess.updateProgressDialog( 8,"Setting up SSH Agent forwarding")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_OTP,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_GET_OTP')
                t = LoginProcess.runAsyncServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.agent,nextevent,"Unable to forward the ssh agent")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def getVNCPassword(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_OTP):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_OTP')
                event.loginprocess.updateProgressDialog( 9,"Getting the one-time password for the VNC server")
                #if (event.loginprocess.globalOptions.has_key('share_local_home_directory_on_remote_desktop') and event.loginprocess.globalOptions['share_local_home_directory_on_remote_desktop']):
                if event.loginprocess.shareHomeDir:
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_WEBDAV_SERVER,event.loginprocess)
                    logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_START_WEBDAV_SERVER')
                else:
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_VIEWER,event.loginprocess)
                    logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_START_VIEWER')
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.otp,nextevent,"Unable to determine the one-time password for the VNC session")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def startWebDavServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_WEBDAV_SERVER):
                logger.debug('LoginProcess.startWebDavServer: posting START_VIEWER while we also connect the webdav server')
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_VIEWER,event.loginprocess)
                wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),nextevent)
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_START_WEBDAV_SERVER')
                event.loginprocess.updateProgressDialog( 10,"Sharing your home directory with the remote server")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_DBUS_SESSION_ADDRESS,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_GET_DBUS_SESSION_ADDRESS')

                if (not event.loginprocess.jobParams.has_key('localWebDavPortNumber')):
                    event.loginprocess.jobParams['localWebDavPortNumber']="0"
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.bind(('localhost', 0))
                    localWebDavPortNumber = sock.getsockname()[1]
                    sock.close()
                    event.loginprocess.jobParams['localWebDavPortNumber'] = str(localWebDavPortNumber)
                    logger.debug('loginProcessEvent: startWebDavServer: set localWebDavPortNumber to ' + str(localWebDavPortNumber))

                t = LoginProcess.startWebDavServerThread(event.loginprocess,nextevent)
                t.setDaemon(True)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def getDbusSessionAddress(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_DBUS_SESSION_ADDRESS):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_DBUS_SESSION_ADDRESS')
                event.loginprocess.updateProgressDialog( 10,"Sharing your home directory with the remote server")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_WEBDAV_INTERMEDIATE_PORT,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_GET_WEBDAV_INTERMEDIATE_PORT')
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.dbusSessionBusAddress,nextevent,"Unable to determine the DBUS_SESSION_BUS_ADDRESS for the VNC session",requireMatch=False)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def getWebDavIntermediatePort(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_WEBDAV_INTERMEDIATE_PORT):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_WEBDAV_INTERMEDIATE_PORT')
                event.loginprocess.updateProgressDialog( 10,"Sharing your home directory with the remote server")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_WEBDAV_REMOTE_PORT,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_GET_WEBDAV_REMOTE_PORT')
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.webDavIntermediatePort,nextevent,"")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def getWebDavRemotePort(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_WEBDAV_REMOTE_PORT):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_WEBDAV_REMOTE_PORT')
                event.loginprocess.updateProgressDialog( 10,"Sharing your home directory with the remote server")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_WEBDAV_TUNNEL,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_START_WEBDAV_TUNNEL')
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.webDavRemotePort,nextevent,"")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def startWebDavTunnel(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_WEBDAV_TUNNEL):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_START_WEBDAV_TUNNEL')
                event.loginprocess.updateProgressDialog( 10,"Sharing your home directory with the remote server")

                #event.loginprocess.jobParams['remoteWebDavPortNumber'] = 8080 # FIXME: Hard-coded remote WebDAV port number for now!
                # remoteWebDavPortNumber is now determined using /usr/local/desktop/get_ephemeral_port_number.py on MASSIVE
                # and from /usr/local/bin/get_ephemeral_port_number.py on the CVL.
                #logger.debug('loginProcessEvent: startWebDavTunnel: set remoteWebDavPortNumber to ' + str(event.loginprocess.jobParams['remoteWebDavPortNumber']))

                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_OPEN_WEBDAV_SHARE_IN_REMOTE_FILE_BROWSER,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_OPEN_WEBDAV_SHARE_IN_REMOTE_FILE_BROWSER')

                t = LoginProcess.runAsyncServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.webDavTunnel,nextevent,"Unable to share your local home directory with the remote server")
                t.setDaemon(True)
                #t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def openWebDavShareInRemoteFileBrowser(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_OPEN_WEBDAV_SHARE_IN_REMOTE_FILE_BROWSER):
                if event.loginprocess.shareHomeDir:
                    logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_OPEN_WEBDAV_SHARE_IN_REMOTE_FILE_BROWSER')
                    event.loginprocess.updateProgressDialog( 10, "Sharing your home directory with the remote server")
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_WEBDAV_WINDOW_ID,event.loginprocess)
                    logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_GET_WEBDAV_WINDOW_ID')

                    if '{dbusSessionBusAddress}' in event.loginprocess.siteConfig.openWebDavShareInRemoteFileBrowser.cmd and 'dbusSessionBusAddress' not in event.loginprocess.jobParams.keys():
                        message = "Couldn't acquire DBUS_SESSION_BUS_ADDRESS, so unable to open shared home directory in remote file browser."
                        def showMessageWindow(message):
                            if sys.platform.startswith("linux"):
                                dlg=HelpDialog(event.loginprocess.notify_window, title="MASSIVE/CVL Launcher", name="MASSIVE/CVL Launcher",size=(680,290),style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)
                                panel=wx.Panel(dlg)
                                sizer=wx.BoxSizer()
                                panel.SetSizer(sizer)
                                text=wx.StaticText(panel,wx.ID_ANY,label=message)
                                sizer.Add(text,0,wx.ALL,15)
                                dlg.addPanel(panel)
                            else:
                                dlg = LauncherMessageDialog(event.loginprocess.notify_window,title="MASSIVE/CVL Launcher",message=message,helpEmailAddress=event.loginprocess.displayStrings.helpEmailAddress)
                            dlg.Show()
                        wx.CallAfter(showMessageWindow,message)
                        return

                    #t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.openWebDavShareInRemoteFileBrowser, None, '', requireMatch=True)
                    t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.openWebDavShareInRemoteFileBrowser, nextevent, '', requireMatch=True)
                    t.setDaemon(True)
                    t.start()
                    event.loginprocess.threads.append(t)
                    event.loginprocess.webdavMounted.set()
                    #wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),nextevent)

            else:
                event.Skip()

        def getWebDavWindowID(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_WEBDAV_WINDOW_ID):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_WEBDAV_WINDOW_ID')
                event.loginprocess.updateProgressDialog( 10,"Sharing your home directory with the remote server")

                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_DISPLAY_WEBDAV_ACCESS_INFO_IN_REMOTE_DIALOG,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_DISPLAY_WEBDAV_ACCESS_INFO_IN_REMOTE_DIALOG')

                t = LoginProcess.runLoopServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.webDavWindowID,nextevent,"Failed to determine WebDAV window ID.", timeout=5)
                t.setDaemon(True)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def displayWebDavInfoDialogOnRemoteDesktop(event):
            """
            This function may actually just write the WebDAV access info
            to a file, instead of displaying it in a dialog, depending on:
            siteConfig.displayWebDavInfoDialogOnRemoteDesktop
            """
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_DISPLAY_WEBDAV_ACCESS_INFO_IN_REMOTE_DIALOG):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_DISPLAY_WEBDAV_ACCESS_INFO_IN_REMOTE_DIALOG')
                event.loginprocess.updateProgressDialog( 10, "Sharing your home directory with the remote server")
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_START_VIEWER')

                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.displayWebDavInfoDialogOnRemoteDesktop, None, '', requireMatch=False)
                t.setDaemon(True)
                t.start()
                event.loginprocess.threads.append(t)

                #nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_VIEWER,event.loginprocess)
                #wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),nextevent)

            else:
                event.Skip()

        def closeWebDavWindow(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_CLOSE_WEBDAV_WINDOW):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_CLOSE_WEBDAV_WINDOW')
                if event.loginprocess.webdavMounted.isSet():
                    logger.debug('closeWebDavWindow: webdavMounted.isSet() is True.')
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_UNMOUNT_WEBDAV,event.loginprocess)
                    logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_UNMOUNT_WEBDAV')

                    if '{dbusSessionBusAddress}' in event.loginprocess.siteConfig.webDavCloseWindow.cmd and 'dbusSessionBusAddress' not in event.loginprocess.jobParams.keys():
                        event.loginprocess.webdavMounted.clear()
                        newevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,event.loginprocess)
                        logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_SHUTDOWN')
                        wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),newevent)
                        return

                    t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.webDavCloseWindow, nextevent, '', requireMatch=False)
                    t.setDaemon(True)
                    t.start()
                    event.loginprocess.threads.append(t)
                else:
                    logger.debug('closeWebDavWindow: webdavMounted.isSet() is False.')

                #wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),nextevent)

            else:
                event.Skip()

        def unmountWebDav(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_UNMOUNT_WEBDAV):
                if event.loginprocess.webdavMounted.isSet():
                    logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_UNMOUNT_WEBDAV')
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,event.loginprocess)
                    logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_SHUTDOWN')

                    if '{dbusSessionBusAddress}' in event.loginprocess.siteConfig.webDavUnmount.cmd and 'dbusSessionBusAddress' not in event.loginprocess.jobParams.keys():
                        event.loginprocess.webdavMounted.clear()
                        wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),nextevent)
                        return

                    t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.webDavUnmount, nextevent, '', requireMatch=False)
                    t.setDaemon(True)
                    t.start()
                    event.loginprocess.threads.append(t)
                    # Technically this is a bit early to clear the event, but I don't think it really matters. -- Chris.
                    event.loginprocess.webdavMounted.clear()
            else:
                event.Skip()

        def startViewer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_VIEWER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_START_VIEWER')
                event.loginprocess.updateProgressDialog( 9,"Starting the VNC viewer")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_STAT_RUNNING_JOB,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_STAT_RUNNING_JOB')
                try:
                    wx.EndBusyCursor()
                    stoppedBusyCursor = True
                except:
                    stoppedBusyCursor = False
                t = LoginProcess.startVNCViewer(event.loginprocess,nextevent)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()


        def cancel(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_CANCEL):
                #newevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,event.loginprocess)
                #logger.debug('loginProcessEvent: cancel: posting EVT_LOGINPROCESS_SHUTDOWN')
                #wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),newevent)
                if (event.string!=""):
                    if sys.platform.startswith("linux"):
                        dlg=HelpDialog(event.loginprocess.notify_window,title="MASSIVE/CVL Launcher", name="MASSIVE/CVL Launcher",size=(680,290),style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)
                        panel=wx.Panel(dlg)
                        sizer=wx.BoxSizer()
                        panel.SetSizer(sizer)
                        text=wx.StaticText(panel,wx.ID_ANY,label=event.string)
                        sizer.Add(text,0,wx.ALL,15)
                        dlg.addPanel(panel)
                    else:
                        dlg = LauncherMessageDialog(event.loginprocess.notify_window,title="MASSIVE/CVL Launcher",message=event.string,helpEmailAddress=event.loginprocess.displayStrings.helpEmailAddress)
                    showModal(dlg,event.loginprocess)
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_COMPLETE,event.loginprocess)
                event.loginprocess.shutdownThread = threading.Thread(target=event.loginprocess.shutdownReal,args=[nextevent])
                event.loginprocess.shutdownThread.start()
#                if hasattr(event.loginprocess, 'turboVncElapsedTimeInSeconds') and event.loginprocess.turboVncElapsedTimeInSeconds > 3:
#                    logger.debug("TurboVNC's elapsed time was greater than 3 seconds, " +
#                        "so presumably user stopped VNC session, so no need to ask " +
#                        "if they want to submit a debug log to cvl.massive.org.au")
#                    logger.dump_log(event.loginprocess.notify_window,submit_log=False)
#                else:
#                    logger.dump_log(event.loginprocess.notify_window,submit_log=True)
                if event.loginprocess.cancelCallback!=None:
                    event.loginprocess.cancelCallback(event.loginprocess.jobParams)
            else:
                event.Skip()

        def shutdown(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_SHUTDOWN):
                if not event.loginprocess._shutdown.is_set():
                    event.loginprocess._shutdown.set()
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_COMPLETE,event.loginprocess)
                    event.loginprocess.shutdownThread = threading.Thread(target=event.loginprocess.shutdownReal,args=[nextevent])
                    event.loginprocess.shutdownThread.start()
            else:
                event.Skip()

        def statRunningJob(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_STAT_RUNNING_JOB):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_STAT_RUNNING_JOB')
                if sys.platform.startswith("darwin"):
                    if hasattr(sys, 'frozen'):
                        applicationName = "MASSIVE Launcher"
                    else:
                        applicationName = "Python"
                    def grabFocusBackFromTurboVNC():
                        subprocess.Popen(['osascript', '-e',
                            "tell application \"System Events\"\r" +
                            "  set launcherApps to every process whose name contains \"" + applicationName + "\"\r" +
                            "  try\r" +
                            "    set launcherApp to item 1 of launcherApps\r" +
                            "    set frontmost of launcherApp to true\r" +
                            "    tell application \"" + applicationName + "\" to activate\r" +
                            "  end try\r" +
                            "end tell\r"])
                    logger.debug('loginProcessEvent: statRunningJob: attempting to grab focus back from TurboVNC')
                    grabFocusBackFromTurboVNC()
                wx.BeginBusyCursor()
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_QUESTION_KILL_SERVER,event.loginprocess)
                logger.debug('loginProcessEvent: statRunningJob: posting EVT_LOGINPROCESS_QUESTION_KILL_SERVER')
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.listAll,nextevent,"")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()



        def showKillServerDialog(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_QUESTION_KILL_SERVER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_QUESTION_KILL_SERVER')
                KillCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_KILL_SERVER,event.loginprocess))
                if event.loginprocess.webdavMounted.isSet():
                    if event.loginprocess.jobParams.has_key('webDavWindowID'):
                        logger.debug("showKillServerDialog: jobParams has 'webDavWindowID' key.")
                        nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CLOSE_WEBDAV_WINDOW,event.loginprocess)
                    else:
                        logger.debug("showKillServerDialog: jobParams doesn't have 'webDavWindowID' key.")
                        nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_UNMOUNT_WEBDAV,event.loginprocess)
                    persistCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),nextevent)
                else:
                    persistCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,event.loginprocess))
                dialog = None
                if (len(event.loginprocess.matchlist)>0):
                    logger.debug("showKillServerDialog: len(event.loginprocess.matchlist)>0")
                    event.loginprocess.job=event.loginprocess.matchlist[0]
                    timeRemaining=event.loginprocess.timeRemaining()
                    if (timeRemaining != None):
                        logger.debug("showKillServerDialog: timeRemaining != None")
                        hours, remainder = divmod(timeRemaining, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        if (hours > 1):
                            timestring = "%s hours and %s minutes"%(hours,minutes)
                        elif (hours) == 1:
                            timestring = "%s hour and %s minutes"%(hours,minutes)
                        elif (minutes > 1):
                            timestring = "%s minutes"%minutes
                        elif (minutes == 1):
                            timestring = "%s minute"%minutes
                        else:
                            timestring = "%s minutes"%minutes
                    else:
                        timestring=" unknown"


                    dialog=LoginProcess.SimpleOptionDialog(event.loginprocess.notify_window,-1,"Stop the Desktop?",event.loginprocess.displayStrings.persistentMessage.format(timestring=timestring),event.loginprocess.displayStrings.persistentMessageStop,event.loginprocess.displayStrings.persistentMessagePersist,KillCallback,persistCallback)
                if dialog:
                    logger.debug("showKillServerDialog: Showing the 'Stop the desktop' question dialog.")
                    showModal(dialog,event.loginprocess)
                else:
                    logger.debug("showKillServerDialog: Not showing the 'Stop the desktop' question dialog.")
                    persistCallback()
            else:
                event.Skip()



        def killServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER or event.GetId() == LoginProcess.EVT_LOGINPROCESS_KILL_SERVER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_RESTART_SERVER or we are EVT_LOGINPROCESS_KILL_SERVER')
                event.loginprocess.updateProgressDialog( 4,"Stopping the existing desktop session")
                if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER):
                    logger.debug("caught an EVT_LOGINPROCESS_RESTART_SERVER")
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_PROJECTS,event.loginprocess)
                    t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.stopForRestart,nextevent,"")
                else:
                    logger.debug("caught an EVT_LOGINPROCESS_KILL_SERVER")
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,event.loginprocess)
                    t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.siteConfig.stop,nextevent,"")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def normalTermination(event):
            # This event is generated if we shutdown the VNC server upon exit. Its basically a no-op, and moves onto processing the shutdown sequence of events
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_NORMAL_TERMINATION):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_NORMAL_TERMINATION')
                wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,event.loginprocess))
            else:
                event.Skip()

        def complete(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_COMPLETE):
                event.loginprocess.shutdownThread.join() #These events aren't processed until the thread is complete anyway.
                if (event.loginprocess.canceled()):
                    if event.loginprocess.skd!=None and event.loginprocess.skd.canceled():
                        logger.debug("LoginProcess.complete: sshKeyDist was canceled.")
                        logger.debug("Not asking user if they want to submit log, because they probably intentionally")
                        logger.debug("clicked a Cancel button, and then had to click an OK button to acknowledge that")
                        logger.debug("the Launcher can't continue without their passphrase, so I don't want the user")
                        logger.debug("to have to respond to a 3rd dialog (the Submit Debug Log dialog) too.")
                        logger.dump_log(event.loginprocess.notify_window,submit_log=False)
                    else:
                        if (event.loginprocess.userCanceled.isSet() and event.loginprocess.queued_job.isSet() and not event.loginprocess.started_job.isSet()):
                            logger.debug("LoginProcess.complete: User canceled login process between queueing the job and starting the job. System is probably busy. Not asking to submit a debug log .")
                            logger.dump_log(event.loginprocess.notify_window,submit_log=False)
                        else:
                            logger.debug("LoginProcess.complete: loginprocess was canceled, asking user if they want to submit the log")
                            logger.dump_log(event.loginprocess.notify_window,submit_log=True,jobParams=event.loginprocess.jobParams)
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_COMPLETE')
                try:
                    wx.EndBusyCursor()
                    stoppedBusyCursor = True
                except:
                    stoppedBusyCursor = False
                event.loginprocess._complete.set()
                if event.loginprocess.completeCallback!=None:
                    event.loginprocess.completeCallback(event.loginprocess.jobParams)
                if event.loginprocess.autoExit:
                    if hasattr(event.loginprocess, 'turboVncElapsedTimeInSeconds'):
                        if event.loginprocess.turboVncElapsedTimeInSeconds > 3:
                            os._exit(0)
              
                #wx.CallAfter(event.loginprocess.parentWindow.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))
            else:
                event.Skip()

    def shutdownReal(self,nextevent=None):
        # First stop all the threads, then (optionally) create a new thread to qdel the job. Finally shutdown the sshKeyDist object (which may shutdown the agent)
        logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_SHUTDOWN')
        for t in self.threads:
            try:
                logger.debug('loginProcessEvent: shutdown: attempting to stop thread ' + str(t))
                t.stop()
            except:
                logger.debug('exception: ' + str(traceback.format_exc()))
        # Throw away the thread references. We've done all we can to ask them to stop at this point.
        self.threads=[]
        logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_CANCEL')
        def qdelCallback():
            try:
                logger.debug('loginProcessEvent: cancel: attempting to format the stop command <%s> using parameters: %s' % (self.siteConfig.stop.cmd, self.jobParams,))
                logger.debug('loginProcessEvent: cancel: formatted stopCmd: ' + self.siteConfig.stop.cmd.format(**self.jobParams))
                self.siteConfig.stop.cmd.format(**self.jobParams)
                t = LoginProcess.runServerCommandThread(self,self.siteConfig.stop,None,"")
                t.setDaemon(True)
                t.start()
                t.join() # I don't like having a long wait on the event handler thread here, but we can't allow the sshKeyDist to be canceled before this thread is complete.
                #event.loginprocess.threads.append(t)
            except:
                logger.debug('loginProcessEvent: cancel: exception when trying to format the stop command: ' + str(traceback.format_exc()))
                pass
        if self.queued_job.isSet() and not self.started_job.isSet() and not self.userCanceled.isSet():
           qdelCallback()
        if self.queued_job.isSet() and self.started_job.isSet() and not self.vncviewerStarted.isSet():
           qdelCallback()
        if self.queued_job.isSet() and not self.started_job.isSet() and self.userCanceled.isSet():
            self.askUserIfTheyWantToDeleteQueuedJobCompleted = False
            def askUserIfTheyWantToDeleteQueuedJob():
                def noopCallback():
                    logger.debug("Leaving a job in the queue after cancel")

                dialog=LoginProcess.SimpleOptionDialog(self.notify_window,-1,"MASSIVE/CVL Launcher",self.displayStrings.qdelQueuedJob,self.displayStrings.qdelQueuedJobQdel,self.displayStrings.qdelQueuedJobNOOP,qdelCallback,noopCallback)
                logger.debug("threading.current_thread().name = " + threading.current_thread().name)
                showModal(dialog,self)
                self.askUserIfTheyWantToDeleteQueuedJobCompleted = True
            wx.CallAfter(askUserIfTheyWantToDeleteQueuedJob)
            while self.askUserIfTheyWantToDeleteQueuedJobCompleted==False:
                time.sleep(0.1)


        if (self.skd!=None): 
                #logger.debug('loginProcessEvent: cancel: calling skd.cancel()')
                #self.skd.shutdown()
                # Calling shutdown() doesn't seem to work - shutdownReal never gets called.
                logger.debug('loginProcessEvent: shutdownReal: calling skd.shutdownReal()')
                self.skd.shutdownReal()
        if (self.progressDialog != None):
            wx.CallAfter(self.progressDialog.Hide)
            wx.CallAfter(self.progressDialog.Show, False)
            wx.CallAfter(self.progressDialog.Destroy)
            self.progressDialog = None
        if nextevent!=None:
            wx.PostEvent(self.notify_window.GetEventHandler(),nextevent)


    def complete(self):
        return self._complete.isSet()
    myEVT_CUSTOM_LOGINPROCESS=None
    EVT_CUSTOM_LOGINPROCESS=None
    def __init__(self,parentWindow,jobParams,keyModel,siteConfig=None,displayStrings=None,autoExit=False,completeCallback=None,cancelCallback=None,globalOptions=None,contacted_massive_website=False,removeKeyOnExit=False,shareHomeDir=False,startupinfo=None,creationflags=0):
        self.parentWindow = parentWindow
        LoginProcess.myEVT_CUSTOM_LOGINPROCESS=wx.NewEventType()
        LoginProcess.EVT_CUSTOM_LOGINPROCESS=wx.PyEventBinder(self.myEVT_CUSTOM_LOGINPROCESS,1)
        self.keyModel=keyModel
        self.threads=[]
        self._canceled=threading.Event()
        self._shutdown=threading.Event()
        self.autoExit = autoExit
        #self.sshCmd = '{sshBinary} -A -T -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o StrictHostKeyChecking=yes -l {username} {loginHost} '
        self.sshTunnelProcess=None
        self.sshAgentProcess=None
        self.joblist=[]
        self.started_job=threading.Event()
        self.queued_job=threading.Event()
        self._complete=threading.Event()
        self.userCanceled=threading.Event()
        self.vncviewerStarted=threading.Event()
        self.webdavMounted=threading.Event()
        self.skd=None
        self.passwdPrompt=None
        self.completeCallback=completeCallback
        self.siteConfig = siteConfig
        self.jobParams = jobParams
        self.globalOptions=globalOptions
        self.contacted_massive_website=contacted_massive_website
        self.removeKeyOnExit=removeKeyOnExit
        self.notify_window=wx.Window(parent=self.parentWindow)
        self.displayStrings=displayStrings
        #self.notify_window.Hide()
        self.notify_window.Center()
        self.cancelCallback=cancelCallback
        self.shareHomeDir=shareHomeDir
        if (self.globalOptions.has_key('share_local_home_directory_on_remote_desktop') and self.globalOptions['share_local_home_directory_on_remote_desktop']):
            self.shareHomeDir=True
        try:
            s = 'Connecting to {configShortName}...'.format(**jobParams)
        except:
            s = 'Connecting...'
        import launcher_progress_dialog
        userCanAbort=True
        maximumProgressBarValue=10
        #self.progressDialog=launcher_progress_dialog.LauncherProgressDialog(self.parentWindow, wx.ID_ANY, s, "", maximumProgressBarValue, userCanAbort,self.cancel)
        self.progressDialog=launcher_progress_dialog.LauncherProgressDialog(self.notify_window, wx.ID_ANY, s, "", maximumProgressBarValue, userCanAbort,self.userCancel)

        self.startupinfo = startupinfo
        self.creationflags = creationflags

        update={}
        update['sshBinary']=self.keyModel.getsshBinary()
        update['launcher_version_number']=launcher_version_number.version_number
        update['loginHost']=self.siteConfig.loginHost
        self.jobParams.update(update)

        for k, v in self.__dict__.iteritems():
            logger.debug('loginProcessEvent properties: %s = %s' % (str(k), str(v),))

        if self.siteConfig is not None and self.siteConfig.__dict__ is not None:
            for k, v in self.siteConfig.__dict__.iteritems():
                logger.debug('loginProcessEvent.siteConfig properties: %s = %s' % (str(k), str(v),))

        LoginProcess.EVT_LOGINPROCESS_CHECK_VNC_VER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_DISTRIBUTE_KEY = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_CHECK_RUNNING_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_OTP = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_START_TUNNEL = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_RUN_VNCVIEWER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_ASK_TERMINATE_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_RECONNECT_DIALOG = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_KILL_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_START_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_WAIT_FOR_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_EXECUTION_HOST = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_VNCDISPLAY = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_NORMAL_TERMINATION = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_CANCEL = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_FORWARD_AGENT = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_START_VIEWER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_QUESTION_KILL_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_STAT_RUNNING_JOB = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_COMPLETE = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_CANCEL_COMPLETE = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SHUTDOWN = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SHOW_MESSAGE = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SHOW_WARNING = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SHOW_ERROR = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_ESTIMATED_START = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SHOW_ESTIMATED_START = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_PROJECTS = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SELECT_PROJECT = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_RUN_SANITY_CHECK = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_START_WEBDAV_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_DBUS_SESSION_ADDRESS = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_WEBDAV_INTERMEDIATE_PORT = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_WEBDAV_REMOTE_PORT = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_START_WEBDAV_TUNNEL = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_OPEN_WEBDAV_SHARE_IN_REMOTE_FILE_BROWSER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_WEBDAV_WINDOW_ID = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_DISPLAY_WEBDAV_ACCESS_INFO_IN_REMOTE_DIALOG = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_CLOSE_WEBDAV_WINDOW = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_UNMOUNT_WEBDAV = wx.NewId()

        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.cancel)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.distributeKey)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.checkRunningServer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.checkVNCVer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.showReconnectDialog)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.killServer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.startServer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.startTunnel)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.waitForServer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.getExecutionHost)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.getVNCDisplay)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.forwardAgent)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.getVNCPassword)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.startViewer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.showKillServerDialog)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.shutdown)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.normalTermination)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.complete)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.statRunningJob)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.getEstimatedStart)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.showEstimatedStart)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.getProjects)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.selectProject)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.runSanityCheck)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.startWebDavServer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.getDbusSessionAddress)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.getWebDavIntermediatePort)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.getWebDavRemotePort)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.startWebDavTunnel)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.openWebDavShareInRemoteFileBrowser)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.getWebDavWindowID)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.displayWebDavInfoDialogOnRemoteDesktop)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.closeWebDavWindow)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.unmountWebDav)

        #self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.showMessages)
    def setCallback(self,callback):
        self.completeCallback=callback
    def setCancelCallback(self,callback):
        self.cancelCallback=callback

    def timeRemaining(self):
        # The time fields returned by qstat can either contain HH:MM or --. -- occurs if the job has only just started etc
        # If -- is present, unpacking after split will fail, hence the try: except: combos.
        job=self.job
        if job != None:
            if (job.has_key('reqTime') and job.has_key('elapTime') and job.has_key('state')):
                if (job['state']=='R'):
                    try:
                        (rhours,rmin) = job['reqTime'].split(':')
                    except:
                        logger.debug('exception: ' + str(traceback.format_exc()))
                        return None
                    try:
                        if len(job['elapTime'].split(':'))==3:
                            (ehours,emin,esec) = job['elapTime'].split(':')
                        else:
                            (ehours,emin) = job['elapTime'].split(':')
                    except:
                        logger.debug('exception: ' + str(traceback.format_exc()))
                        ehours=0
                        emin=0
                    return (int(rhours)-int(ehours))*60*60 + (int(rmin)-int(emin))*60
                else:
                    try:
                        (rhours,rmin) = job['reqTime'].split(':')
                    except:
                        logger.debug('exception: ' + str(traceback.format_exc()))
                        return None
                    ehours=0
                    emin=0
                    return (int(rhours)-int(ehours))*60*60 + (int(rmin)-int(emin))*60
            else:
                return None
        else:
            return None
        
    def validateVncJobID(self):
        if (self.vncJobID != None and re.search("^[0-9]+\.\S+$",self.vncJobID)):
            return True
        else:
            return False

    def doLogin(self):
        #wx.CallAfter(self.parentWindow.SetCursor, wx.StockCursor(wx.CURSOR_WAIT))
        wx.BeginBusyCursor()
        event=self.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CHECK_VNC_VER,self)
        wx.PostEvent(self.notify_window.GetEventHandler(),event)

    def shutdown(self):
        print "posting shutdown event"
        event=self.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,self)
        wx.PostEvent(self.notify_window.GetEventHandler(),event)


    def getSharedSession(self,queue):
        from siteConfig import siteConfig
        from siteConfig import cmdRegEx
        print "in get shared session"
        t = LoginProcess.runServerCommandThread(self,self.siteConfig.otp,None,"Unable to determine the one-time password for the VNC session")
        t.start()
        print "waiting for the new otp"
        t.join()
        print "new otp generated"
        Visible={}
        Visible['usernamePanel']=True
        Visible['projectPanel']=False
        Visible['resourcePanel']=False
        Visible['resolutionPanel']=False
        Visible['cipherPanel']=False
        Visible['debugCheckBoxPanel']='Advanced'
        Visible['advancedCheckBoxPanel']=True
        Visible['optionsDialog']=False
        siteConfigDict={}
        siteConfigDict['messageRegexs']=[re.compile("^INFO:(?P<info>.*(?:\n|\r\n?))",re.MULTILINE),re.compile("^WARN:(?P<warn>.*(?:\n|\r\n?))",re.MULTILINE),re.compile("^ERROR:(?P<error>.*(?:\n|\r\n?))",re.MULTILINE)]
        siteConfigDict['loginHost']=self.siteConfig.loginHost
        siteConfigDict['execHost']=cmdRegEx('echo %s'%self.jobParams['execHost'],'(?P<execHost>.*)$',host='local')
        siteConfigDict['vncDisplay']=cmdRegEx('echo %s'%self.jobParams['vncDisplay'],'(?P<vncDisplay>.*)$',host='local')
        siteConfigDict['otp']= cmdRegEx('echo %s'%self.jobParams['vncPasswd'],'(?P<vncPasswd>.*)$',host='local')
        siteConfigDict['agent']=self.siteConfig.agent
        siteConfigDict['tunnel']=self.siteConfig.tunnel
        #newConfig = siteConfig(siteConfigDict,Visible)
        newConfig = siteConfig()
        newConfig.__dict__.update(siteConfigDict)
        newConfig.visibility=Visible
        queue.put(newConfig)
        #return newConfig
   
    def cancel(self,error=""):
        if (not self._canceled.isSet()):
            self._canceled.set()
            if error != None:
                logger.debug("LoginProcess.cancel: " + error)
            else:
                logger.debug("LoginProcess.cancel: no error specified")
            event=self.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CANCEL,self,error)
            wx.PostEvent(self.notify_window.GetEventHandler(),event)

    def userCancel(self,error=""):
        self.userCanceled.set()
        try:
            self.progressState=self.progressDialog.getProgress()
        except:
            self.progressState=0
        self.cancel(error)

    def canceled(self):
        return self._canceled.isSet()


    def updateProgressDialog(self, value, message):
        if self.progressDialog!=None:
            self.progressDialog.Update(value, message)
            self.shouldAbort = self.progressDialog.shouldAbort()

    def buildVNCOptionsString(self):
        if sys.platform.startswith("win"):
            optionPrefixCharacter = "/"
        else:
            optionPrefixCharacter = "-"
        vncOptionsString = ""

        # This is necessary to avoid confusion arising from connecting to localhost::[port] after creating SSH tunnel.
        # In this case, the X11 version of TurboVNC assumes that the client and server are the same computer:
        # "Same machine: preferring raw encoding"
        if not sys.platform.startswith("win"):
            if self.jobParams['turboVncFlavour'] == "X11":
                vncOptionsString = "-encodings \"tight copyrect\""
            else:
                vncOptionsString = "-encoding \"Tight\""

        if 'jpeg_compression' in self.globalOptions and self.globalOptions['jpeg_compression']==False:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "nojpeg"
        defaultJpegChrominanceSubsampling = "1x"
        if 'jpeg_chrominance_subsampling' in self.globalOptions and self.globalOptions['jpeg_chrominance_subsampling']!=defaultJpegChrominanceSubsampling:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "samp " + self.globalOptions['jpeg_chrominance_subsampling']
        defaultJpegImageQuality = "95"
        if 'jpeg_image_quality' in self.globalOptions and self.globalOptions['jpeg_image_quality']!=defaultJpegImageQuality:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "quality " + self.globalOptions['jpeg_image_quality']
        if 'zlib_compression_enabled' in self.globalOptions and self.globalOptions['zlib_compression_enabled']==True:
            if 'zlib_compression_level' in self.globalOptions:
                vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "compresslevel " + self.globalOptions['zlib_compression_level']
        if 'view_only' in self.globalOptions and self.globalOptions['view_only']==True:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "viewonly"
        if 'disable_clipboard_transfer' in self.globalOptions and self.globalOptions['disable_clipboard_transfer']==True:
            if sys.platform.startswith("win"):
                vncOptionsString = vncOptionsString + " /disableclipboard"
            #else:
                #vncOptionsString = vncOptionsString + " -noclipboardsend -noclipboardrecv"
        if sys.platform.startswith("win"):
            if 'scale' in self.globalOptions:
                if self.globalOptions['scale']=="Auto":
                    vncOptionsString = vncOptionsString + " /fitwindow"
                else:
                    vncOptionsString = vncOptionsString + " /scale " + self.globalOptions['scale']
            defaultSpanMode = 'automatic'
            if 'span' in self.globalOptions and self.globalOptions['span']!=defaultSpanMode:
                vncOptionsString = vncOptionsString + " /span " + self.globalOptions['span']
        if 'double_buffering' in self.globalOptions and self.globalOptions['double_buffering']==False:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "singlebuffer"
        if 'full_screen_mode' in self.globalOptions and self.globalOptions['full_screen_mode']==True:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "fullscreen"
        if 'deiconify_on_remote_bell_event' in self.globalOptions and self.globalOptions['deiconify_on_remote_bell_event']==False:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "noraiseonbeep"
        if sys.platform.startswith("win"):
            if 'emulate3' in self.globalOptions and self.globalOptions['emulate3']==True:
                vncOptionsString = vncOptionsString + " /emulate3"
            if 'swapmouse' in self.globalOptions and self.globalOptions['swapmouse']==True:
                vncOptionsString = vncOptionsString + " /swapmouse"
        if 'dont_show_remote_cursor' in self.globalOptions and self.globalOptions['dont_show_remote_cursor']==True:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "nocursorshape"
        elif 'let_remote_server_deal_with_mouse_cursor' in self.globalOptions and self.globalOptions['let_remote_server_deal_with_mouse_cursor']==True:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "x11cursor"
        if 'request_shared_session' in self.globalOptions and self.globalOptions['request_shared_session']==False:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "noshared"
        if sys.platform.startswith("win"):
            if 'toolbar' in self.globalOptions and self.globalOptions['toolbar']==False:
                vncOptionsString = vncOptionsString + " /notoolbar"
            if 'dotcursor' in self.globalOptions and self.globalOptions['dotcursor']==True:
                vncOptionsString = vncOptionsString + " /dotcursor"
            if 'smalldotcursor' in self.globalOptions and self.globalOptions['smalldotcursor']==True:
                vncOptionsString = vncOptionsString + " /smalldotcursor"
            if 'normalcursor' in self.globalOptions and self.globalOptions['normalcursor']==True:
                vncOptionsString = vncOptionsString + " /normalcursor"
            if 'nocursor' in self.globalOptions and self.globalOptions['nocursor']==True:
                vncOptionsString = vncOptionsString + " /nocursor"
            if 'writelog' in self.globalOptions and self.globalOptions['writelog']==True:
                if 'loglevel' in self.globalOptions and self.globalOptions['loglevel']==True:
                    vncOptionsString = vncOptionsString + " /loglevel " + self.globalOptions['loglevel']
                if 'logfile' in self.globalOptions:
                    vncOptionsString = vncOptionsString + " /logfile \"" + self.globalOptions['logfile'] + "\""
        return vncOptionsString
