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

if not sys.platform.startswith('win'):
    import pexpect

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
                f = lambda x: os.path.join(os.path.dirname(sys.executable), 'openssh-cygwin-stdin-build', 'bin', x)
            else:
                f = lambda x: os.path.join(os.getcwd(), 'openssh-cygwin-stdin-build', 'bin', x)
 
            sshBinary        = f('ssh.exe')
            sshKeyGenBinary  = f('ssh-keygen.exe')
            sshKeyScanBinary = f('ssh-keyscan.exe')
            sshAgentBinary   = f('ssh-agent.exe')
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
            self.Destroy()


        def getPassword(self):
            val = self.ShowModal()
            return self.password

    class startAgentThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject

        def run(self):
            print 'startAgentThread: run()'
            agentenv = None
            try:
                agentenv = os.environ['SSH_AUTH_SOCK']
                print 'startAgentThread: found SSH_AUTH_SOCK environment variable: ' + agentenv
            except:
                print 'startAgentThread: did not find SSH_AUTH_SOCK environment variable; trying to start ssh-agent'
                try:
                    agent = subprocess.Popen(self.keydistObject.sshpaths.sshAgentBinary,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
                    stdout = agent.stdout.readlines()
                    print 'startagent stdout:', str(stdout)
                    for line in stdout:
                        match = re.search("^SSH_AUTH_SOCK=(?P<socket>.*); export SSH_AUTH_SOCK;$",line)
                        if match:
                            agentenv = match.group('socket')
                            os.environ['SSH_AUTH_SOCK'] = agentenv
                            print 'startAgentThread: started ssh-agent; SSH_AUTH_SOCK = ' + agentenv
                    if agent is None:
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_CANCEL, self, str(stdout))
                        print 'startAgentThread: failed to start ssh-agent: ' + str(str(stdout))
                except Exception as e:
                    string = "%s"%e
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_CANCEL,self,string)
                    print 'startAgentThread: failed to start ssh-agent: ' + str(e)

            newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_LISTFINGERPRINTS,self.keydistObject)
            wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)
            print 'startAgentThread: exiting run()'

    class genkeyThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject

        def run(self):
            print 'genkeyThread: run()'
            cmd = '{sshkeygen} -q -f "{keyfilename}" -C "MASSIVE Launcher" -N {password}'.format(sshkeygen=self.keydistObject.sshpaths.sshKeyGenBinary,
                                                                                                 keyfilename=self.keydistObject.sshpaths.sshKeyPath,
                                                                                                 password=self.keydistObject.password)

            print 'genkeyThread: running command: ' + cmd

            keygen_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
            keygen_proc.wait()

            try:
                with open(self.keydistObject.sshKeyPath+".pub",'r'): pass
                print 'genkeyThread: able to open public key file; posting the EVT_KEYDIST_AUTHFAIL event to trigger loading of the key'
                event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_AUTHFAIL,self.keydistObject) # Auth hasn't really failed but this event will trigger loading the key
            except Exception as e:
                print 'genkeyThread: some other error while generating the key: ' + str(e)
                event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_CANCEL,self.keydistObject,"error generating key")
 
            print 'genkeyThread: posting self.keydistObject.notifywindow.GetEventHandler()'
            wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),event)
            print 'genkeyThread: exiting run()'

    class listFingerprintsThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject

        def run(self):
            print 'listFingerprintsThread: run()'
            sshKeyListCmd = self.keydistObject.sshpaths.sshAddBinary + " -l "
            print 'listFingerprintsThread: running command: ' + sshKeyListCmd
            keylist = subprocess.Popen(sshKeyListCmd, stdout = subprocess.PIPE,stderr=subprocess.STDOUT,shell=True,universal_newlines=True)
            keylist.wait()
            stdout = keylist.stdout.readlines()

            print 'listFingerprintsThread: stdout: ' + str(stdout)

            self.keydistObject.fplock.acquire()
            self.keydistObject.fingerprints = []
            for line in stdout:
                match = re.search("^[0-9]+\ (\S*)\ (.+)$",line)
                if match:
                    self.keydistObject.fingerprints.append(match.group(1))
            if (self.keydistObject.pubkeyfp in self.keydistObject.fingerprints):
                self.keydistObject.pubkeyloaded = True
            self.keydistObject.fplock.release()
            if (len(self.keydistObject.fingerprints) > 0):
                print 'listFingerprintsThread: found the fingerprint; posting the EVT_KEYDIST_TESTAUTH event'
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_TESTAUTH,self.keydistObject)
            else:
                print 'listFingerprintsThread: did not find the fingerprint; posting the EVT_KEYDIST_AUTHFAIL event'
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_AUTHFAIL,self.keydistObject)
            wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)
            print 'listFingerprintsThread: leaving run()'

    class scanHostKeysThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject
            self.ssh_keygen_cmd = '{sshkeygen} -F {host} -f {known_hosts_file}'.format(sshkeygen=self.keydistObject.sshpaths.sshKeyGenBinary,host=self.keydistObject.host,known_hosts_file=self.keydistObject.sshpaths.sshKnownHosts)
            self.ssh_keyscan_cmd = '{sshscan} {host}'.format(sshscan=self.keydistObject.sshpaths.sshKeyScanBinary,host=self.keydistObject.host)

        def getKnownHostKeys(self):
            keygen = subprocess.Popen(self.ssh_keygen_cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,universal_newlines=True)
            stdout,stderr = keygen.communicate()
            keygen.wait()
            hostkeys=[]
            for line in stdout.split('\n'):
                print "in getKnownHostKeys line"
                print line
                if (not (line.find('#')==0 or line == '')):
                    hostkeys.append(line)
            return hostkeys
                    
        def appendKey(self,key):
            with open(self.keydistObject.sshpaths.sshKnownHosts,'a+') as known_hosts:
                known_hosts.write(key)
            

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
            hostKeys = self.scanHost()
            newevent=None
            foundKey=False
            if len(hostKeys)>1:
                print "That was unexpected, a scan of the host returned more than one host key"
            print "hostKeys"
            print hostKeys
            print "knownKeys"
            print knownKeys
            
            for key in hostKeys:
                if key in knownKeys:
                    foundKey=True
            if (not foundKey):
                #TODO check the key against a list of trusted keys from a web server/CVL VM managment
                for k in hostKeys: self.appendKey(k)

            newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEEDAGENT,self.keydistObject)
            wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)
                        
            

    class testAuthThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject

        def run(self):
            print 'testAuthThread: run()'

            ssh_cmd = '{sshbinary} -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o StrictHostKeyChecking=no -l {login} {host} echo "success_testauth"'.format(sshbinary=self.keydistObject.sshpaths.sshBinary,
                                                                                                                                                                          login=self.keydistObject.username,
                                                                                                                                                                          host=self.keydistObject.host)

            print 'testAuthThread: run(): executing: ' + ssh_cmd

            ssh = subprocess.Popen(ssh_cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,shell=True,universal_newlines=True)
            stdout, stderr = ssh.communicate()
            ssh.wait()

            print 'testAuthThread: run(): stdout: ' + str(stdout)

            if 'success_testauth' in stdout:
                print 'testAuthThread: run(): got success_testauth in stdout :)'
                self.authentication_success = True
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_AUTHSUCCESS,self.keydistObject)
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)
            else:
                print 'testAuthThread: run(): did NOT see success_testauth in stdout :('
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_AUTHFAIL,self.keydistObject)
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)


    class getPubkeyThread(Thread):
        def __init__(self,keydistObject):
            Thread.__init__(self)
            self.keydistObject = keydistObject

        def fingerprint(self):
            sshKeyGenCmd = self.keydistObject.sshpaths.sshKeyGenBinary + " -l -f " + double_quote(self.keydistObject.sshpaths.sshKeyPath) + ".pub"
            fp = subprocess.Popen(sshKeyGenCmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,shell=True,universal_newlines=True)
            stdout = fp.stdout.readlines()
            fp.wait()
            for line in stdout:
                match = re.search("^[0-9]+\ (\S*)\ (.+)$",line)
                if match:
                    fp = match.group(1)
                    comment = match.group(2)
            return fp,comment

        def loadKey(self):
            print 'getPubkeyThread: loadKey():'

            if (self.keydistObject.password != None and len(self.keydistObject.password) > 0):
                print 'getPubkeyThread: loadKey(): got passphrase from keydistObject'
                passphrase = self.keydistObject.password
            else:
                print 'getPubkeyThread: loadKey(): using empty passphrase'
                passphrase = ''

            if sys.platform.startswith('win'):
                print 'boo'
                # The patched OpenSSH binary on Windows/cygwin allows us
                # to send the password via stdin.
                stdout, stderr = subprocess.Popen(self.keydistObject.sshpaths.sshAddBinary + ' ' + double_quote(self.keydistObject.sshKeyPath), 
                                                  stdin=subprocess.PIPE,
                                                  stdout=subprocess.PIPE,
                                                  stderr=subprocess.STDOUT,
                                                  shell=True,
                                                  universal_newlines=True).communicate(input=passphrase + '\r\n')

                print 'boo2'
                print 'stdout from ssh-add:', str(stdout)
                print 'stderr from ssh-add:', str(stderr)

                if stdout is None or str(stdout).strip() == '':
                    # Got EOF from ssh-add binary
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
                elif 'Identity added' in stdout:
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_LISTFINGERPRINTS, self.keydistObject)
                elif 'Bad pass' in stdout:
                    if passphrase == '':
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
                    else:
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_WRONGPASS, self.keydistObject)
                else:
                    # unknown error
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED,self.keydistObject)
            else:
                # On Linux or BSD/OSX we can use pexpect to talk to ssh-add.

                args = [self.keydistObject.sshKeyPath]
                print 'getPubkeyThread: loadKey(): running %s with args %s' % (str(self.keydistObject.sshpaths.sshAddBinary), str(args),)
                lp = pexpect.spawn(sshAddBinary, args=args)

                idx = lp.pexpect(["Identity added", ".*pass.*"])

                if idx == 1:
                    print 'getPubkeyThread: loadKey(): sending passphrase to ssh-agent'
                    lp.sendline(passphrase)

                    idx = lp.pexpect(["Identity added", "Bad pass", pexpect.EOF])

                    if idx == 0:
                        print 'getPubkeyThread: loadKey(): got "Identity added"; posting the EVT_KEYDIST_LISTFINGERPRINTS event'
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_LISTFINGERPRINTS, self.keydistObject)
                    elif idx == 1:
                        print 'getPubkeyThread: loadKey(): got "Bad pass"'
                        if passphrase == '':
                            print 'getPubkeyThread: loadKey(): empty passphrase,  so posting the EVT_KEYDIST_KEY_LOCKED event'
                            newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
                        else:
                            print 'getPubkeyThread: loadKey(): non-empty passphrase,  so posting the EVT_KEYDIST_KEY_WRONGPASS event'
                            newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_WRONGPASS, self.keydistObject)
                    else:
                        print 'getPubkeyThread: loadKey(): got EOF (?) from ssh-add,  so posting the EVT_KEYDIST_KEY_LOCKED event'
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
                else:
                    print 'getPubkeyThread: loadKey(): got "Identity added" from ssh-add, so sending the EVT_KEYDIST_KEY_LOCKED event'
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
                lp.close()

            wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(), newevent)
            print 'getPubkeyThread: loadKey(): exiting'

        def run(self):
            try:
                sshKeyPath, _ = sshpaths().ssh_files()
                f = open(sshKeyPath+".pub",'r')
                f.close()
                self.keydistObject.sshKeyPath = sshKeyPath
                fp,comment = self.fingerprint()
                self.keydistObject.pubkeyfp = fp
                self.keydistObject.pubkeyComment = comment
                self.keydistObject.fplock.acquire()
                if (fp not in self.keydistObject.fingerprints):
                    self.loadKey()
                else:
                    newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_LISTFINGERPRINTS,self.keydistObject)
                    wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)
                self.keydistObject.fplock.release()

            except IOError:
                newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEWPASS_REQ,self.keydistObject)
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),newevent)


    class CopyIDThread(Thread):
        def __init__(self,keydist):
            Thread.__init__(self)
            self.keydistObject = keydist

        def run(self):
            sshClient = ssh.SSHClient()
            sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())
            try:
                sshClient.connect(hostname=self.keydistObject.host,username=self.keydistObject.username,password=self.keydistObject.password,allow_agent=False,look_for_keys=False)
                stdin,stdout,stderr = sshClient.exec_command("mktemp")
                tmpfile = stdout.read()
                tmpfile = tmpfile.rstrip()
                if (stderr.read() != ""):
                    raise Exception
                sftp = sshClient.open_sftp()
                sftp.put(self.keydistObject.sshKeyPath+".pub",tmpfile)
                sftp.close()

                sshClient.exec_command("module load massive")
                sshClient.exec_command("/bin/mkdir -p ~/.ssh")
                sshClient.exec_command("/bin/chmod 700 ~/.ssh")
                sshClient.exec_command("/bin/touch ~/.ssh/authorized_keys")
                sshClient.exec_command("/bin/chmod 600 ~/.ssh/authorized_keys")
                sshClient.exec_command("/bin/cat %s >> ~/.ssh/authorized_keys"%tmpfile)
                sshClient.exec_command("/bin/rm -f %s"%tmpfile)
                sshClient.close()
                print "copy id generating test auth afer success"
                self.keydistObject.keycopiedLock.acquire()
                self.keydistObject.keycopied=True
                self.keydistObject.keycopiedLock.release()
                event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_TESTAUTH,self.keydistObject)
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),event)
            except ssh.AuthenticationException as e:
                string = "%s"%e
                print "copy id thread, NEEDPASS"
                event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_COPYID_NEEDPASS,self.keydistObject,string)
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),event)
            except ssh.SSHException as e:
                string = "%s"%e
                event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_CANCEL,self.keydistObject,string)
                wx.PostEvent(self.keydistObject.notifywindow.GetEventHandler(),event)



    class sshKeyDistEvent(wx.PyCommandEvent):
        def __init__(self,id,keydist,string=""):
            wx.PyCommandEvent.__init__(self,KeyDist.myEVT_CUSTOM_SSHKEYDIST,id)
            self.keydist = keydist
            self.string = string
        def copyid_complete(event):
            if (event.GetId() == KeyDist.EVT_COPYID_COMPLETE):
                event.keydist.completedLock.acquire()
                event.keydist.completed = True
                event.keydist.completedLock.release()
            event.Skip()

        def copyid_fail(event):
            if (event.GetId() == KeyDist.EVT_COPYID_FAIL):
                event.keydist.copyid(event.string)
            event.Skip()

        def test_authorised(event):
            if (event.GetId() == KeyDist.EVT_NOTAUTHORISED):
                event.keydist.copyid()
            event.Skip()

        def loadkey(event):
            if (event.GetId() == KeyDist.EVT_LOADKEY_REQ):
                event.keydist.loadKey()
            else:
                event.Skip()


        def newkey(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_NEWPASS_REQ):
                wx.CallAfter(event.keydist.getNewPassphrase_stage1,event.string)
            if (event.GetId() == KeyDist.EVT_KEYDIST_NEWPASS_RPT):
                print "received NEWPASS_RPT"
                wx.CallAfter(event.keydist.getNewPassphrase_stage2)
            if (event.GetId() == KeyDist.EVT_KEYDIST_NEWPASS_COMPLETE):
                try:
                    if (event.keydist.workThread != None):
                        event.keydist.workThread.join()
                except RuntimeError:
                    pass
                event.keydist.workThread = KeyDist.genkeyThread(event.keydist)
                event.keydist.workThread.start()
            event.Skip()

        def copyid(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_COPYID_NEEDPASS):
                wx.CallAfter(event.keydist.getLoginPassword,event.string)
            if (event.GetId() == KeyDist.EVT_KEYDIST_COPYID):
                try:
                    if (event.keydist.workThread != None):
                        event.keydist.workThread.join()
                except RuntimeError:
                    pass
                print "creating CopyID Thread"
                event.keydist.workThread = KeyDist.CopyIDThread(event.keydist)
                event.keydist.workThread.start()
            event.Skip()

        def scanhostkeys(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_SCANHOSTKEYS):
                try:
                    if (event.keydist.workThread != None):
                        event.keydist.workThread.join()
                except RuntimeError:
                    pass
                print "creating scanHostKeys Thread"
                event.keydist.workThread = KeyDist.scanHostKeysThread(event.keydist)
                event.keydist.workThread.start()
            event.Skip()

        def cancel(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_CANCEL):
                if (len(event.string)>0):
                    print event.string
                try:
                    if (event.keydist.workThread != None):
                        event.keydist.workThread.join()
                except RuntimeError:
                    pass
                event.keydist.completed=True
            event.Skip()

        def success(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_AUTHSUCCESS):
                event.keydist.completed=True
            event.Skip()


        def needagent(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_NEEDAGENT):
                try:
                    if (event.keydist.workThread != None):
                        event.keydist.workThread.join()
                except RuntimeError:
                    pass
                event.keydist.workThread = KeyDist.startAgentThread(event.keydist)
                event.keydist.workThread.start()
            else:
                event.Skip()

        def listfingerprints(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_LISTFINGERPRINTS):
                try:
                    if (event.keydist.workThread != None):
                        event.keydist.workThread.join()
                except RuntimeError:
                    pass
                event.keydist.workThread = KeyDist.listFingerprintsThread(event.keydist)
                event.keydist.workThread.start()
            else:
                event.Skip()

        def testauth(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_TESTAUTH):
                try:
                    if (event.keydist.workThread != None):
                        print "waiting for previous thread to join"
                        event.keydist.workThread.join()
                except RuntimeError:
                    pass
                event.keydist.workThread = KeyDist.testAuthThread(event.keydist)
                event.keydist.workThread.start()
            else:
                event.Skip()

        def keylocked(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_KEY_LOCKED):
                wx.CallAfter(event.keydist.GetKeyPassword)
            if (event.GetId() == KeyDist.EVT_KEYDIST_KEY_WRONGPASS):
                wx.CallAfter(event.keydist.GetKeyPassword,"Sorry that password was incorrect. ")
            event.Skip()


        def authfail(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_AUTHFAIL):
                if(not event.keydist.pubkeyloaded):
                    try:
                        if (event.keydist.workThread != None):
                            event.keydist.workThread.join()
                    except RuntimeError:
                        pass
                    event.keydist.workThread = KeyDist.getPubkeyThread(event.keydist)
                    event.keydist.workThread.start()
                else:
                    # if they key is loaded into the ssh agent, then authentication failed because the public key isn't on the server.
                    # *****TODO*****
                    # actually this might not be strictly true. gnome keychain (and possibly others) will report a key loaded even if its still locked
                    # we probably need a button that says "I can't remember my old keys password, please generate a new keypair"
                    event.keydist.keycopiedLock.acquire()
                    keycopied=event.keydist.keycopied
                    event.keydist.keycopiedLock.release()
                    if (keycopied):
                        print "auth failed but key copied, retry auth"
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_TESTAUTH,event.keydist)
                        wx.PostEvent(event.keydist.notifywindow.GetEventHandler(),newevent)
                    else:
                        print "autfail event, key is loaded, but we can't log copy the id"
                        newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_COPYID_NEEDPASS,event.keydist)
                        wx.PostEvent(event.keydist.notifywindow.GetEventHandler(),newevent)
            else:
                event.Skip()


        def startevent(event):
            if (event.GetId() == KeyDist.EVT_KEYDIST_START):
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
        KeyDist.EVT_KEYDIST_LISTFINGERPRINTS = wx.NewId()
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

        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.cancel)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.success)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.needagent)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.listfingerprints)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.testauth)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.authfail)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.startevent)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.newkey)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.copyid)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.keylocked)
        notifywindow.Bind(self.EVT_CUSTOM_SSHKEYDIST, KeyDist.sshKeyDistEvent.scanhostkeys)

        self.completed=False
        self.username = username
        self.host = host
        self.notifywindow = notifywindow
        self.sshKeyPath = ""
        self.workThread = None
        self.pubkey = None
        self.pubkeyfp = None
        self.pubkeyloaded = False
        self.password = None
        self.fplock = Lock()
        self.completedLock = Lock()
        self.keycopiedLock=Lock()
        self.keycopied=False
        self.sshpaths=sshPaths
        self.authentication_success = False

    def GetKeyPassword(self,prepend=""):
        ppd = KeyDist.passphraseDialog(None,wx.ID_ANY,'Unlock Key',prepend+"Please enter the passphrase for the key","OK","Cancel")
        password = ppd.getPassword()
        if (password == None):
            event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_CANCEL,self)
        else:
            self.password = password
            print "Get Key Password, generating AUTHFAIL"
            event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_AUTHFAIL,self)
        wx.PostEvent(self.notifywindow.GetEventHandler(),event)

    def getLoginPassword(self,prepend=""):
        print "get login password"
        ppd = KeyDist.passphraseDialog(None,wx.ID_ANY,'Login Passphrase',prepend+"Please enter your login password for username %s at %s"%(self.username,self.host),"OK","Cancel")
        password = ppd.getPassword()
        self.password = password
        event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_COPYID,self)
        wx.PostEvent(self.notifywindow.GetEventHandler(),event)

    def getNewPassphrase_stage1(self,prepend=""):
        ppd = KeyDist.passphraseDialog(None,wx.ID_ANY,'New Passphrase',prepend+"Please enter a new passphrase","OK","Cancel")
        password = ppd.getPassword()
        if (len(password) < 6 and len(password)>0):
            event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEWPASS_REQ,self,"The password was too short. ")
        else:
            self.password = password
            event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEWPASS_RPT,self)
        wx.PostEvent(self.notifywindow.GetEventHandler(),event)

    def getNewPassphrase_stage2(self):
        ppd = KeyDist.passphraseDialog(None,wx.ID_ANY,'New Passphrase',"Please repeat the new passphrase","OK","Cancel")
        phrase = ppd.getPassword()
        if (phrase == None):
            phrase = ""
        if (phrase == self.password):
            event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEWPASS_COMPLETE,self)
        else:
            event = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_NEWPASS_REQ,self,"The passwords didn't match. ")
        wx.PostEvent(self.notifywindow.GetEventHandler(),event)


    def distributeKey(self):
        self.sshKeyPath, _ = sshpaths().ssh_files()
        event = KeyDist.sshKeyDistEvent(self.EVT_KEYDIST_START, self)
        wx.PostEvent(self.notifywindow.GetEventHandler(), event)
