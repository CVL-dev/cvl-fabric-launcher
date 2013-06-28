from threading import *
import sshKeyDist
from utilityFunctions import *
import traceback
import sys
import launcher_version_number
import shlex
import xmlrpclib
import re
import urllib2
import datetime




class LoginProcess():
    """LoginProcess Class."""
            
    class createTunnelThread(Thread):

        def __init__(self,loginprocess,success,failure):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.success=success
            self.failure=failure
    
        def stop(self):
            self.process.stdin.write("exit\n")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            try:
                # Dodgyness ... I can't think of how to determine the remotePortNumber except by adding 5900 to the vnc Display number.
                # I can't think of an easy way to get the vncDisplay number when executing via qsub, but on MASSIVE it will always ben display :1
                if (not self.loginprocess.jobParams.has_key('localPortNumber')):
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.bind(('localhost', 0))
                    localPortNumber = sock.getsockname()[1]
                    sock.close()
                    self.loginprocess.localPortNumber = str(localPortNumber)
                    self.loginprocess.jobParams['localPortNumber'] = str(localPortNumber)
                if (not self.loginprocess.jobParams.has_key('vncDisplay')):
                    self.loginprocess.jobParams['vncDisplay']=":1"
                self.loginprocess.jobParams['remotePortNumber'] = str(5900+int(self.loginprocess.jobParams['vncDisplay'].lstrip(':')))
                try:
                    tunnel_cmd = self.loginprocess.tunnelCmd.format(**self.loginprocess.jobParams)
                except KeyError as e:
                    self.loginprocess.cancel("I couldn't determine the correct command to create a tunnel for the VNC session. I was missing the parameter %s"%e)
                    return



                logger_debug('tunnel_cmd: ' + tunnel_cmd)

                # Not 100% sure if this is necessary on Windows vs Linux. Seems to break the
                # Windows version of the launcher, but leaving in for Linux/OSX.
                if sys.platform.startswith("win"):
                    pass
                else:
                    tunnel_cmd = shlex.split(tunnel_cmd)

                self.process = subprocess.Popen(tunnel_cmd,
                    universal_newlines=True,shell=False,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
                while (not self.stopped()):
                    time.sleep(0.1)
                    line = self.process.stdout.readline()
                    if (line != None):
                        match = re.search(self.loginprocess.tunnelRegEx.format(**self.loginprocess.jobParams),line)
                        if (match and not self.stopped()):
                            self.success()
                            success=True
                    else:
                        if (not success):
                            self.failure()
                    if self.stopped():
                        return
            except Exception as e:
                error_message = "%s"%e
                logger_error('Create tunnel failure: '+ error_message)
                self.failure()
                return

    class getOTPThread(Thread):
        def __init__(self,loginprocess):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
    
        def stop(self):
            logger_debug("stoping the thread that generates the one time password")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            try:
                try:
                    otp_cmd = self.loginprocess.otpCmd.format(**self.loginprocess.jobParams)
                except KeyError as e:
                    self.loginprocess.cancel("Trying to get the One Time password, I was missing a parameter %s"%e)
                    return
                logger_debug("otp command %s"%otp_cmd)
                if sys.platform.startswith("win"):
                    pass
                else:
                    otp_cmd = shlex.split(otp_cmd)

                otpProcess = subprocess.Popen(otp_cmd,
                    universal_newlines=True,shell=False,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
                stdout,stderr = otpProcess.communicate()
                passwdFound=False
                for line in stdout.split('\n'):
                    passwd = re.search(self.loginprocess.otpRegEx.format(**self.loginprocess.jobParams),line)
                    if (passwd):
                        self.loginprocess.jobParams.update(passwd.groupdict())
                        passwdFound=True
                        break

            except Exception as e:
                self.loginprocess.cancel("Couldn't execute vncpassword %s"%e)
                return
            if (not passwdFound):
                self.loginprocess.cancel("Couldn't extract a VNC password")
                return
            if (not self.stopped()):
                event=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_VIEWER,self.loginprocess)
                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),event)
                
    class forwardAgentThread(Thread):

        def __init__(self,loginprocess,success,failure):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.success=success
            self.failure=failure
    
        def stop(self):
            logger_debug("stoping the thread that forwards the SSH Agent") 
            self.process.stdin.write("exit\n")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):

            try:
                agent_cmd = self.loginprocess.agentCmd.format(**self.loginprocess.jobParams)
                logger_debug('agent_cmd: ' + agent_cmd)

                # Not 100% sure if this is necessary on Windows vs Linux. Seems to break the
                # Windows version of the launcher, but leaving in for Linux/OSX.
                if sys.platform.startswith("win"):
                    pass
                else:
                    agent_cmd = shlex.split(agent_cmd)

                self.process = subprocess.Popen(agent_cmd,
                    universal_newlines=True,shell=False,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
                while (not self.stopped()):
                    time.sleep(0.1)
                    line = self.process.stdout.readline()
                    if (line != None):
                        match = re.search(self.loginprocess.agentRegEx.format(**self.loginprocess.jobParams),line)
                        if (match and not self.stopped()):
                            self.success()
                            success=True
                    else:
                        if (not success):
                            self.failure()
                    if self.stopped():
                        return

            except Exception as e:
                error_message = "%s"%e
                logger_error('forward agent failure: '+ error_message)
                self.failure()

    class SimpleOptionDialog(wx.Dialog):
        def __init__(self, parent, id, title, text, okString, cancelString,OKCallback,CancelCallback):
            wx.Dialog.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER | wx.STAY_ON_TOP)
            self.SetTitle(title)
            self.panel = wx.Panel(self,-1)
            self.label = wx.StaticText(self.panel, -1, text)
            self.Cancel = wx.Button(self.panel,-1,label=cancelString)
            self.OK = wx.Button(self.panel,-1,label=okString)
            self.OKCallback=OKCallback
            self.CancelCallback=CancelCallback

            self.sizer = wx.FlexGridSizer(2, 1)
            self.buttonRow = wx.FlexGridSizer(1, 2)
            self.sizer.Add(self.label)
            self.sizer.Add(self.buttonRow)
            self.buttonRow.Add(self.Cancel)
            self.buttonRow.Add(self.OK)

            self.OK.Bind(wx.EVT_BUTTON,self.onOK)
            self.Cancel.Bind(wx.EVT_BUTTON,self.onCancel)

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
        def __init__(self,loginprocess):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
    
        def stop(self):
            logger_debug("stopping the thread that starts the VNC Viewer")
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
                    self.turboVncProcess = subprocess.Popen(vncCommandString,
                        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                        universal_newlines=True)
                    self.turboVncStdout, self.turboVncStderr = self.turboVncProcess.communicate(input=self.loginprocess.jobParams['vncPasswd'] + "\n")
                    if (not self.stopped()):
                        event=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,self.loginprocess)
                        wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),event)
                        event=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_QUESTION_KILL_SERVER,self.loginprocess)
                        wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),event)

                except Exception as e:
                    self.loginprocess.cancel("Couldn't start the vnc viewer: %s"%e)
            else:
                    self.loginprocess.cancel("Couldn't start the vnc viewer. There was no password set")
        
    class startServerThread(Thread):
        def __init__(self,loginprocess):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
    
        def stop(self):
            logger_debug("stopping the thread that starts the VNC viewer")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            sshCmd = self.loginprocess.sshCmd
            (stdout, stderr) = run_ssh_command(sshCmd.format(**self.loginprocess.jobParams), self.loginprocess.startServerCmd.format(**self.loginprocess.jobParams),ignore_errors=True, callback=self.loginprocess.cancel)
            started=False
            import itertools
            for line  in itertools.chain(stdout.split('\n'),stderr.split('\n')):
                match=re.search(self.loginprocess.startServerRegEx.format(**self.loginprocess.jobParams),line)
                if (match):
                    print "matched the startServerRegEx %s"%line
                    self.loginprocess.jobParams.update(match.groupdict())
                    self.loginprocess.started_job.set()
                    started=True
                    break
                else:
                    print "didn't match the startServerRegEx %s"%line
            if (not started):
                self.loginprocess.cancel("I was unable to start the VNC server")
                return
            if (not self.stopped()):
                event=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CONNECT_SERVER,self.loginprocess)
                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),event)

    class getExecutionHostThread(Thread):
        def __init__(self,loginprocess):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
    
        def stop(self):
            logger_debug("stopping the thread that determines the execution host")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            notStarted=True
            tsleep=0
            sleepperiod=1
            jobRunning=None
            # Make local copies, just because I tired of typing "self.loginprocess."
            runningCmd=self.loginprocess.runningCmd
            runningRegEx=self.loginprocess.runningRegEx
            execHostCmd=self.loginprocess.execHostCmd
            execHostRegEx=self.loginprocess.execHostRegEx
            sshCmd = self.loginprocess.sshCmd
            jobParams=self.loginprocess.jobParams
            while (not jobRunning and not self.stopped()):
                tsleep+=sleepperiod
                if (not self.stopped()):
                    time.sleep(sleepperiod)
                try:
                    (stdout,stderr) = run_ssh_command(sshCmd.format(**jobParams),runningCmd.format(**jobParams),ignore_errors=True)
                except KeyError as e:
                    self.loginprocess.cancel("Trying to check if the job is running yet, I was missing a parameter %s"%e)
                    return
                
                for line in stdout.split('\n'):
                    if (not self.stopped()):
                        try:
                            regex=runningRegEx.format(**jobParams)
                            logger_debug("searching the output of %s using regex %s"%(runningCmd.format(**jobParams),regex))
                        except KeyError as e:
                            logger_error("Trying to check if the job is running yet, unable to formulate regex, missing parameter %s"%e)
                            self.loginprocess.cancel("Sorry, a catastropic error occured and I was unable to connect to your VNC session")
                            return
                        jobRunning = re.search(regex,line)
                        if (jobRunning):
                            print "job is running"
                            self.loginprocess.jobParams.update(jobRunning.groupdict())
                            break
                        if (not jobRunning and tsleep == 1):
                            sleepperiod=15
                        if (not jobRunning and tsleep > 15 and self.loginprocess.showStartCmd!=None):
                            stdoutRead, stderrRead = run_ssh_command(sshCmd.format(**jobParams),self.loginprocess.showStartCmd.format(**jobParams),ignore_errors=True)
                            if not "00:00:00" in stdoutRead:
                                logger_debug("showstart " + self.loginprocess.jobParams['jobid'] + "...")
                                logger_debug('showstart stderr: ' + stderrRead)
                                logger_debug('showstart stdout: ' + stdoutRead)
                          
                                showstartLines = stdoutRead.split("\n")
                                for showstartLine in showstartLines:
                                    if showstartLine.startswith("Estimated Rsv based start"):
                                        showstartLineComponents = showstartLine.split(" on ")
                                        if not showstartLineComponents[1].startswith("-"):
                                            wx.CallAfter(self.loginprocess.updateProgressDialog, 6, "Estimated start: " + showstartLineComponents[1])
                            sleepperiod=30
            # Loop until we figure out which host the vnc server was started on.
            print "job is running, looking for execHost"
            execHost = None
            jobParams=self.loginprocess.jobParams
            while (not execHost and not self.stopped()):
                try:
                    (stdout,stderr) = run_ssh_command(sshCmd.format(**jobParams),execHostCmd.format(**jobParams),ignore_errors=True)
                except KeyError as e:
                    logger_error("execHostCmd missing parameter %s"%e)
                    self.loginprocess.cancel("Sorry, a catastropic error occured and I was unable to connect to your VNC session")
                lines = stdout.split('\n')
                for line in lines:
                    if (not self.stopped()):
                        try:
                            execHost = re.search(execHostRegEx.format(**jobParams),line)
                        except KeyError as e:
                            logger_error("execHostRegEx missing parameter %s"%e)
                            self.loginprocess.cancel("Sorry, a catastropic error occured and I was unable to connect to your VNC session")
                            return
                        if (execHost):
                            self.loginprocess.jobParams.update(execHost.groupdict())
                            break
            if (not self.stopped()):
                logger_debug("in getExecutionHost, posting START_TUNNEL")
                event=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_TUNNEL,self.loginprocess)
                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),event)

    class killServerThread(Thread):
        def __init__(self,loginprocess,restart):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.restart = restart
    
        def stop(self):
            logger_debug("stopping the killServerThread (this won't really stop killing the server, but it will stop any further actions events being posted)")
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            try:
                stdoutRead, stderrRead = run_ssh_command(self.loginprocess.sshCmd.format(**self.loginprocess.jobParams),self.loginprocess.stopCmd.format(**self.loginprocess.jobParams), ignore_errors=True,callback=self.loginprocess.cancel)
            except KeyError as e:
                logger_error("stopCmd missing parameter %s"%e)
                self.loginprocess.cancel("Sorry, an error occured and I was unable to shutdown your VNC session")
                return
            if (not self.stopped()):
                if (self.restart):
                    event=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_SERVER,self.loginprocess)
                else:
                    event=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_NORMAL_TERMINATION,self.loginprocess)
                self.loginprocess.vncJobID=None
                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),event)

    class CheckExistingDesktop(Thread):
        def __init__(self,loginprocess,callback_found,callback_notfound):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
            self.loginprocess.joblist=[]
            self.callback_found=callback_found
            self.callback_notfound=callback_notfound
    
        def stop(self):
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            self.loginprocess.job=None
            try:
                (stdout,stderrr) = run_ssh_command(self.loginprocess.sshCmd.format(**self.loginprocess.jobParams),self.loginprocess.listAllCmd.format(**self.loginprocess.jobParams),ignore_errors=True)
            except KeyError as e:
                logger_error("listAllCmd missing parameter %s"%e)
                self.loginprocess.cancel("Sorry, an error occured and I was unable to determine if you already have any running desktops")
                return
            lines = stdout.split('\n')
            for line in lines:
                try:
                    regex = self.loginprocess.listAllRegEx.format(**self.loginprocess.jobParams)
                except KeyError as e:
                    logger_error("listAllRegEx missing parameter %s"%e)
                    self.loginprocess.cancel("Sorry, an error occured and I was unable to determine if you already have any running desktops")
                    return
                match=re.search(regex,line)
                if match:
                    self.loginprocess.joblist.append(match.groupdict())

            # Currently only capabale of dealing with one existing Desktop at a time (as is MASSIVE policy)
            # TODO make a nice dialog here to select which job you are talking about from a list of jobs.
            if (self.loginprocess.joblist!=[]):
                self.loginprocess.job=self.loginprocess.joblist[-1]
                self.loginprocess.jobParams.update(self.loginprocess.job)

            if (not self.stopped()):
                if (self.loginprocess.job !=None):
                    self.callback_found()
                else:
                    self.callback_notfound()

    class CheckVNCVerThread(Thread):
        def __init__(self,loginprocess):
            Thread.__init__(self)
            self.loginprocess = loginprocess
            self._stop = Event()
    
        def stop(self):
            logger_debug("stop called on CheckVNCVerThread") 
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

            return (vnc, turboVncVersionNumber)

        def getTurboVncVersionNumber(self,vnc):
            self.turboVncVersionNumber = "0.0"

            turboVncVersionNumberCommandString = vnc + " -help"
            proc = subprocess.Popen(turboVncVersionNumberCommandString,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                universal_newlines=True)
            turboVncStdout, turboVncStderr = proc.communicate(input="\n")
            if turboVncStderr != None:
                logger_debug("turboVncStderr: " + turboVncStderr)
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
                logger_debug('turboVncFlavour stderr: ' + stderr)
            if proc.returncode==0:
                logger_debug("Java version of TurboVNC Viewer is installed.")
                turboVncFlavour = "Java"
            else:
                logger_debug("X11 version of TurboVNC Viewer is installed.")
                turboVncFlavour = "X11"
            
            return (vnc,turboVncVersionNumber,turboVncFlavour)

        def showTurboVncNotFoundMessageDialog(loginprocess):
            turboVncNotFoundDialog = wx.Dialog(self.notify_window, title="MASSIVE/CVL Launcher", name="MASSIVE/CVL Launcher",pos=(200,150),size=(680,290))

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


            okButton = wx.Button(turboVncNotFoundPanel, 1, ' OK ')
            okButton.SetDefault()
            turboVncNotFoundPanelSizer.Add(okButton, flag=wx.ALIGN_RIGHT)
            turboVncNotFoundPanelSizer.Add(wx.StaticText(turboVncNotFoundPanel))
            turboVncNotFoundPanelSizer.Fit(turboVncNotFoundPanel)


            turboVncNotFoundDialogSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=5, hgap=5)
            turboVncNotFoundDialogSizer.Add(massiveIconPanel, flag=wx.EXPAND)
            turboVncNotFoundDialogSizer.Add(turboVncNotFoundPanel, flag=wx.EXPAND)
            turboVncNotFoundDialogSizer.Add(wx.StaticText(turboVncNotFoundDialog,label="       "))
            turboVncNotFoundDialog.SetSizer(turboVncNotFoundDialogSizer)
            turboVncNotFoundDialogSizer.Fit(turboVncNotFoundDialog)

            turboVncNotFoundDialog.ShowModal()
            turboVncNotFoundDialog.Destroy()

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
                    print e
                    logger_debug("Exception while checking TurboVNC version number.")

                    def error_dialog():
                        dlg = wx.MessageDialog(self.notify_window, "Error: Unable to contact MASSIVE website to check the TurboVNC version number.\n\n" +
                                                "The launcher cannot continue.\n",
                                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                        dlg.ShowModal()
                        dlg.Destroy()
                        # If we can't contact the MASSIVE website, it's probably because
                        # there's no active network connection, so don't try to submit
                        # the log to cvl.massive.org.au
                        dump_log(self.notify_window,submit_log=False)
                        sys.exit(1)
                    wx.CallAfter(error_dialog)

                turboVncLatestVersion = myHtmlParser.latestVersionNumber
            else:
                turboVncLatestVersion = ''
            turboVncLatestVersion = ''

            turboVncVersionNumber = None

            if sys.platform.startswith("win"):
                (vnc, turboVncVersionNumber) = self.getTurboVncVersionNumber_Windows()
                turboVncFlavour = None
            else:
                vnc = "/opt/TurboVNC/bin/vncviewer"
                (vnc,turboVncVersionNumber,turboVncFlavour) = self.getTurboVncVersionNumber(vnc)

            if turboVncVersionNumber is None:
                def error_dialog():
                    dlg = wx.MessageDialog(self.loginprocess.notify_window, "Error: Could not determine TurboVNC version number.\n\n" +
                                            "The launcher cannot continue.\n",
                                    "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                    dlg.ShowModal()
                    dlg.Destroy()
                    dump_log(self.loginprocess.notify_window)
                    sys.exit(1)

                if (self.loginprocess.notify_window.progressDialog != None):
                    wx.CallAfter(self.loginprocess.notify_window.progressDialog.Hide)
                    wx.CallAfter(self.loginprocess.notify_window.progressDialog.Show, False)
                    wx.CallAfter(self.loginprocess.notify_window.progressDialog.Destroy)
                    self.loginprocess.notify_window.progressDialog = None

                wx.CallAfter(error_dialog)
                return

            if os.path.exists(vnc):
                logger_debug("TurboVNC was found in " + vnc)
            else:
                self.loginprocess.cancel("TurboVNC not found")
                wx.CallAfter(showTurboVncNotFoundMessageDialog)

            logger_debug("TurboVNC viewer version number = " + turboVncVersionNumber)
            
            #self.loginprocess.turboVncVersionNumber = turboVncVersionNumber
            self.loginprocess.jobParams['vnc'] = vnc
            self.loginprocess.jobParams['turboVncFlavour'] = turboVncFlavour
            self.loginprocess.jobParams['vncOptionsString'] = self.loginprocess.buildVNCOptionsString()

            if turboVncVersionNumber.startswith("0.") or turboVncVersionNumber.startswith("1.0"):
                def showOldTurboVncWarningMessageDialog():
                    dlg = wx.MessageDialog(self.notify_window, "Warning: Using a TurboVNC viewer earlier than v1.1 means that you will need to enter your password twice.\n",
                                    "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                    dlg.ShowModal()
                    dlg.Destroy()
                    logger_debug("vnc viewer found, user warned about old version")
                wx.CallAfter(showOldTurboVncWarningMessageDialog)
            else:
                logger_debug("vnc viewer found")
            if (not self.stopped()):
                event=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_DISTRIBUTE_KEY,self.loginprocess)
                wx.PostEvent(self.loginprocess.notify_window.GetEventHandler(),event)

    class loginProcessEvent(wx.PyCommandEvent):
        def __init__(self,id,loginprocess,string=""):
            wx.PyCommandEvent.__init__(self,LoginProcess.myEVT_CUSTOM_LOGINPROCESS,id)
            self.loginprocess = loginprocess
            self.string = string

        def showReconnectDialog(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RECONNECT_DIALOG):
                wx.CallAfter(event.loginprocess.updateProgressDialog, 4,"Do you want to reconnect to an existing desktop?")
                ReconnectCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CONNECT_SERVER,event.loginprocess))
                NewDesktopCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER,event.loginprocess))
                timeRemaining=event.loginprocess.timeRemaining()
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
                    timestring = str(datetime.timedelta(seconds=event.loginprocess.timeRemaining))
                    dialog=LoginProcess.SimpleOptionDialog(event.loginprocess.notify_window,-1,"Reconnect to Existing Desktop","An Existing Desktop was found. It has %s remaining. Would you like to reconnect or kill it and start a new desktop"%timestring,"Reconnect","New Desktop",ReconnectCallback,NewDesktopCallback)
                else:
                    dialog=LoginProcess.SimpleOptionDialog(event.loginprocess.notify_window,-1,"Reconnect to Existing Desktop","An Existing Desktop was found, would you like to reconnect or kill it and start a new desktop","Reconnect","New Desktop",ReconnectCallback,NewDesktopCallback)
                wx.CallAfter(dialog.ShowModal)
            else:
                event.Skip()

        def normalTermination(event):
            # This event is generated if we shutdown the VNC server upon exit. Its basically a no-op, and moves onto processing the shutdown sequence of events
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_NORMAL_TERMINATION):
                wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_COMPLETE,event.loginprocess))
            else:
                event.Skip()

        def showKillServerDialog(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_QUESTION_KILL_SERVER):
                KillCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_KILL_SERVER,event.loginprocess))
                NOOPCallback=lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_COMPLETE,event.loginprocess))
                dialog=LoginProcess.SimpleOptionDialog(event.loginprocess.notify_window,-1,"Stop the Desktop?","Would you like to leave the desktop running so you can reconnect latter?","Stop the desktop","Leave it running",KillCallback,NOOPCallback)
                wx.CallAfter(dialog.ShowModal)
            else:
                event.Skip()

        def connectServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_CONNECT_SERVER):
                wx.CallAfter(event.loginprocess.updateProgressDialog, 6,"Getting the node name")
                logger_debug("caught event CONNECT_SERVER")
                t = LoginProcess.getExecutionHostThread(event.loginprocess)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()


        def killServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER or event.GetId() == LoginProcess.EVT_LOGINPROCESS_KILL_SERVER):
                wx.CallAfter(event.loginprocess.updateProgressDialog, 4,"Stoping the existing desktop session")
                if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER):
                    logger_debug("caught an EVT_LOGINPROCESS_RESTART_SERVER")
                    restart=True
                else:
                    logger_debug("caught an EVT_LOGINPROCESS_KILL_SERVER")
                    restart=False
                t = LoginProcess.killServerThread(event.loginprocess,restart)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def startServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_SERVER):
                wx.CallAfter(event.loginprocess.updateProgressDialog, 5,"Starting a new desktop session")
                logger_debug("caught an EVT_LOGINPROCESS_START_SERVER")
                t = LoginProcess.startServerThread(event.loginprocess)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()
    
        def checkVNCVer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_CHECK_VNC_VER):
                logger_debug("caught an EVT_LOGINPROCESS_CHECK_VNC_VER")
                wx.CallAfter(event.loginprocess.updateProgressDialog, 1,"Checking VNC Version")
                t = LoginProcess.CheckVNCVerThread(event.loginprocess)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
                logger_debug("starting a thread to find the VNC Viewer")
            else:
                event.Skip()

        def distributeKey(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_DISTRIBUTE_KEY):
                wx.CallAfter(event.loginprocess.updateProgressDialog, 2,"Configuring Authorisation")
                event.loginprocess.skd = sshKeyDist.KeyDist(event.loginprocess.jobParams['username'],event.loginprocess.jobParams['loginHost'],event.loginprocess.notify_window,event.loginprocess.sshpaths)
                successevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CHECK_RUNNING_SERVER,event.loginprocess)
                event.loginprocess.skd.distributeKey(lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),successevent),
                                                     event.loginprocess.cancel)
            else:
                event.Skip()


        def checkRunningServer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_CHECK_RUNNING_SERVER):
                logger_debug("caught LOGINPROCESS_CHECK_RUNNING_SERVER event")
                event.loginprocess.skd = None # SSH key distritbution is complete at this point.
                wx.CallAfter(event.loginprocess.updateProgressDialog, 3,"Looking for an existing desktop to connect to")
                reconnectdialogevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_RECONNECT_DIALOG,event.loginprocess)
                newdesktopevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_START_SERVER,event.loginprocess)
                t = LoginProcess.CheckExistingDesktop(event.loginprocess,lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),reconnectdialogevent),lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),newdesktopevent))
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def forwardAgent(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_FORWARD_AGENT):
                logger_debug("recieved FORWARD_AGENT event")
                wx.CallAfter(event.loginprocess.updateProgressDialog, 8,"Setting up SSH Agent forwarding")
                successCallback = lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_GET_OTP,event.loginprocess))
                failCallback = lambda: event.loginprocess.cancel("Unable to forward the ssh agent")
                t = LoginProcess.forwardAgentThread(event.loginprocess,successCallback,failCallback)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()
        
        def startTunnel(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_TUNNEL):
                wx.CallAfter(event.loginprocess.updateProgressDialog, 7,"Starting the tunnel")
                logger_debug("recieved START_TUNNEL event")
                print "receieved START_TUNNEL event"
                event.loginprocess.localPortNumber = "0" # Request ephemeral port.
                testRun = False
                successCallback = lambda: wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_FORWARD_AGENT,event.loginprocess))
                failCallback = lambda: event.loginprocess.cancel("Unable to start the tunnel for some reason")
                t = LoginProcess.createTunnelThread(event.loginprocess,successCallback,failCallback)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def getVNCPassword(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_GET_OTP):
                wx.CallAfter(event.loginprocess.updateProgressDialog, 9,"Getting the one time password for the VNC server")
                logger_debug("recieved GET_OTP event")
                t = LoginProcess.getOTPThread(event.loginprocess)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def startViewer(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_START_VIEWER):
                wx.CallAfter(event.loginprocess.updateProgressDialog, 9,"Starting the VNC viewer")
                logger_debug("recieved START_VIEWER event")
                t = LoginProcess.startVNCViewer(event.loginprocess)
                t.setDaemon(False)
                t.start()
                event.loginprocess.threads.append(t)
            else:
                event.Skip()

        def shutdown(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_SHUTDOWN):
                for t in event.loginprocess.threads:
                    try:
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
            else:
                event.Skip()

        def cancel(event):
            if (event.GetId() == LoginProcess.EVT_LOGINPROCESS_CANCEL):
                if event.loginprocess.started_job.isSet():
                    t = LoginProcess.killServerThread(event.loginprocess,False)
                    t.setDaemon(True)
                    t.start()
                    event.loginprocess.threads.append(t)
                print "caught LOGINPROCESS_CANCEL"
                if (event.loginprocess.skd!=None): 
                        event.loginprocess.skd.cancel()
                newevent=LoginProcess.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_SHUTDOWN,event.loginprocess)
                wx.PostEvent(event.loginprocess.notify_window.GetEventHandler(),newevent)
                if (event.string!=""):
                    dlg = wx.MessageDialog(event.loginprocess.notify_window, event.string,
                    "Launcher", wx.OK | wx.ICON_INFORMATION)
                    wx.CallAfter(dlg.ShowModal)

            else:
                event.Skip()

    myEVT_CUSTOM_LOGINPROCESS=None
    EVT_CUSTOM_LOGINPROCESS=None
    def __init__(self,username,host,resolution,cipher,notifywindow,sshpaths,project=None,hours=None,nodes=1,usePBS=True,directConnect=False,fastInterface="-ib"):
        LoginProcess.myEVT_CUSTOM_LOGINPROCESS=wx.NewEventType()
        LoginProcess.EVT_CUSTOM_LOGINPROCESS=wx.PyEventBinder(self.myEVT_CUSTOM_LOGINPROCESS,1)
        self.notify_window = notifywindow
        self.loginParams={}
        self.jobParams={}
        self.loginParams['username']=username
        self.loginParams['loginHost']=host
        self.loginParams['project']=project
        self.loginParams['sshBinary']=sshpaths.sshBinary
        self.jobParams['resolution']=resolution
        self.jobParams['cipher']=cipher
        self.jobParams.update(self.loginParams)
        self.sshpaths=sshpaths
        self.threads=[]
        self.jobParams['project']=project
        self.jobParams['hours']=hours
        self.jobParams['nodes']=nodes
        self._canceled=threading.Event()
        self.usePBS=usePBS
        self.directConnect = directConnect
        self.sshCmd = '{sshBinary} -A -T -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o StrictHostKeyChecking=yes -l {username} {loginHost} '
        self.sshTunnelProcess=None
        self.sshAgentProcess=None
        self.fastInterface="-ib"
        self.joblist=[]
        self.started_job=threading.Event()
        self.skd=None


        if (self.usePBS):
            self.listAllCmd='qstat -u {username}'
            self.listAllRegEx='^\s*(?P<jobid>(?P<jobidNumber>[0-9])\.\S+)\s+{username}\s+(?P<queue>\S+)\s+(?P<jobname>desktop_{username})\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>[^C])\s+(?P<elapTime>\S+)\s*$'
            self.runningCmd='qstat -u {username}'
            self.runningRegEx='^\s*(?P<jobid>{jobid})\s+{username}\s+(?P<queue>\S+)\s+(?P<jobname>desktop_{username})\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>R)\s+(?P<elapTime>\S+)\s*$'
            self.stopCmd='qdel {jobid}'
            self.execHostCmd='qpeek {jobidNumber}'
            self.execHostRegEx='\s*To access the desktop first create a secure tunnel to (?P<execHost>\S+)\s*$'
            self.startServerCmd="/usr/local/desktop/request_visnode.sh {project} {hours} {nodes} True False False"
            self.startServerRegEx="^(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s*$"
            self.showStartCmd="showstart {jobid}"
        else:
            self.listAllCmd='"module load turbovnc ; vncserver -list"'
            self.listAllRegEx='^(?P<vncDisplay>:[0-9]+)\s*(?P<vncPID>[0-9]+)\s*$'
            self.runningCmd='"module load turbovnc ; vncserver -list"'
            self.runningRegEx='^(?P<vncDisplay>{vncDisplay})\s*(?P<vncPID>[0-9]+)\s*$'
            self.stopCmd='"module load turbovnc ; vncserver -kill {vncDisplay}"'
            self.execHostCmd='echo execHost: {loginHost}'
            self.execHostRegEx='^\s*execHost: (?P<execHost>\S+)\s*$'
            self.startServerCmd = "vncsession --vnc turbovnc --geometry {resolution}"
            self.startServerRegEx="^.*started on display \S+(?P<vncDisplay>:[0-9]+).*$"
            self.showStartCmd=None

        if (not self.directConnect):
            self.agentCmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -l {username} {loginHost} \"/usr/bin/ssh -A {execHost} \\"echo agent_hello; bash \\"\"'
            self.agentRegEx='agent_hello'
            self.tunnelCmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -L {localPortNumber}:{execHost}:{remotePortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"'
            self.tunnelRegEx='tunnel_hello'
            self.otpCmd = '{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -l {username} {loginHost} \"/usr/bin/ssh {execHost} \\"module load turbovnc ; vncpasswd -o -display localhost{vncDisplay} \\"\"'
            self.otpRegEx='^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$'
        else:
            self.agentCmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -l {username} {execHost} "echo agent_hello; bash "'
            self.agentRegEx='agent_hello'
            self.tunnelCmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -L {localPortNumber}:localhost:{remotePortNumber} -l {username} {execHost} "echo tunnel_hello; bash"'
            self.tunnelRegEx='tunnel_hello'
            self.otpCmd = '{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -l {username} {execHost} "module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}"'
            self.otpRegEx='^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$'

        LoginProcess.EVT_LOGINPROCESS_CHECK_VNC_VER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_DISTRIBUTE_KEY = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_CHECK_RUNNING_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_GET_OTP = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_START_TUNNEL = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_RUN_VNCVIEWER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_ASK_TERMINATE_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_RECONNECT_DIALOG = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_CONNECT_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_KILL_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_START_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_RESTART_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_NORMAL_TERMINATION = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_CANCEL = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_FORWARD_AGENT = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_START_VIEWER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_QUESTION_KILL_SERVER = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_COMPLETE = wx.NewId()
        LoginProcess.EVT_LOGINPROCESS_SHUTDOWN = wx.NewId()

        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.cancel)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.distributeKey)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.checkRunningServer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.checkVNCVer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.showReconnectDialog)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.killServer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.startServer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.startTunnel)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.connectServer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.forwardAgent)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.getVNCPassword)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.startViewer)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.showKillServerDialog)
        self.notify_window.Bind(self.EVT_CUSTOM_LOGINPROCESS, LoginProcess.loginProcessEvent.shutdown)

    def timeRemaining(self):
        job=self.job
        if job != None:
            if (job.has_key('reqTime') and job.has_key('elapTime') and job.has_key['state']):
                if (job['state']=='R'):
                    (rhours,rmin) = job['reqTime'].split(':')
                    (ehours,emin) = job['elapTime'].split(':')
                    return (int(rhours)-int(ehours))*60*60 + (int(rmin)-int(emin))*60
                else:
                    (rhours,rmin) = job['reqTime'].split(':')
                    ehours=0
                    emin=0
                    return (int(rhours)-int(ehours))*60*60 + (int(rmin)-int(emin))*60
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
            event=self.loginProcessEvent(LoginProcess.EVT_LOGINPROCESS_CANCEL,self,error)
            wx.PostEvent(self.notify_window.GetEventHandler(),event)
            #logger_error("LoginTasks.cancel error message %s"%error)


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
