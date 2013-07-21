from threading import *
import cvlsshutils.sshKeyDist
from utilityFunctions import *
import traceback
import sys
import launcher_version_number
import shlex
import xmlrpclib
import re
import urllib2
import datetime
import os

from logger.Logger import logger

class LoginProcess():
    """LoginProcess Class."""
            
    class runAsyncServerCommandThread(Thread):
        # Execute a command (might be start tunnel, or foward agent) wait for a regex to mactch and post an event. 
        # The command will continue to execute (e.g. the tunnel will remain open) but processing will continue on other tasks

        def __init__(self,loginprocess,cmd,regex,nextevent,errormessage):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.cmd=cmd
            self.regex=regex
            self.nextevent=nextevent
            self.errormessage=errormessage
    
        def stop(self):
            self.process.stdin.write("exit\n")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            try:

                # Not 100% sure if this is necessary on Windows vs Linux. Seems to break the
                # Windows version of the launcher, but leaving in for Linux/OSX.
                cmd=self.cmd.format(**self.loginprocess.jobParams)
                logger.debug("running %s"%cmd)
                if sys.platform.startswith("win"):
                    pass
                else:
                    cmd = shlex.split(cmd)
                
                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                except:
                    # On non-Windows systems the previous block will die with 
                    # "AttributeError: 'module' object has no attribute 'STARTUPINFO'" even though
                    # the code is inside the 'if' block, hence the use of a dodgy try/except block.
                    startupinfo = None

                self.process = subprocess.Popen(cmd, universal_newlines=True,shell=False,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, startupinfo=startupinfo)
                while (not self.stopped()):
                    time.sleep(0.1)
                    line = self.process.stdout.readline()
                    if (line != None):
                        match = re.search(self.regex.format(**self.loginprocess.jobParams),line)
                        if (match and not self.stopped() and not self.loginprocess.canceled()):
                            wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextevent)
                    else:
                        if (not success):
                            self.loginprocess.cancel(errormessage)
                    if self.stopped():
                        return
            except Exception as e:
                error_message = "%s"%e
                logger.error('async server command failure: '+ error_message)
                self.loginprocess.cancel(error_message)
                return

    class runServerCommandThread(Thread):
        def __init__(self, loginprocess, cmd, regex, nextevent,errormessage, requireMatch=True, sanityCheckHack=False):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.cmd=cmd
            if (not isinstance(regex,list)):
                self.regex=[regex]
            else:
                self.regex=regex
            self.nextevent=nextevent
            self.errormessage=errormessage
            self.requireMatch=requireMatch
            self.sanityCheckHack = sanityCheckHack
    
        def stop(self):
            logger.debug("stoping the runServerCommandThread cmd %s"%self.cmd.format(**self.loginprocess.jobParams))
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            logger.debug("runServerCommandThread: self.cmd = " + self.cmd)
            logger.debug("runServerCommandThread: self.cmd.format(**self.loginprocess.jobParams) = " + self.cmd.format(**self.loginprocess.jobParams))
            sshCmd = self.loginprocess.sshCmd
            self.loginprocess.matchlist=[]
            try:
                (stdout, stderr) = run_ssh_command(sshCmd.format(**self.loginprocess.jobParams), self.cmd.format(**self.loginprocess.jobParams),ignore_errors=True, callback=self.loginprocess.cancel)
                logger.debug("runServerCommandThread: stderr = " + stderr)
                logger.debug("runServerCommandThread: stdout = " + stdout)
            except Exception as e:
                logger.error("could not format the command in runServerCommandThread %s)"%self.cmd)
                self.loginprocess.cancel("An error occured. I'm sorry I can't give any more detailed information")
                return

            if self.sanityCheckHack:
                if 'REQUEST_VISNODE_ERROR' in stdout:
                    logger.debug('We saw REQUEST_VISNODE_ERROR so we are quitting.')
                    self.loginprocess.cancel('Server-side sanity check reported an error.') # FIXME give detail?
                    return

            import itertools
            messages=parseMessages(self.loginprocess.messageRegexs,stdout,stderr)
            concat=""
            for key in messages.keys():
                concat=concat+messages[key]
            event=None
            oneMatchFound=False
            if (messages.has_key('error')):
                logger.error("canceling the loginprocess due to errors in the output of the command: %s %s"%(self.cmd.format(**self.loginprocess.jobParams),messages))
                self.loginprocess.cancel(concat)
            elif (messages.has_key('warn') or messages.has_key('info')):
                dlg=HelpDialog(self.loginprocess.notify_window, title="MASSIVE/CVL Launcher", name="MASSIVE/CVL Launcher",size=(680,290),style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)
                panel=wx.Panel(dlg)
                sizer=wx.BoxSizer()
                panel.SetSizer(sizer)
                text=wx.StaticText(panel,wx.ID_ANY,label=concat)
                sizer.Add(text,0,wx.ALL,15)
                dlg.addPanel(panel)
                wx.CallAfter(dlg.Show)
            for line  in itertools.chain(stdout.splitlines(False),stderr.splitlines(False)):
                for regex in self.regex:
                    if (regex != None):
                        match=re.search(regex.format(**self.loginprocess.jobParams),line)
                        if (match):
                            oneMatchFound=True
                            logger.debug('runServerCommand matched the regex %s %s' % (regex.format(**self.loginprocess.jobParams),line))
                            self.loginprocess.jobParams.update(match.groupdict())
                            self.loginprocess.matchlist.append(match.groupdict())
                        else:
                            logger.debug('runServerCommand did not match the regex %s %s' % (regex.format(**self.loginprocess.jobParams),line))
            if (not oneMatchFound and self.requireMatch):
                    for regex in self.regex:
                        logger.error("no match found for the regex %s"%regex.format(**self.loginprocess.jobParams))
                    self.loginprocess.cancel(self.errormessage)
            if (not self.stopped() and self.nextevent!=None and not self.loginprocess.canceled()):
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
            self.OKCallback()

        def onCancel(self,event):
            self.Close()
            self.Destroy()
            self.CancelCallback()

    class startVNCViewer(Thread):
        def __init__(self,loginprocess,nextevent):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.nextevent=nextevent
    
        def stop(self):
            logger.debug("stopping the thread that starts the VNC Viewer")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            wx.CallAfter(self.loginprocess.notify_window.progressDialog.Show, False)
            
            if (self.loginprocess.jobParams.has_key('vncPasswd')):

                try:
                    if sys.platform.startswith("win"):
                        vncCommandString = "\"{vnc}\" /user {username} /autopass /nounixlogin {vncOptionsString} localhost::{localPortNumber}".format(**self.loginprocess.jobParams)
                    else:
                        vncCommandString = "{vnc} -user {username} -autopass -nounixlogin {vncOptionsString} localhost::{localPortNumber}".format(**self.loginprocess.jobParams)
                    self.loginprocess.turboVncStartTime = datetime.datetime.now()
                    logger.debug('turboVncStartTime = ' + str(self.loginprocess.turboVncStartTime))

                    self.loginprocess.turboVncProcess = subprocess.Popen(vncCommandString,
                        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                        universal_newlines=True)
                    self.loginprocess.turboVncStdout, self.loginprocess.turboVncStderr = self.loginprocess.turboVncProcess.communicate(input=self.loginprocess.jobParams['vncPasswd'] + "\n")

                    self.loginprocess.turboVncFinishTime = datetime.datetime.now()
                    logger.debug('turboVncFinishTime = ' + str(self.loginprocess.turboVncFinishTime))

                    self.loginprocess.turboVncElapsedTime = self.loginprocess.turboVncFinishTime - self.loginprocess.turboVncStartTime
                    self.loginprocess.turboVncElapsedTimeInSeconds = self.loginprocess.turboVncElapsedTime.total_seconds()

                    if self.loginprocess.turboVncStderr != None and self.loginprocess.turboVncStderr.strip()!="":
                        logger.debug('self.loginprocess.turboVncStderr: ' + self.loginprocess.turboVncStderr)

                    if self.loginprocess.turboVncProcess.returncode != 0:
                        logger.debug('self.loginprocess.turboVncStdout: ' + self.loginprocess.turboVncStdout)

                    if (not self.stopped() and not self.loginprocess.canceled()):
                        wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),self.nextevent)

                except Exception as e:
                    self.loginprocess.cancel("Couldn't start the vnc viewer: %s"%e)
            else:
                    self.loginprocess.cancel("Couldn't start the vnc viewer. There was no password set")



    class runLoopServerCommandThread(Thread):
        def __init__(self,loginprocess,cmd,regex,nextEvent,errorstring):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.nextEvent = nextEvent
            self.cmd=cmd
            if (not isinstance(regex,list)):
                self.regex=[regex]
            else:
                self.regex=regex
            self.errorstring=errorstring
            for k, v in self.__dict__.iteritems():
                logger.debug('runLoopServerCommandThread properties: %s = %s' % (str(k), str(v),))
    
        def stop(self):
            logger.debug("runLoopServerCommandThread: stopping the thread that determines the execution host")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            notStarted=True
            tsleep=0
            sleepperiod=1
            # Make local copies, just because I tired of typing "self.loginprocess."
            sshCmd = self.loginprocess.sshCmd
            jobParams=self.loginprocess.jobParams
            matched=False
            matchedDict={}
            for regex in self.regex:
                matchedDict[regex]=False
            logger.debug("runLoopServerCommandThread: self.cmd = " + self.cmd)
            logger.debug("runLoopServerCommandThread: self.cmd.format(**jobParams) = " + self.cmd.format(**jobParams))
            while (not matched and not self.stopped()):
                tsleep+=sleepperiod
                if (not self.stopped()):
                    time.sleep(sleepperiod)
                try:
                    (stdout,stderr) = run_ssh_command(sshCmd.format(**jobParams),self.cmd.format(**jobParams),ignore_errors=True)
                    logger.debug("runLoopServerCommandThread: stderr = " + stderr)
                    logger.debug("runLoopServerCommandThread: stdout = " + stdout)
                except KeyError as e:
                    self.loginprocess.cancel("Trying to run %s\n%s but I was missing a parameter %s"%(sshCmd,self.cmd,e))
                    return
                
            
                for line in stdout.splitlines(False):
                    for regexUnformatted in self.regex:
                        if regexUnformatted != None:
                            if (not self.stopped()):
                                try:
                                    regex=regexUnformatted.format(**jobParams)
                                    logger.debug("searching the output of %s using regex %s"%(self.cmd.format(**jobParams),regex))
                                except KeyError as e:
                                    logger.error("Trying to run %s, unable to formulate regex, missing parameter %s"%(regexUnformatted,e))
                                    self.loginprocess.cancel("Sorry, a catastropic error occured and I was unable to connect to your VNC session")
                                    return
                                match = re.search(regex,line)
                                if (match):
                                    self.loginprocess.jobParams.update(match.groupdict())
                                    self.loginprocess.matchlist.append(match.groupdict())
                                    matchedDict[regexUnformatted]=True
                                    matched=True
                                    for oneMatch in matchedDict.values():
                                        matched=(matched and oneMatch)
                if (not matched and tsleep > 15):
                    sleepperiod=15
                if (not matched and tsleep > 15 and not self.loginprocess.canceled()):
                    logger.error('runLoopServerCommandThread: no match, slept for more than 15 seconds, posting EVT_LOGINPROCESS_GET_ESTIMATED_START')
                    newevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_ESTIMATED_START,self.loginprocess)
                    wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),newevent)
                    sleepperiod=30
            if (not self.stopped() and not self.loginprocess.canceled()):
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
                        #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                        #wx.CallAfter(sys.stdout.write, traceback.format_exc())
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
                        #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                        #wx.CallAfter(sys.stdout.write, traceback.format_exc())
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
                        #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                        #wx.CallAfter(sys.stdout.write, traceback.format_exc())
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
                        #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                        #wx.CallAfter(sys.stdout.write, traceback.format_exc())
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
                        #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                        #wx.CallAfter(sys.stdout.write, traceback.format_exc())
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
                        #wx.CallAfter(sys.stdout.write, "MASSIVE/CVL Launcher v" + launcher_version_number.version_number + "\n")
                        #wx.CallAfter(sys.stdout.write, traceback.format_exc())

            logger.debug('CheckVNCVerThread: vnc = %s, turboVncVersionNumber = %s' % (str(vnc), str(turboVncVersionNumber),))

            return (vnc, turboVncVersionNumber)

        def getTurboVncVersionNumber(self,vnc):
            self.turboVncVersionNumber = "0.0"

            turboVncVersionNumberCommandString = vnc + " -help"
            proc = subprocess.Popen(turboVncVersionNumberCommandString,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                universal_newlines=True)
            turboVncStdout, turboVncStderr = proc.communicate(input="\n")
            if turboVncStderr != None:
                logger.debug("turboVncStderr: " + turboVncStderr)
            turboVncVersionNumberComponents = turboVncStdout.split(" v")
            turboVncVersionNumberComponents = turboVncVersionNumberComponents[1].split(" (build")
            turboVncVersionNumber = turboVncVersionNumberComponents[0].strip()

            # Check TurboVNC flavour (X11 or Java) for non-Windows platforms:
            turboVncFlavourTestCommandString = "file /opt/TurboVNC/bin/vncviewer | grep -q ASCII"
            proc = subprocess.Popen(turboVncFlavourTestCommandString,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                universal_newlines=True)
            stdout, stderr = proc.communicate(input="\n")
            if stderr != None:
                logger.debug('turboVncFlavour stderr: ' + stderr)
            if proc.returncode==0:
                logger.debug("Java version of TurboVNC Viewer is installed.")
                turboVncFlavour = "Java"
            else:
                logger.debug("X11 version of TurboVNC Viewer is installed.")
                turboVncFlavour = "X11"
            
            return (vnc,turboVncVersionNumber,turboVncFlavour)

        def showTurboVncNotFoundMessageDialog(self,turboVncLatestVersion):

            turboVncNotFoundDialog = HelpDialog(self.loginprocess.notify_window, title="MASSIVE/CVL Launcher", name="MASSIVE/CVL Launcher",size=(680,290),style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)

            turboVncNotFoundPanel = wx.Panel(turboVncNotFoundDialog)
            turboVncNotFoundPanelSizer = wx.FlexGridSizer(rows=4, cols=1, vgap=5, hgap=5)
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
            turboVncNotFoundPanelSizer.Add(wx.StaticText(turboVncNotFoundPanel))

            turboVncNotFoundDialog.addPanel(turboVncNotFoundPanel)
            turboVncNotFoundDialog.Centre()
            turboVncNotFoundDialog.ShowModal()

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

            if self.loginprocess.notify_window.contacted_massive_website:
                try:
                    myHtmlParser = MyHtmlParser('TurboVncLatestVersionNumber')
                    feed = urllib2.urlopen(LAUNCHER_URL, timeout=10)
                    html = feed.read()
                    myHtmlParser.feed(html)
                    myHtmlParser.close()
                except Exception as e:
                    logger.debug("Exception while checking TurboVNC version number: " + str(e))

                    def error_dialog():
                        dlg = wx.MessageDialog(self.notify_window, "Error: Unable to contact MASSIVE website to check the TurboVNC version number.\n\n" +
                                                "The launcher cannot continue.\n",
                                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                        dlg.ShowModal()
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
                    dlg.ShowModal()
                    dlg.Destroy()
                    logger.dump_log(self.loginprocess.notify_window)
                    sys.exit(1)

                if (self.loginprocess.notify_window.progressDialog != None):
                    wx.CallAfter(self.loginprocess.notify_window.progressDialog.Hide)
                    wx.CallAfter(self.loginprocess.notify_window.progressDialog.Show, False)
                    wx.CallAfter(self.loginprocess.notify_window.progressDialog.Destroy)
                    self.loginprocess.notify_window.progressDialog = None

                wx.CallAfter(error_dialog)
                return


            logger.debug("TurboVNC viewer version number = " + turboVncVersionNumber)
            
            self.loginprocess.jobParams['vnc'] = vnc
            self.loginprocess.jobParams['turboVncFlavour'] = turboVncFlavour
            self.loginprocess.jobParams['vncOptionsString'] = self.loginprocess.buildVNCOptionsString()

            if (not self.stopped() and not self.loginprocess.canceled()):
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
                event.loginprocess.skd = cvlsshutils.sshKeyDist.KeyDist(event.loginprocess.parentWindow,event.loginprocess.jobParams['username'],event.loginprocess.jobParams['loginHost'],event.loginprocess.notify_window,event.loginprocess.sshpaths)
                successevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CHECK_RUNNING_SERVER,event.loginprocess)
                event.loginprocess.skd.distributeKey(lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),successevent),
                                                     event.loginprocess.cancel)
            else:
                event.Skip()


        def checkRunningServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_CHECK_RUNNING_SERVER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_CHECK_RUNNING_SERVER')
                event.loginprocess.skd = None # SSH key distritbution is complete at this point.
                wx.CallAfter(event.loginprocess.updateProgressDialog, 3,"Looking for an existing desktop to connect to")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_RECONNECT_DIALOG,event.loginprocess)
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.listAllCmd,event.loginprocess.listAllRegEx,nextevent,"Error determining if you have any existing jobs running",requireMatch=False)
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
                wx.CallAfter(event.loginprocess.updateProgressDialog, 4,"Do you want to reconnect to an existing desktop?")
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
                    dialog=LoginProcess.SimpleOptionDialog(event.loginprocess.notify_window,-1,"Reconnect to Existing Desktop","An Existing Desktop was found. It has %s remaining. Would you like to reconnect or kill it and start a new desktop"%timestring,"Reconnect","New Desktop",ReconnectCallback,NewDesktopCallback)
                else:
                    dialog=LoginProcess.SimpleOptionDialog(event.loginprocess.notify_window,-1,"Reconnect to Existing Desktop","An Existing Desktop was found, would you like to reconnect or kill it and start a new desktop","Reconnect","New Desktop",ReconnectCallback,NewDesktopCallback)
                wx.CallAfter(dialog.ShowModal)
            else:
                event.Skip()

        def getProjects(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_PROJECTS):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_PROJECTS')

                wx.CallAfter(event.loginprocess.updateProgressDialog, 5,"Getting a list of your valid projects")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SELECT_PROJECT,event.loginprocess)
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.getProjectsCmd,event.loginprocess.getProjectsRegEx,nextevent,"I couldn't find any projects that you were a member of.")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def selectProject(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_SELECT_PROJECT):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_SELECT_PROJECT')

                wx.CallAfter(event.loginprocess.updateProgressDialog, 5,"Getting a list of your valid projects")
                grouplist=[]
                groups=[]
                showDialog=False
                msg=""
                for match in event.loginprocess.matchlist:
                    grouplist = grouplist + match.values()
                    groups.append(match.values())
                
                logger.debug('selectProject: groups = ' + str(groups))

                try:
                    event.loginprocess.startServerCmd.format(**event.loginprocess.jobParams) # check if we actually need the project to format the startServerCmd
                    if (event.loginprocess.jobParams.has_key('project') and not (event.loginprocess.jobParams['project'] in grouplist)):
                        logger.debug("we have a value for project, but the user is not a member of that project")
                        msg='You don\'t appear to be a member of the project {project}.\n\nPlease select from one of the following:'.format(**event.loginprocess.jobParams)
                        event.loginprocess.jobParams.pop('project',None)
                        try: # check again if we really need the project field.
                            logger.debug("trying to format the startServerCmd")
                            event.loginprocess.startServerCmd.format(**event.loginprocess.jobParams)
                            logger.debug("trying to format the startServerCmd, project is not necessary")
                            showDialog=False
                        except:
                            logger.debug("trying to format the startServerCmd, project is necessary")
                            showDialog=True
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
                        if parentWindow!=None and parentWindow.__class__.__name__=="LauncherMainFrame":
                            launcherMainFrame = parentWindow
                            launcherMainFrame.massiveProjectComboBox.SetValue(project)
                            if project in launcherMainFrame.massiveProjects:
                                launcherMainFrame.massiveProjectComboBox.SetSelection(launcherMainFrame.massiveProjects.index(project))
                            massiveLauncherConfig = event.loginprocess.massiveLauncherConfig
                            massiveLauncherPreferencesFilePath = event.loginprocess.massiveLauncherPreferencesFilePath
                            if massiveLauncherConfig!=None and massiveLauncherPreferencesFilePath!=None:
                               massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_project", project)
                               with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                                   massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)
                    cancelCallback=lambda x: event.loginprocess.cancel(x)
                    #dlg=ListSelectionDialog(event.loginprocess.notify_window, headers=None,message=msg, items=grouplist, callback=callback, style=wx.RESIZE_BORDER)
                    dlg=ListSelectionDialog(parent=event.loginprocess.notify_window, title='MASSIVE/CVL Launcher', headers=None, message=msg, noSelectionMessage="Please select a valid MASSIVE project from the list.", items=grouplist, okCallback=okCallback, cancelCallback = cancelCallback, style=wx.DEFAULT_DIALOG_STYLE)
                    dlg.ShowModal()
                if (not event.loginprocess.canceled()):
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_SERVER,event.loginprocess)
                    wx.PostEvent(event.loginprocess.notify_window,nextevent)
            else:
                event.Skip()

        def startServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_SERVER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_START_SERVER')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 5,"Starting a new desktop session")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_WAIT_FOR_SERVER,event.loginprocess)
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.startServerCmd,event.loginprocess.startServerRegEx,nextevent,"Error starting the VNC server. This could occur")
                t.setDaemon(False)
                event.loginprocess.started_job.set()
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def waitForServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_WAIT_FOR_SERVER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_WAIT_FOR_SERVER')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 6,"Waiting for the VNC server to start")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_EXECUTION_HOST,event.loginprocess)
                t = LoginProcess.runLoopServerCommandThread(event.loginprocess,event.loginprocess.runningCmd,event.loginprocess.runningRegEx,nextevent,"")
                #t = LoginProcess.waitForStartThread(event.loginprocess,event)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def getEstimatedStart(event):
            # runLoopServerCommand can generate GET_ESTIMATED_START events. Most other threads can only post events that were given to them when they were initialised
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_ESTIMATED_START):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_ESTIMATED_START')
                if (event.loginprocess.showStartCmd!=None):
                    logger.debug('loginProcessEvent: event.loginprocess.showStartCmd is not None, so posting EVT_LOGINPROCESS_SHOW_ESTIMATED_START')
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHOW_ESTIMATED_START,event.loginprocess)
                    t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.showStartCmd,event.loginprocess.showStartRegEx,nextevent,"Error estimating the start time")
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
                    wx.CallAfter(event.loginprocess.updateProgressDialog, 6, string )
                    logger.debug('loginProcessEvent: showEstimatedStart: ' + string)
                except Exception as e:
                    logger.debug('loginProcessEvent: showEstimatedStart: exception: ' + str(traceback.format_exc()))
                    pass
            else:
                event.Skip()


        def getExecutionHost(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_EXECUTION_HOST):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_EXECUTION_HOST')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 6,"Getting execution host")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_VNCDISPLAY,event.loginprocess)
                logger.debug('loginProcessEvent: getExecutionHost: posting EVT_LOGINPROCESS_GET_VNCDISPLAY')
                t = LoginProcess.runLoopServerCommandThread(event.loginprocess,event.loginprocess.execHostCmd,event.loginprocess.execHostRegEx,nextevent,"")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def getVNCDisplay(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_VNCDISPLAY):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_VNCDISPLAY')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 6,"Getting the display number")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_TUNNEL,event.loginprocess)
                logger.debug('loginProcessEvent: getVNCDisplay: posting EVT_LOGINPROCESS_START_TUNNEL')
                t = LoginProcess.runLoopServerCommandThread(event.loginprocess,event.loginprocess.vncDisplayCmd,event.loginprocess.vncDisplayRegEx,nextevent,"Unable to get the VNC display")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()
    
        def startTunnel(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_TUNNEL):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_START_TUNNEL')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 7,"Starting the tunnel")
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


                if ("m1" in event.loginprocess.loginParams['loginHost'] or "m2" in event.loginprocess.loginParams['loginHost']):
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SET_DESKTOP_RESOLUTION,event.loginprocess)
                else:
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_FORWARD_AGENT,event.loginprocess)

                t = LoginProcess.runAsyncServerCommandThread(event.loginprocess,event.loginprocess.tunnelCmd,event.loginprocess.tunnelRegEx,nextevent,"Unable to start the tunnel for some reason")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)

            else:
                event.Skip()

        def setDesktopResolution(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_SET_DESKTOP_RESOLUTION):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_SET_DESKTOP_RESOLUTION')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 8, "Setting the desktop resolution")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_RUN_SANITY_CHECK,event.loginprocess)

                logger.debug('Setting the desktop resolution.')
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.setDisplayResolutionCmd, '.*', nextevent, '', requireMatch=False)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def runSanityCheck(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RUN_SANITY_CHECK):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_RUN_SANITY_CHECK')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 8, "Running the sanity check script")
                nextevent = LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_FORWARD_AGENT,event.loginprocess)

                if "m1" in event.loginprocess.loginParams['loginHost'] or "m2" in event.loginprocess.loginParams['loginHost']:
                    logger.debug('Running server-side sanity check.')
                    t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.runSanityCheckCmd,
                                                            '.*',
                                                            nextevent,
                                                            'Error reported by server-side sanity check.',
                                                            sanityCheckHack=True)
                    t.setDaemon(False)
                    t.start()
                    event.loginprocess.threads.append(t)
                else:
                    logger.debug('Not running server-side sanity check; must be using a CVL host.')
                    if not event.loginprocess.canceled():
                        logger.debug('Posting the EVT_LOGINPROCESS_FORWARD_AGENT event.')
                        wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(), nextevent)
            else:
                event.Skip()

        def forwardAgent(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_FORWARD_AGENT):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_FORWARD_AGENT')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 8,"Setting up SSH Agent forwarding")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_OTP,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_GET_OTP')
                t = LoginProcess.runAsyncServerCommandThread(event.loginprocess,event.loginprocess.agentCmd,event.loginprocess.agentRegEx,nextevent,"Unable to forward the ssh agent")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def getVNCPassword(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_OTP):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_GET_OTP')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 9,"Getting the one-time password for the VNC server")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_VIEWER,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_START_VIEWER')
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.otpCmd,event.loginprocess.otpRegEx,nextevent,"Unable to determine the one-time password for the VNC session")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def startViewer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_VIEWER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_START_VIEWER')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 9,"Starting the VNC viewer")
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_STAT_RUNNING_JOB,event.loginprocess)
                logger.debug('loginProcessEvent: posting EVT_LOGINPROCESS_STAT_RUNNING_JOB')
                t = LoginProcess.startVNCViewer(event.loginprocess,nextevent)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()


        def cancel(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_CANCEL):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_CANCEL')
                if event.loginprocess.started_job.isSet():
                    logger.debug('loginProcessEvent: cancel: trying to stop the job on MASSIVE/CVL but since we are already in a cancel state, we will not try to be to graceful about it')
                    nextevent=None
                    # Cancelation during the startup process is tricky. It conceivable although unlikely that we will have set the event to say the job is started, but not succesfully submitted a job.
                    # Therefore test if the stopCmd can actually be formated before attempting to execute it.
                    try:
                        event.loginprocess.stopCmd.format(**event.loginprocess.jobParams)
                        t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.stopCmd,".",nextevent,"",requireMatch=False)
                        t.setDaemon(True)
                        t.start()
                        event.loginprocess.threads.append(t)
                    except:
                        pass
 
                if (event.loginprocess.skd!=None): 
                        logger.debug('loginProcessEvent: cancel: calling skd.cancel()')
                        event.loginprocess.skd.cancel()
                newevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,event.loginprocess)
                logger.debug('loginProcessEvent: cancel: posting EVT_LOGINPROCESS_SHUTDOWN')
                wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),newevent)
                if (event.string!=""):
                    dlg=HelpDialog(event.loginprocess.notify_window,title="MASSIVE/CVL Launcher", name="MASSIVE/CVL Launcher",size=(680,290),style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)
                    panel=wx.Panel(dlg)
                    sizer=wx.BoxSizer()
                    panel.SetSizer(sizer)
                    text=wx.StaticText(panel,wx.ID_ANY,label=event.string)
                    sizer.Add(text,0,wx.ALL,15)
                    dlg.addPanel(panel)
                    dlg.ShowModal()
                if hasattr(event.loginprocess, 'turboVncElapsedTimeInSeconds') and event.loginprocess.turboVncElapsedTimeInSeconds > 3:
                    logger.debug("TurboVNC's elapsed time was greater than 3 seconds, " +
                        "so presumably user stopped VNC session, so no need to ask " +
                        "if they want to submit a debug log to cvl.massive.org.au")
                    logger.dump_log(event.loginprocess.notify_window,submit_log=False)
                else:
                    logger.dump_log(event.loginprocess.notify_window,submit_log=True)
            else:
                event.Skip()

        def shutdown(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_SHUTDOWN):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_SHUTDOWN')
                for t in event.loginprocess.threads:
                    try:
                        logger.debug('loginProcessEvent: shutdown: attempting to stop thread ' + str(t))
                        t.stop()
                    except:
                        pass
                # Throw away the thread references. We've done all we can to ask them to stop at this point.
                event.loginprocess.threads=[]
                if (event.loginprocess.notify_window.progressDialog != None):
                    wx.CallAfter(event.loginprocess.notify_window.progressDialog.Hide)
                    wx.CallAfter(event.loginprocess.notify_window.progressDialog.Show, False)
                    wx.CallAfter(event.loginprocess.notify_window.progressDialog.Destroy)
                    event.loginprocess.notify_window.progressDialog = None
                logger.debug('loginProcessEvent: shutdown: all threads stopped and joined')
                if event.loginprocess.autoExit:
                    if hasattr(event.loginprocess, 'turboVncElapsedTimeInSeconds'):
                        if event.loginprocess.turboVncElapsedTimeInSeconds > 3:
                            os._exit(0)
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
                nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_QUESTION_KILL_SERVER,event.loginprocess)
                logger.debug('loginProcessEvent: statRunningJob: posting EVT_LOGINPROCESS_QUESTION_KILL_SERVER')
                t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.listAllCmd,event.loginprocess.listAllRegEx,nextevent,"")
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()



        def showKillServerDialog(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_QUESTION_KILL_SERVER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_QUESTION_KILL_SERVER')
                KillCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_KILL_SERVER,event.loginprocess))
                NOOPCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,event.loginprocess))
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
                        dialog=LoginProcess.SimpleOptionDialog(event.loginprocess.notify_window,-1,"Stop the Desktop?","Would you like to leave your current session running so that you can reconnect later?\nIt has %s remaining."%timestring,"Stop the desktop","Leave it running",KillCallback,NOOPCallback)
                    elif ("m1" not in event.loginprocess.loginParams['loginHost'] and "m2" not in event.loginprocess.loginParams['loginHost']):
                        dialog=LoginProcess.SimpleOptionDialog(event.loginprocess.notify_window,-1,"Stop the Desktop?","Would you like to leave your current session running so that you can reconnect later?","Stop the desktop","Leave it running",KillCallback,NOOPCallback)
                    else:
                        logger.debug("showKillServerDialog: timeRemaining is None and ('m1' or 'm2' is in loginHost)")
                    if dialog:
                        logger.debug("showKillServerDialog: Showing the 'Stop the desktop' question dialog.")
                        wx.CallAfter(dialog.ShowModal)
                    else:
                        logger.debug("showKillServerDialog: Not showing the 'Stop the desktop' question dialog.")
                else:
                    logger.debug("showKillServerDialog: len(event.loginprocess.matchlist)=0")
                    wx.CallAfter(NOOPCallback)
            else:
                event.Skip()



        def killServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER or event.GetId() == LoginProcess.EVT_LOGINPROCESS_KILL_SERVER):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_RESTART_SERVER or we are EVT_LOGINPROCESS_KILL_SERVER')
                wx.CallAfter(event.loginprocess.updateProgressDialog, 4,"Stopping the existing desktop session")
                if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER):
                    logger.debug("caught an EVT_LOGINPROCESS_RESTART_SERVER")
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_PROJECTS,event.loginprocess)
                else:
                    logger.debug("caught an EVT_LOGINPROCESS_KILL_SERVER")
                    nextevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,event.loginprocess)
                if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER):
                    t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.stopCmdForRestart,".*",nextevent,"",requireMatch=False)
                else:
                    t = LoginProcess.runServerCommandThread(event.loginprocess,event.loginprocess.stopCmd,".*",nextevent,"",requireMatch=False)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def normalTermination(event):
            # This event is generated if we shutdown the VNC server upon exit. Its basically a no-op, and moves onto processing the shutdown sequence of events
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_NORMAL_TERMINATION):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_NORMAL_TERMINATION')
                wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_COMPLETE,event.loginprocess))
            else:
                event.Skip()

        def complete(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_COMPLETE):
                logger.debug('loginProcessEvent: caught EVT_LOGINPROCESS_COMPLETE')
                if event.loginprocess.autoExit:
                    if hasattr(event.loginprocess, 'turboVncElapsedTimeInSeconds'):
                        if event.loginprocess.turboVncElapsedTimeInSeconds > 3:
                            os._exit(0)
            else:
                event.Skip()

    myEVT_CUSTOM_LOGINPROCESS=None
    EVT_CUSTOM_LOGINPROCESS=None
    def __init__(self,parentWindow,username,host,resolution,cipher,notifywindow,sshpaths,siteConfig=None,project=None,hours=None,nodes=1,usePBS=True,directConnect=False,autoExit=False,fastInterface="-ib",massiveLauncherConfig=None, massiveLauncherPreferencesFilePath=None):
        self.parentWindow = parentWindow
        LoginProcess.myEVT_CUSTOM_LOGINPROCESS=wx.NewEventType()
        LoginProcess.EVT_CUSTOM_LOGINPROCESS=wx.PyEventBinder(self.myEVT_CUSTOM_LOGINPROCESS,1)
        self.notify_window = notifywindow
        self.loginParams={}
        self.jobParams={}
        self.loginParams['launcher_version_number'] = launcher_version_number.version_number
        self.loginParams['username']=username
        self.loginParams['configName']=host
        self.loginParams['project']=project
        self.loginParams['sshBinary']=sshpaths.sshBinary
        self.jobParams['resolution']=resolution
        self.jobParams['cipher']=cipher
        self.jobParams.update(self.loginParams)
        self.sshpaths=sshpaths
        self.threads=[]
        self.jobParams['project']=project
        self.jobParams['hours']=hours
        self.jobParams['wallseconds']=int(hours)*60*60
        self.jobParams['nodes']=nodes
        self._canceled=threading.Event()
        self.usePBS=usePBS
        self.directConnect = directConnect
        self.autoExit = autoExit
        self.sshCmd = '{sshBinary} -A -T -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o StrictHostKeyChecking=yes -l {username} {loginHost} '
        self.sshTunnelProcess=None
        self.sshAgentProcess=None
        self.fastInterface="-ib"
        self.joblist=[]
        self.started_job=threading.Event()
        self.skd=None
        self.massiveLauncherConfig = massiveLauncherConfig
        self.massiveLauncherPreferencesFilePath = massiveLauncherPreferencesFilePath
        if (siteConfig!=None):
            self.listAllCmd=siteConfig['listAllCmd']
            self.listAllRegEx=siteConfig['listAllRegEx']
            self.runningCmd=siteConfig['runningCmd']
            self.runningRegEx=siteConfig['runningRegEx']
            self.stopCmd=siteConfig['stopCmd']
            self.stopCmdForRestart=siteConfig['stopCmdForRestart']
            self.execHostCmd=siteConfig['execHostCmd']
            self.startServerCmd=siteConfig['startServerCmd']
            self.startServerRegEx=siteConfig['startServerRegEx']
            self.showStartCmd=siteConfig['showStartCmd']
            self.showStartRegEx=siteConfig['showStartRegEx']
            self.vncDisplayCmd = siteConfig['vncDisplayCmd']
            self.vncDisplayRegEx=siteConfig['vncDisplayRegEx']
            self.messageRegexs=siteConfig['messageRegexs']
        else:
            self.siteConfig={}

            self.messageRegexs=[re.compile("^INFO:(?P<info>.*(?:\n|\r\n?))",re.MULTILINE),re.compile("^WARN:(?P<warn>.*(?:\n|\r\n?))",re.MULTILINE),re.compile("^ERROR:(?P<error>.*(?:\n|\r\n?))",re.MULTILINE)]
            # output from startServerCmd that matches and of these regular expressions will pop up in a window for the user
            if ("m1" in self.loginParams['configName'] or "m2" in self.loginParams['configName']):
                update={}
                update['loginHost']=host
                self.loginParams.update(update)
                self.jobParams.update(self.loginParams)
                self.listAllCmd='qstat -u {username}'
                self.listAllRegEx='^\s*(?P<jobid>(?P<jobidNumber>[0-9]+).\S+)\s+{username}\s+(?P<queue>\S+)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>[^C])\s+(?P<elapTime>\S+)\s*$'
                self.runningCmd='qstat -u {username}'
                self.runningRegEx='^\s*(?P<jobid>{jobid})\s+{username}\s+(?P<queue>\S+)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>R)\s+(?P<elapTime>\S+)\s*$'
                # request_visnode is a little buggy, if you issue a qdel <jobid> ; request_visnode it may provide the id of the deleted job. Sleep to work around
                self.stopCmd='\'qdel -a {jobid}\''
                self.stopCmdForRestart='\'qdel {jobid} ; sleep 5\''
                self.execHostCmd='qpeek {jobidNumber}'
                self.execHostRegEx='\s*To access the desktop first create a secure tunnel to (?P<execHost>\S+)\s*$'
                self.startServerCmd="\'/usr/local/desktop/request_visnode.sh {project} {hours} {nodes} True False False\'"
                self.runSanityCheckCmd="\'/usr/local/desktop/sanity_check.sh {launcher_version_number}\'"
                self.setDisplayResolutionCmd="\'/usr/local/desktop/set_display_resolution.sh {resolution}\'"
                #self.getProjectsCmd='\"groups | sed \'s@ @\\n@g\'\"' # '\'groups | sed \'s\/\\\\ \/\\\\\\\\n\/g\'\''
                self.getProjectsCmd='\"gbalance -u {username} --show Name | tail -n +3\"'
                self.getProjectsRegEx='^\s*(?P<group>\S+)\s*$'
                self.startServerRegEx="^(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s*$"
                self.showStartCmd="showstart {jobid}"
                self.showStartRegEx="Estimated Rsv based start .*?on (?P<estimatedStart>.*)"
                self.vncDisplayCmd = '"/usr/bin/ssh {execHost} \' module load turbovnc ; vncserver -list\'"'
                self.vncDisplayRegEx='^(?P<vncDisplay>:[0-9]+)\s*(?P<vncPID>[0-9]+)\s*$'
                self.otpCmd = '"/usr/bin/ssh {execHost} \' module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\'"'
                self.otpRegEx='^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$'

            else:
                update={}
                update['loginHost']="118.138.241.53"
                self.loginParams.update(update)
                self.jobParams.update(self.loginParams)
                self.directConnect=True
                self.execHostCmd='\"module load pbs ; qstat -f {jobidNumber} | grep exec_host | sed \'s/\ \ */\ /g\' | cut -f 4 -d \' \' | cut -f 1 -d \'/\' | xargs -iname hostn name | grep address | sed \'s/\ \ */\ /g\' | cut -f 3 -d \' \' | xargs -iip echo execHost ip; qstat -f {jobidNumber}\"'
                self.execHostRegEx='^\s*execHost (?P<execHost>\S+)\s*$'
                self.getProjectsCmd='\"groups | sed \'s@ @\\n@g\'\"' # '\'groups | sed \'s\/\\\\ \/\\\\\\\\n\/g\'\''
                self.getProjectsRegEx='^\s*(?P<group>\S+)\s*$'
                self.listAllCmd='\"module load pbs ; module load maui ; qstat | grep {username}\"'
                self.listAllRegEx='^\s*(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s+(?P<jobname>desktop_\S+)\s+{username}\s+(?P<elapTime>\S+)\s+(?P<state>R)\s+(?P<queue>\S+)\s*$'
                self.runningCmd='\"module load pbs ; module load maui ; qstat | grep {username}\"'
                self.runningRegEx='^\s*(?P<jobid>{jobidNumber}\.\S+)\s+(?P<jobname>desktop_\S+)\s+{username}\s+(?P<elapTime>\S+)\s+(?P<state>R)\s+(?P<queue>\S+)\s*$'
                if ("Hugyens" in self.loginParams['configName']):
                    self.startServerCmd="\"module load pbs ; module load maui ; echo \'module load pbs ; /usr/local/bin/vncsession --vnc turbovnc --geometry {resolution} ; sleep {wallseconds}\' |  qsub -q huygens -l nodes=1:ppn=1,walltime={wallseconds} -N desktop_{username} -o .vnc/ -e .vnc/\""
                else:
                    self.startServerCmd="\"module load pbs ; module load maui ; echo \'module load pbs ; /usr/local/bin/vncsession --vnc turbovnc --geometry {resolution} ; sleep {wallseconds}\' |  qsub -l nodes=1:ppn=1,walltime={wallseconds} -N desktop_{username} -o .vnc/ -e .vnc/\""
                self.startServerRegEx="^(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s*$"
                self.stopCmd='\"module load pbs ; module load maui ; qdel -a {jobidNumber}\"'
                self.stopCmdForRestart='\"module load pbs ; module load maui ; qdel {jobidNumber}\"'
                self.showStartCmd=None
                self.showStartRegEx="Estimated Rsv based start on (?P<estimatedStart>^-.*)"
                self.vncDisplayCmd = '" /usr/bin/ssh {execHost} \' cat /var/spool/torque/spool/{jobidNumber}.*\'"'
                self.vncDisplayRegEx='^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$'
                self.otpCmd = '"/usr/bin/ssh {execHost} \' module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\'"'
                self.otpRegEx='^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$'


            if (not self.directConnect):
                self.agentCmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -l {username} {loginHost} \"/usr/bin/ssh -A {execHost} \\"echo agent_hello; bash \\"\"'
                self.agentRegEx='agent_hello'
                self.tunnelCmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -L {localPortNumber}:{execHost}:{remotePortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"'
                self.tunnelRegEx='tunnel_hello'
            else:
            # I've disabled StrickHostKeyChecking here temporarily untill all CVL vms are added a a most known hosts file.
                self.agentCmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -l {username} {execHost} "echo agent_hello; bash "'
                self.agentRegEx='agent_hello'
                self.tunnelCmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -L {localPortNumber}:localhost:{remotePortNumber} -l {username} {execHost} "echo tunnel_hello; bash"'
                self.tunnelRegEx='tunnel_hello'

        for k, v in self.__dict__.iteritems():
            logger.debug('loginProcessEvent properties: %s = %s' % (str(k), str(v),))

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
        LoginProcess.EVT_LOGINPROCESS_SHUTDOWN = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SHOW_MESSAGE = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SHOW_WARNING = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SHOW_ERROR = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_ESTIMATED_START = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SHOW_ESTIMATED_START = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_PROJECTS = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SELECT_PROJECT = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SET_DESKTOP_RESOLUTION = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_RUN_SANITY_CHECK = wx.NewId()

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
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.setDesktopResolution)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.runSanityCheck)
        #self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.showMessages)

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
                        return None
                    try:
                        (ehours,emin) = job['elapTime'].split(':')
                    except:
                        ehours=0
                        emin=0
                    return (int(rhours)-int(ehours))*60*60 + (int(rmin)-int(emin))*60
                else:
                    try:
                        (rhours,rmin) = job['reqTime'].split(':')
                    except:
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
        event=self.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CHECK_VNC_VER,self)
        wx.PostEvent(self.notify_window.GetEventHandler(),event)
   
    def cancel(self,error=""):
        if (not self._canceled.isSet()):
            self._canceled.set()
            logger.debug("LoginProcess.cancel: " + error)
            event=self.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CANCEL,self,error)
            wx.PostEvent(self.notify_window.GetEventHandler(),event)

    def canceled(self):
        return self._canceled.isSet()


    def updateProgressDialog(self, value, message):
        if self.notify_window.progressDialog!=None:
            self.notify_window.progressDialog.Update(value, message)
            self.shouldAbort = self.notify_window.progressDialog.shouldAbort()

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

        if 'jpeg_compression' in self.notify_window.vncOptions and self.notify_window.vncOptions['jpeg_compression']==False:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "nojpeg"
        defaultJpegChrominanceSubsampling = "1x"
        if 'jpeg_chrominance_subsampling' in self.notify_window.vncOptions and self.notify_window.vncOptions['jpeg_chrominance_subsampling']!=defaultJpegChrominanceSubsampling:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "samp " + self.notify_window.vncOptions['jpeg_chrominance_subsampling']
        defaultJpegImageQuality = "95"
        if 'jpeg_image_quality' in self.notify_window.vncOptions and self.notify_window.vncOptions['jpeg_image_quality']!=defaultJpegImageQuality:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "quality " + self.notify_window.vncOptions['jpeg_image_quality']
        if 'zlib_compression_enabled' in self.notify_window.vncOptions and self.notify_window.vncOptions['zlib_compression_enabled']==True:
            if 'zlib_compression_level' in self.notify_window.vncOptions:
                vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "compresslevel " + self.notify_window.vncOptions['zlib_compression_level']
        if 'view_only' in self.notify_window.vncOptions and self.notify_window.vncOptions['view_only']==True:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "viewonly"
        if 'disable_clipboard_transfer' in self.notify_window.vncOptions and self.notify_window.vncOptions['disable_clipboard_transfer']==True:
            if sys.platform.startswith("win"):
                vncOptionsString = vncOptionsString + " /disableclipboard"
            #else:
                #vncOptionsString = vncOptionsString + " -noclipboardsend -noclipboardrecv"
        if sys.platform.startswith("win"):
            if 'scale' in self.notify_window.vncOptions:
                if self.notify_window.vncOptions['scale']=="Auto":
                    vncOptionsString = vncOptionsString + " /fitwindow"
                else:
                    vncOptionsString = vncOptionsString + " /scale " + self.notify_window.vncOptions['scale']
            defaultSpanMode = 'automatic'
            if 'span' in self.notify_window.vncOptions and self.notify_window.vncOptions['span']!=defaultSpanMode:
                vncOptionsString = vncOptionsString + " /span " + self.notify_window.vncOptions['span']
        if 'double_buffering' in self.notify_window.vncOptions and self.notify_window.vncOptions['double_buffering']==False:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "singlebuffer"
        if 'full_screen_mode' in self.notify_window.vncOptions and self.notify_window.vncOptions['full_screen_mode']==True:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "fullscreen"
        if 'deiconify_on_remote_bell_event' in self.notify_window.vncOptions and self.notify_window.vncOptions['deiconify_on_remote_bell_event']==False:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "noraiseonbeep"
        if sys.platform.startswith("win"):
            if 'emulate3' in self.notify_window.vncOptions and self.notify_window.vncOptions['emulate3']==True:
                vncOptionsString = vncOptionsString + " /emulate3"
            if 'swapmouse' in self.notify_window.vncOptions and self.notify_window.vncOptions['swapmouse']==True:
                vncOptionsString = vncOptionsString + " /swapmouse"
        if 'dont_show_remote_cursor' in self.notify_window.vncOptions and self.notify_window.vncOptions['dont_show_remote_cursor']==True:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "nocursorshape"
        elif 'let_remote_server_deal_with_mouse_cursor' in self.notify_window.vncOptions and self.notify_window.vncOptions['let_remote_server_deal_with_mouse_cursor']==True:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "x11cursor"
        if 'request_shared_session' in self.notify_window.vncOptions and self.notify_window.vncOptions['request_shared_session']==False:
            vncOptionsString = vncOptionsString + " " + optionPrefixCharacter + "noshared"
        if sys.platform.startswith("win"):
            if 'toolbar' in self.notify_window.vncOptions and self.notify_window.vncOptions['toolbar']==False:
                vncOptionsString = vncOptionsString + " /notoolbar"
            if 'dotcursor' in self.notify_window.vncOptions and self.notify_window.vncOptions['dotcursor']==True:
                vncOptionsString = vncOptionsString + " /dotcursor"
            if 'smalldotcursor' in self.notify_window.vncOptions and self.notify_window.vncOptions['smalldotcursor']==True:
                vncOptionsString = vncOptionsString + " /smalldotcursor"
            if 'normalcursor' in self.notify_window.vncOptions and self.notify_window.vncOptions['normalcursor']==True:
                vncOptionsString = vncOptionsString + " /normalcursor"
            if 'nocursor' in self.notify_window.vncOptions and self.notify_window.vncOptions['nocursor']==True:
                vncOptionsString = vncOptionsString + " /nocursor"
            if 'writelog' in self.notify_window.vncOptions and self.notify_window.vncOptions['writelog']==True:
                if 'loglevel' in self.notify_window.vncOptions and self.notify_window.vncOptions['loglevel']==True:
                    vncOptionsString = vncOptionsString + " /loglevel " + self.notify_window.vncOptions['loglevel']
                if 'logfile' in self.notify_window.vncOptions:
                    vncOptionsString = vncOptionsString + " /logfile \"" + self.notify_window.vncOptions['logfile'] + "\""
        return vncOptionsString
