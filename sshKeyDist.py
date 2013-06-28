import os
import subprocess
import ssh
import wx
import wx.lib.newevent
import re
from StringIO import StringIO
import logging
from threading import *
import time
import sys
from os.path import expanduser
import subprocess
import traceback
from utilityFunctions import logger_debug, logger_error

OPENSSH_BUILD_DIR = 'openssh-cygwin-stdin-build'

if not sys.platform.startswith('win'):
    import pexpect

def is_pageant_running():
    username = os.path.split(os.path.expanduser('~'))[-1]
    return 'PAGEANT.EXE' in os.popen('tasklist /FI "USERNAME eq %s"' % username).read()

def start_pageant():
    if is_pageant_running():
        # Pageant pops up a dialog box if we try to run a second
        # instance, so leave immediately.
        return

    if hasattr(sys, 'frozen'):
        pageant = os.path.join(os.path.dirname(sys.executable), OPENSSH_BUILD_DIR, 'bin', 'PAGEANT.EXE')
    else:
        pageant = os.path.join(os.getcwd(), OPENSSH_BUILD_DIR, 'bin', 'PAGEANT.EXE')

    import win32process
    subprocess.Popen([pageant], creationflags=win32process.DETACHED_PROCESS)

def double_quote(x):
    return '"' + x + '"'

class sshpaths():
    def ssh_binaries(self):
        """
        Locate the ssh binaries on various systems. On Windows we bundle a
        stripped-down OpenSSH build that uses Cygwin.
        """
 
        if sys.platform.startswith('win'):
            if hasattr(sys, 'frozen'):
                f = lambda x: os.path.join(os.path.dirname(sys.executable), OPENSSH_BUILD_DIR, 'bin', x)
            else:
                f = lambda x: os.path.join(os.getcwd(), OPENSSH_BUILD_DIR, 'bin', x)
 
            sshBinary        = f('ssh.exe')
            sshKeyGenBinary  = f('ssh-keygen.exe')
            sshKeyScanBinary = f('ssh-keyscan.exe')
            sshAgentBinary   = f('charade.exe')
            sshAddBinary     = f('ssh-add.exe')
            chownBinary      = f('chown.exe')
            chmodBinary      = f('chmod.exe')
        elif sys.platform.startswith('darwin'):
            sshBinary        = '/usr/bin/ssh'
            sshKeyGenBinary  = '/usr/bin/ssh-keygen'
            sshKeyScanBinary = '/usr/bin/ssh-keyscan'
            sshAgentBinary   = '/usr/bin/ssh-agent'
            sshAddBinary     = '/usr/bin/ssh-add'
            chownBinary      = '/usr/sbin/chown'
            chmodBinary      = '/bin/chmod'
        else:
            sshBinary        = '/usr/bin/ssh'
            sshKeyGenBinary  = '/usr/bin/ssh-keygen'
            sshKeyScanBinary = '/usr/bin/ssh-keyscan'
            sshAgentBinary   = '/usr/bin/ssh-agent'
            sshAddBinary     = '/usr/bin/ssh-add'
            chownBinary      = '/bin/chown'
            chmodBinary      = '/bin/chmod'
 
        return (sshBinary, sshKeyGenBinary, sshAgentBinary, sshAddBinary, sshKeyScanBinary, chownBinary, chmodBinary,)
    
    def ssh_files(self):
        known_hosts_file = os.path.join(expanduser('~'), '.ssh', 'known_hosts')
        sshKeyPath = os.path.join(expanduser('~'), '.ssh', 'MassiveLauncherKey')
        return (sshKeyPath,known_hosts_file,)

    def __init__(self):
        (sshBinary, sshKeyGenBinary, sshAgentBinary, sshAddBinary, sshKeyScanBinary,chownBinary, chmodBinary,) = self.ssh_binaries()
        (sshKeyPath,sshKnownHosts,) = self.ssh_files()
        self.sshBinary = sshBinary
        self.sshKeyGenBinary = sshKeyGenBinary
        self.sshAgentBinary = sshAgentBinary
        self.sshAddBinary = sshAddBinary
        self.sshKeyScanBinary = sshKeyScanBinary
        self.chownBinary = chownBinary
        self.chmodBinary = chmodBinary

        self.sshKeyPath = sshKeyPath
        self.sshKnownHosts = sshKnownHosts

class KeyDist():

    def complete(self):
        self.completedLock.acquire()
        returnval = self.completed
        self.completedLock.release()
        return returnval

    class passphraseDialog(wx.Dialog):

        def __init__(self, parent, id, title, text, okString, cancelString):
            wx.Dialog.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER | wx.STAY_ON_TOP)
            self.SetTitle(title)
            self.panel = wx.Panel(self,-1)
            self.label = wx.StaticText(self.panel, -1, text)
            self.PassphraseField = wx.TextCtrl(self.panel, wx.ID_ANY, style=wx.TE_PASSWORD ^ wx.TE_PROCESS_ENTER)
            self.PassphraseField.SetFocus()
            self.Cancel = wx.Button(self.panel,-1,label=cancelString)
            self.OK = wx.Button(self.panel,-1,label=okString)

            self.sizer = wx.FlexGridSizer(2, 2, 5, 5)
            self.sizer.Add(self.label)
            self.sizer.Add(self.PassphraseField)
            self.sizer.Add(self.Cancel)
            self.sizer.Add(self.OK)

            self.PassphraseField.Bind(wx.EVT_TEXT_ENTER,self.onEnter)
            self.OK.Bind(wx.EVT_BUTTON,self.onEnter)
            self.Cancel.Bind(wx.EVT_BUTTON,self.onEnter)

            self.border = wx.BoxSizer()
            self.border.Add(self.sizer, 0, wx.ALL, 15)
            self.panel.SetSizerAndFit(self.border)
            self.Fit()
            self.password = None

        def onEnter(self,e):
            if (e.GetId() == self.Cancel.GetId()):
                self.canceled = True
                self.password = None
            else:
                self.canceled = False
                self.password = self.PassphraseField.GetValue()
            self.Close()


        def getPassword(self):
            val = self.ShowModal()
            passwd = self.password
            canceled = self.canceled
            self.Destroy()
            return (canceled,passwd)

    class startAgentThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject
            self._stop = Event()

        def stop(self):
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()


        def run(self):
            agentenv = None
            try:
                agentenv = os.environ['SSH_AUTH_SOCK']
            except:
                try:
                    agent = subprocess.Popen(self.keydistObject.sshpaths.sshAgentBinary,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
                    stdout = agent.stdout.readlines()
                    for line in stdout:
                        if sys.platform.startswith('win'):
                            match = re.search("^SSH_AUTH_SOCK=(?P<socket>.*);.*$",line) # output from charade.exe doesn't match the regex, even though it looks the same!?
                        else:
                            match = re.search("^SSH_AUTH_SOCK=(?P<socket>.*); export SSH_AUTH_SOCK;$",line)
                        if match:
                            agentenv = match.group('socket')
                            os.environ['SSH_AUTH_SOCK'] = agentenv
                    if agent is None:
                        self.keydistObject.cancel(message="I tried to start and ssh agent, but failed with the error message %s"%str(stdout))
                        return
                except Exception as e:
                    self.keydistObject.cancel(message="I tried to start and ssh agent, but failed with the error message %s" % str(e))
                    return

            newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_GETPUBKEY,self.keydistObject)
            if (not self.stopped()):
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)

    class genkeyThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject
            self._stop = Event()

        def stop(self):
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            logger_debug("executing genkeyThread, run method")
            cmd = '{sshkeygen} -q -f "{keyfilename}" -C "{keycomment}" -N \"{password}\"'.format(sshkeygen=self.keydistObject.sshpaths.sshKeyGenBinary,
                                                                                                 keyfilename=self.keydistObject.sshpaths.sshKeyPath,
                                                                                                 keycomment=self.keydistObject.launcherKeyComment,
                                                                                                 password=self.keydistObject.password)
            try:
                keygen_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
                (stdout,stderr) = keygen_proc.communicate("\n\n")
                logger_debug("sshkeygen completed")
                if (stderr != None):
                    logger_debug("key gen proc returned an error %s"%stderr)
                    self.keydistObject.cancel("Unable to generate a new ssh key pair %s"%stderr)
                    return
                if (stdout != None):
                    logger_error("key gen proc returned a message %s"%stdout)
                    #self.keydistObject.cancel("Unable to generate a new ssh key pair %s"%stderr)
                    #return
            except Exception as e:
                logger_debug("sshkeygen threw and exception %s" % str(e))
                self.keydistObject.cancel("Unable to generate a new ssh key pair: %s" % str(e))
                return


            try:
                logger_debug("sshkeygen completed, trying to open the key file")
                with open(self.keydistObject.sshpaths.sshKeyPath,'r'): pass
                event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_LOADKEY,self.keydistObject) # Auth hasn't really failed but this event will trigger loading the key
            except Exception as e:
                logger_error("ssh key gen failed %s" % str(e))
                self.keydistObject.cancel("Unable to generate a new ssh key pair %s" % str(e))
                return
            if (not self.stopped()):
                logger_debug("generating LOADKEY event from genkeyThread")
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),event)

    class getPubKeyThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject
            self._stop = Event()

        def stop(self):
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            sshKeyListCmd = self.keydistObject.sshpaths.sshAddBinary + " -L "
            keylist = subprocess.Popen(sshKeyListCmd, stdout = subprocess.PIPE,stderr=subprocess.STDOUT,shell=True,universal_newlines=True)
            (stdout,stderr) = keylist.communicate()
            self.keydistObject.pubkeylock.acquire()

            logger_debug('getPubKeyThread: stdout of ssh-add -l: ' + str(stdout))
            logger_debug('getPubKeyThread: stderr of ssh-add -l: ' + str(stderr))

            lines = stdout.split('\n')
            logger_debug("ssh key list completed")
            for line in lines:
                match = re.search("^(?P<keytype>\S+)\ (?P<key>\S+)\ (?P<keycomment>.+)$",line)
                if match:
                    keycomment = match.group('keycomment')
                    correctKey = re.search('.*{launchercomment}.*'.format(launchercomment=self.keydistObject.launcherKeyComment),keycomment)
                    if correctKey:
                        self.keydistObject.keyloaded = True
                        logger_debug('getPubKeyThread: loaded key successfully')
                        self.keydistObject.pubkey = line.rstrip()
            logger_debug("all lines processed")
            if (self.keydistObject.keyloaded):
                logger_debug("key loaded")
                logger_debug("getPubKeyThread found a key, posting TESTAUTH")
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_TESTAUTH,self.keydistObject)
            else:
                logger_debug("getPubKeyThread did not find a key, posting LOADKEY")
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_LOADKEY,self.keydistObject)
            self.keydistObject.pubkeylock.release()
            if (not self.stopped()):
                logger_debug("getPubKeyThread is posting the next event")
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)

    class scanHostKeysThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject
            self.ssh_keygen_cmd = '{sshkeygen} -F {host} -f {known_hosts_file}'.format(sshkeygen=self.keydistObject.sshpaths.sshKeyGenBinary,host=self.keydistObject.host,known_hosts_file=self.keydistObject.sshpaths.sshKnownHosts)
            self.ssh_keyscan_cmd = '{sshscan} -H {host}'.format(sshscan=self.keydistObject.sshpaths.sshKeyScanBinary,host=self.keydistObject.host)
            self._stop = Event()

        def stop(self):
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def getKnownHostKeys(self):
            keygen = subprocess.Popen(self.ssh_keygen_cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,universal_newlines=True)
            stdout,stderr = keygen.communicate()
            keygen.wait()
            hostkeys=[]
            for line in stdout.split('\n'):
                if (not (line.find('#')==0 or line == '')):
                    hostkeys.append(line)
            return hostkeys
                    
        def appendKey(self,key):
            with open(self.keydistObject.sshpaths.sshKnownHosts,'a+') as known_hosts:
                known_hosts.write(key)
                known_hosts.write('\n')
            

        def scanHost(self):
            scan = subprocess.Popen(self.ssh_keyscan_cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,universal_newlines=True)
            stdout,stderr = scan.communicate()
            scan.wait()
            hostkeys=[]
            for line in stdout.split('\n'):
                if (not (line.find('#')==0 or line == '')):
                    hostkeys.append(line)
            return hostkeys

        def run(self):
            knownKeys = self.getKnownHostKeys()
            if (len(knownKeys)==0):
                hostKeys = self.scanHost()
                for key in hostKeys:
                    self.appendKey(key)
            newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEEDAGENT,self.keydistObject)
            if (not self.stopped()):
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)
                        
            

    class testAuthThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject
            self._stop = Event()

        def stop(self):
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
        
            # I have a problem where I have multiple identity files in my ~/.ssh, and I want to use only identities loaded into the agent
            # since openssh does not seem to have an option to use only an agent we have a workaround, 
            # by passing the -o IdentityFile option a path that does not exist, openssh can't use any other identities, and can only use the agent.
            # This is a little "racy" in that a tempfile with the same path could concievably be created between the unlink and openssh attempting to use it
            # but since the pub key is extracted from the agent not the identity file I can't see anyway an attacker could use this to trick a user into uploading the attackers key.
            print "testAuthThread started"
            import tempfile, os
            (fd,path)=tempfile.mkstemp()
            os.close(fd)
            os.unlink(path)
            
            ssh_cmd = '{sshbinary} -o IdentityFile={nonexistantpath} -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o StrictHostKeyChecking=yes -l {login} {host} echo "success_testauth"'.format(sshbinary=self.keydistObject.sshpaths.sshBinary,
                                                                                                                                                                          login=self.keydistObject.username,
                                                                                                                                                                          host=self.keydistObject.host,
                                                                                                                                                                          nonexistantpath=path)

            logger_debug('testAuthThread: attempting: ' + ssh_cmd)
            ssh = subprocess.Popen(ssh_cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,shell=True,universal_newlines=True)
            stdout, stderr = ssh.communicate()
            ssh.wait()

            logger_debug('testAuthThread: stdout of ssh command: ' + str(stdout))
            logger_debug('testAuthThread: stderr of ssh command: ' + str(stderr))

            if 'success_testauth' in stdout:
                logger_debug('testAuthThread: got success_testauth in stdout :)')
                self.keydistObject.authentication_success = True
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_AUTHSUCCESS,self.keydistObject)
            else:
                logger_debug('testAuthThread: did not see success_testauth in stdout, posting EVT_KEYDIST_AUTHFAIL event')
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_AUTHFAIL,self.keydistObject)

            if (not self.stopped()):
                logger_debug('testAuthThread: self.stopped() == False, so posting event: ' + str(newevent))
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)


    class loadKeyThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject
            self._stop = Event()

        def stop(self):
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()


        def loadKey(self):
            try:
                f = open(self.keydistObject.sshpaths.sshKeyPath,'r')
                f.close()
            except IOError as e: # The key file didn't exist, so we should generate a new one.
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEWPASS_REQ,self.keydistObject)
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)
                return

            if (self.keydistObject.password != None and len(self.keydistObject.password) > 0):
                passphrase = self.keydistObject.password
            else:
                passphrase = ''

            if sys.platform.startswith('win'):
                # The patched OpenSSH binary on Windows/cygwin allows us
                # to send the password via stdin.
                cmd = self.keydistObject.sshpaths.sshAddBinary + ' ' + double_quote(self.keydistObject.sshpaths.sshKeyPath)
                logger_debug('on Windows, so running: ' + cmd)
                stdout, stderr = subprocess.Popen(cmd,
                                                  stdin=subprocess.PIPE,
                                                  stdout=subprocess.PIPE,
                                                  stderr=subprocess.STDOUT,
                                                  shell=True,
                                                  universal_newlines=True).communicate(input=passphrase + '\r\n')

                if stdout is None or str(stdout).strip() == '':
                    logger_debug('Got EOF from ssh-add binary')
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
                elif 'Identity added' in stdout:
                    logger_debug('Got "Identity added" from ssh-add binary')
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_GETPUBKEY, self.keydistObject)
                elif 'Bad pass' in stdout:
                    logger_debug('Got "Bad pass" from ssh-add binary')
                    if passphrase == '':
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
                    else:
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_WRONGPASS, self.keydistObject)
                else:
                    logger_debug('Got unknown error from ssh-add binary')
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED,self.keydistObject)
            else:
                # On Linux or BSD/OSX we can use pexpect to talk to ssh-add.

                args = [self.keydistObject.sshpaths.sshKeyPath]
                lp = pexpect.spawn(self.keydistObject.sshpaths.sshAddBinary, args=args)

                idx = lp.expect(["Identity added", ".*pass.*"])

                if idx == 1:
                    logger_debug("sending passphrase to ssh-add")
                    lp.sendline(passphrase)

                    idx = lp.expect(["Identity added", "Bad pass", pexpect.EOF])

                if idx == 0:
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_GETPUBKEY, self.keydistObject)
                elif idx == 1:
                    if passphrase == '':
                        logger_debug("passphrase is an empty string ssh-add returned Bad pass")
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
                    else:
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_WRONGPASS, self.keydistObject)
                else:
                    logger_debug("1 returning KEY_LOCKED %s %s"%(lp.before,lp.after))
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
                lp.close()

            if (not self.stopped()):
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(), newevent)


        def run(self):
            self.loadKey()


    class CopyIDThread(Thread):
        def __init__(self,keydist):
            Thread.__init__(self)
            self.keydistObject = keydist
            self._stop = Event()

        def stop(self):
            self._stop.set()
        
        def stopped(self):
            return self._stop.isSet()

        def run(self):
            sshClient = ssh.SSHClient()
            sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())
            try:
                sshClient.connect(hostname=self.keydistObject.host,username=self.keydistObject.username,password=self.keydistObject.password,allow_agent=False,look_for_keys=False)
                sshClient.exec_command("module load massive")
                sshClient.exec_command("/bin/mkdir -p ~/.ssh")
                sshClient.exec_command("/bin/chmod 700 ~/.ssh")
                sshClient.exec_command("/bin/touch ~/.ssh/authorized_keys")
                sshClient.exec_command("/bin/chmod 600 ~/.ssh/authorized_keys")
                sshClient.exec_command("/bin/echo \"%s\" >> ~/.ssh/authorized_keys"%self.keydistObject.pubkey)
                # FIXME The exec_commands above can fail if the user is over quota.
                sshClient.close()
                self.keydistObject.keycopiedLock.acquire()
                self.keydistObject.keycopied=True
                self.keydistObject.keycopiedLock.release()
                event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_TESTAUTH,self.keydistObject)
                logger_debug('CopyIDThread: successfully copied the key')
            except ssh.AuthenticationException as e:
                logger_debug('CopyIDThread: ssh.AuthenticationException: ' + str(e))
                event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_COPYID_NEEDPASS,self.keydistObject,string)
            except ssh.SSHException as e:
                logger_debug('CopyIDThread: ssh.SSHException : ' + str(e))
                self.keydistObject.cancel(message=str(e))
                return
            if (not self.stopped()):
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(), event)



    class sshKeyDistEvent(wx.PyCommandEvent):
        def __init__(self,id,keydist,string=""):
            wx.PyCommandEvent.__init__(self,KeyDist.myEVT_CUSTOM_SSHKEYDIST,id)
            self.keydist = keydist
            self.string = string

        def newkey(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_NEWPASS_REQ):
                logger_debug("recieved NEWPASS_REQ event")
                wx.CallAfter(event.keydist.getNewPassphrase_stage1,event.string)
            if (event.GetId() == KeyDist.EVT_KEYDIST_NEWPASS_RPT):
                logger_debug("recieved NEWPASS_RPT event")
                wx.CallAfter(event.keydist.getNewPassphrase_stage2)
            if (event.GetId() == KeyDist.EVT_KEYDIST_NEWPASS_COMPLETE):
                logger_debug("recieved NEWPASS_COMPLETE event")
                t = KeyDist.genkeyThread(event.keydist)
                t.setDaemon(True)
                t.start()
                event.keydist.threads.append(t)
            event.Skip()

        def copyid(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_COPYID_NEEDPASS):
                logger_debug("recieved COPYID_NEEDPASS event")
                wx.CallAfter(event.keydist.getLoginPassword,event.string)
            elif (event.GetId() == KeyDist.EVT_KEYDIST_COPYID):
                logger_debug("recieved COPYID event")
                t = KeyDist.CopyIDThread(event.keydist)
                t.setDaemon(True)
                t.start()
                event.keydist.threads.append(t)
            else:
                event.Skip()

        def scanhostkeys(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_SCANHOSTKEYS):
                logger_debug("recieved SCANHOSTKEYS event")
                t = KeyDist.scanHostKeysThread(event.keydist)
                t.setDaemon(True)
                t.start()
                event.keydist.threads.append(t)
            event.Skip()

        def cancel(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_CANCEL):
                event.keydist._canceled.set()
                if (len(event.string)>0):
                    pass
                for t in event.keydist.threads:
                    try:
                        t.stop()
                        t.join()
                    except:
                        pass
                event.keydist.completed=True
                if (event.keydist.callback_fail != None):
                    event.keydist.callback_fail()
            else:
                event.Skip()

        def success(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_AUTHSUCCESS):
                logger_debug("received AUTHSUCCESS event")
                event.keydist.completed=True
                if (event.keydist.callback_success != None):
                    event.keydist.callback_success()
            event.Skip()


        def needagent(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_NEEDAGENT):
                logger_debug("received NEEDAGENT event")
                t = KeyDist.startAgentThread(event.keydist)
                t.setDaemon(True)
                t.start()
                event.keydist.threads.append(t)
            else:
                event.Skip()

        def listpubkeys(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_GETPUBKEY):
                logger_debug("received GETPUBKEY event")
                t = KeyDist.getPubKeyThread(event.keydist)
                t.setDaemon(True)
                t.start()
                event.keydist.threads.append(t)
            else:
                event.Skip()

        def testauth(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_TESTAUTH):
                logger_debug("received TESTAUTH event")
                print "received TESTAUTH event, starting testAuthThread"
                t = KeyDist.testAuthThread(event.keydist)
                t.setDaemon(True)
                t.start()
                event.keydist.threads.append(t)
            else:
                event.Skip()

        def keylocked(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_KEY_LOCKED):
                logger_debug("received KEY_LOCKED event")
                wx.CallAfter(event.keydist.GetKeyPassword)
            if (event.GetId() == KeyDist.EVT_KEYDIST_KEY_WRONGPASS):
                logger_debug("received KEY_WRONGPASS event")
                wx.CallAfter(event.keydist.GetKeyPassword,"Sorry that password was incorrect. ")
            event.Skip()

        def loadkey(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_LOADKEY):
                logger_debug("received LOADKEY event")
                t = KeyDist.loadKeyThread(event.keydist)
                t.setDaemon(True)
                t.start()
                event.keydist.threads.append(t)
            else:
                event.Skip()

        def authfail(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_AUTHFAIL):
                logger_debug("received AUTHFAIL event")
                event.keydist.pubkeylock.acquire()
                keyloaded = event.keydist.keyloaded
                event.keydist.pubkeylock.release()
                if(not keyloaded):
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_LOADKEY,event.keydist)
                    wx.PostEvent(event.keydist.notifywindow.GetEventHandler(),newevent)
                else:
                    # if they key is loaded into the ssh agent, then authentication failed because the public key isn't on the server.
                    # *****TODO*****
                    # actually this might not be strictly true. gnome keychain (and possibly others) will report a key loaded even if its still locked
                    # we probably need a button that says "I can't remember my old keys password, please generate a new keypair"
                    event.keydist.keycopiedLock.acquire()
                    keycopied=event.keydist.keycopied
                    event.keydist.keycopiedLock.release()
                    if (keycopied):
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_TESTAUTH,event.keydist)
                        wx.PostEvent(event.keydist.notifywindow.GetEventHandler(),newevent)
                    else:
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_COPYID_NEEDPASS,event.keydist)
                        wx.PostEvent(event.keydist.notifywindow.GetEventHandler(),newevent)
            else:
                event.Skip()


        def startevent(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_START):
                logger_debug("received KEYDIST_START event")
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_SCANHOSTKEYS,event.keydist)
                wx.PostEvent(event.keydist.notifywindow.GetEventHandler(),newevent)
            else:
                event.Skip()

    myEVT_CUSTOM_SSHKEYDIST=None
    EVT_CUSTOM_SSHKEYDIST=None
    def __init__(self,username,host,notifywindow,sshPaths):
        KeyDist.myEVT_CUSTOM_SSHKEYDIST=wx.NewEventType()
        KeyDist.EVT_CUSTOM_SSHKEYDIST=wx.PyEventBinder(self.myEVT_CUSTOM_SSHKEYDIST,1)
        KeyDist.EVT_KEYDIST_START = wx.NewId()
        KeyDist.EVT_KEYDIST_CANCEL = wx.NewId()
        KeyDist.EVT_KEYDIST_SUCCESS = wx.NewId()
        KeyDist.EVT_KEYDIST_NEEDAGENT = wx.NewId()
        KeyDist.EVT_KEYDIST_NEEDKEYS = wx.NewId()
        KeyDist.EVT_KEYDIST_GETPUBKEY = wx.NewId()
        KeyDist.EVT_KEYDIST_TESTAUTH = wx.NewId()
        KeyDist.EVT_KEYDIST_AUTHSUCCESS = wx.NewId()
        KeyDist.EVT_KEYDIST_AUTHFAIL = wx.NewId()
        KeyDist.EVT_KEYDIST_NEWPASS_REQ = wx.NewId()
        KeyDist.EVT_KEYDIST_NEWPASS_RPT = wx.NewId()
        KeyDist.EVT_KEYDIST_NEWPASS_COMPLETE = wx.NewId()
        KeyDist.EVT_KEYDIST_COPYID = wx.NewId()
        KeyDist.EVT_KEYDIST_COPYID_NEEDPASS = wx.NewId()
        KeyDist.EVT_KEYDIST_KEY_LOCKED = wx.NewId()
        KeyDist.EVT_KEYDIST_KEY_WRONGPASS = wx.NewId()
        KeyDist.EVT_KEYDIST_SCANHOSTKEYS = wx.NewId()
        KeyDist.EVT_KEYDIST_LOADKEY = wx.NewId()

        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.cancel)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.success)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.needagent)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.listpubkeys)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.testauth)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.authfail)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.startevent)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.newkey)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.copyid)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.keylocked)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.scanhostkeys)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.loadkey)

        self.completed=False
        self.username = username
        self.host = host
        self.notifywindow = notifywindow
        self.sshKeyPath = ""
        self.threads=[]
        self.pubkeyfp = None
        self.keyloaded = False
        self.password = None
        self.pubkeylock = Lock()
        self.completedLock = Lock()
        self.keycopiedLock=Lock()
        self.keycopied=False
        self.sshpaths=sshPaths
        self.launcherKeyComment=os.path.basename(self.sshpaths.sshKeyPath)
        self.authentication_success = False
        self.callback_success=None
        self.callback_fail=None
        self._canceled=Event()

    def GetKeyPassword(self,prepend=""):
        ppd = KeyDist.passphraseDialog(None,wx.ID_ANY,'Unlock Key',prepend+"Please enter the passphrase for the key","OK","Cancel")
        (canceled,password) = ppd.getPassword()
        if (canceled):
            self.cancel("Sorry, I can't continue without the password for that key. If you've forgotten the password, you could remove the key and generate a new one. The key probably located in ~/.ssh/MassiveKey*")
            return
        else:
            self.password = password
            event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_TESTAUTH,self)
            wx.PostEvent(self.notifywindow.GetEventHandler(),event)

    def getLoginPassword(self,prepend=""):
        ppd = KeyDist.passphraseDialog(None,wx.ID_ANY,'Login Passphrase',prepend+"Please enter your login password for username %s at %s"%(self.username,self.host),"OK","Cancel")
        (canceled,password) = ppd.getPassword()
        if canceled:
            self.cancel()
            return
        self.password = password
        event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_COPYID,self)
        wx.PostEvent(self.notifywindow.GetEventHandler(),event)

    def getNewPassphrase_stage1(self,prepend=""):
        ppd = KeyDist.passphraseDialog(None,wx.ID_ANY,'New Passphrase',prepend+"Please enter a new passphrase","OK","Cancel")
        (canceled,password) = ppd.getPassword()
        if (not canceled):
            if (password != None and len(password) < 6 and len(password)>0):
                event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEWPASS_REQ,self,"The password was too short. ")
            else:
                self.password = password
                event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEWPASS_RPT,self)
            wx.PostEvent(self.notifywindow.GetEventHandler(),event)

    def getNewPassphrase_stage2(self):
        ppd = KeyDist.passphraseDialog(None,wx.ID_ANY,'New Passphrase',"Please repeat the new passphrase","OK","Cancel")
        (canceled,phrase) = ppd.getPassword()
        if (phrase == None and not canceled):
            phrase = ""
        if (phrase == self.password):
            event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEWPASS_COMPLETE,self)
        else:
            event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEWPASS_REQ,self,"The passwords didn't match. ")
        wx.PostEvent(self.notifywindow.GetEventHandler(),event)


    def distributeKey(self,callback_success=None,callback_fail=None):
        event = KeyDist.sshKeyDistEvent(self.EVT_KEYDIST_START, self)
        wx.PostEvent(self.notifywindow.GetEventHandler(), event)
        self.callback_fail=callback_fail
        self.callback_success=callback_success
        
    def canceled(self):
        return self._canceled.isSet()

    def cancel(self,message=""):
        if (not self.canceled()):
            self._canceled.set()
            newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_CANCEL, self)
            wx.PostEvent(self.notifywindow.GetEventHandler(), newevent)
