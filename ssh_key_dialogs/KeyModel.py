# KeyModel.py

import sys
import os
import subprocess
import tempfile
import traceback

if os.path.abspath("..") not in sys.path:
    sys.path.append(os.path.abspath(".."))
from sshKeyDist import sshpaths
from sshKeyDist import double_quote

class KeyModel():

    def __init__(self, privateKeyFilePath):

        self.privateKeyFilePath = privateKeyFilePath

        (self.privateKeyDirectory, self.privateKeyFileName) = os.path.split(self.privateKeyFilePath)
        # sshKeyDist.sshpaths currently assumes that private key is in ~/.ssh
        self.sshPathsObject = sshpaths(self.privateKeyFileName)

    def generateNewKey(self, passphrase, keyComment, keyCreatedSuccessfullyCallback, keyFileAlreadyExistsCallback, passphraseTooShortCallback):

        success = False

        if sys.platform.startswith('win'):
            # The patched OpenSSH binary on Windows/cygwin allows us
            # to send the passphrase via STDIN.
            cmdList = [self.sshPathsObject.sshKeyGenBinary, "-f", double_quote(self.privateKeyFilePath), "-C", keyComment]
            #logger_debug('on Windows, so running: ' + cmd)
            proc = subprocess.Popen(cmdList,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate(input=passphrase + '\r\n')

            if stdout is None or str(stdout).strip() == '':
                #logger_debug('Got EOF from ssh-keygen binary')
                print '(1) Got EOF from ssh-keygen binary'
            elif 'Enter passphrase' in stdout:
                stdout, stderr = proc.communicate(input=passphrase + '\r\n')
                if stdout is None or str(stdout).strip() == '':
                    #logger_debug('Got EOF from ssh-keygen binary')
                    print '(2) Got EOF from ssh-keygen binary'
                elif "Enter same passphrase" in stdout:
                    stdout, stderr = proc.communicate(input=passphrase + '\r\n')
                    if stdout is None or str(stdout).strip() == '':
                        #logger_debug('Got EOF from ssh-keygen binary')
                        print '(3) Got EOF from ssh-keygen binary'
                    elif "Your identification has been saved" in stdout:
                        success = True
                        keyCreatedSuccessfullyCallback()
                    elif "do not match" in stdout:
                        print "Passphrases do not match."
                    elif "passphrase too short" in stdout:
                        passphraseTooShortCallback()
            elif 'already exists' in stdout:
                keyFileAlreadyExistsCallback()
            else:
                #logger_debug('Got unknown error from ssh-keygen binary')
                print 'Got unknown error from ssh-keygen binary'
                print stderr
        else:
            # On Linux or BSD/OSX we can use pexpect to talk to ssh-keygen.

            import pexpect

            args = ["-f", self.privateKeyFilePath, "-C", keyComment]
            lp = pexpect.spawn(self.sshPathsObject.sshKeyGenBinary, args=args)

            idx = lp.expect(["Enter passphrase", "already exists", pexpect.EOF])

            if idx == 0:
                lp.sendline(passphrase)
                idx = lp.expect(["Enter same passphrase again"])
                lp.sendline(passphrase)
                idx = lp.expect(["Your identification has been saved", "do not match.", "passphrase too short"])
                if idx == 0:
                    success = True
                    keyCreatedSuccessfullyCallback()
                elif idx == 1:
                    # This shouldn't happen.
                    print "Passphrases do not match"
                elif idx == 2:
                    passphraseTooShortCallback()
            elif idx == 1:
                keyFileAlreadyExistsCallback()
            else:
                #logger_debug("1 returning KEY_LOCKED %s %s"%(lp.before,lp.after))
                print "Unexpected result from attempt to create new key."
            lp.close()
        return success

    def changePassphrase(self, existingPassphrase, newPassphrase, 
        passphraseUpdatedSuccessfullyCallback,
        existingPassphraseIncorrectCallback,
        newPassphraseTooShortCallback,
        keyLockedCallback):

        success = False

        if sys.platform.startswith('win'):
            # The patched OpenSSH binary on Windows/cygwin allows us
            # to send the passphrase via STDIN.
            cmdList = [self.sshPathsObject.sshKeyGenBinary, "-f", double_quote(self.privateKeyFilePath), "-p"]
            #cmd = self.keydistObject.sshpaths.sshAddBinary + ' ' + double_quote(self.keydistObject.sshpaths.sshKeyPath)
            #logger_debug('on Windows, so running: ' + cmd)
            proc = subprocess.Popen(cmdList,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate(input=existingPassphrase + '\r\n')

            if stdout is None or str(stdout).strip() == '':
                #logger_debug('Got EOF from ssh-keygen binary')
                print '(1) Got EOF from ssh-keygen binary'
                keyLockedCallback()
            elif 'Enter new passphrase' in stdout:
                stdout, stderr = proc.communicate(input=newPassphrase + '\r\n')
                if stdout is None or str(stdout).strip() == '':
                    #logger_debug('Got EOF from ssh-keygen binary')
                    print '(2) Got EOF from ssh-keygen binary'
                elif "Enter same passphrase" in stdout:
                    stdout, stderr = proc.communicate(input=newPassphrase + '\r\n')
                    if stdout is None or str(stdout).strip() == '':
                        #logger_debug('Got EOF from ssh-keygen binary')
                        print '(3) Got EOF from ssh-keygen binary'
                    elif "Your identification has been saved" in stdout:
                        success = True
                        passphraseUpdatedSuccessfullyCallback()
                    elif "do not match" in stdout:
                        # This shouldn't happen because changePassphrase 
                        # only takes one argument for newPassphrase,
                        # so repeated newPassphrase should have 
                        # already been checked before changePassphrase
                        # is called.
                        print "Passphrases do not match."
                    elif "passphrase too short" in stdout:
                        newPassphraseTooShortCallback()

            elif 'Bad pass' in stdout or 'load failed' in stdout:
                #logger_debug('Got "Bad pass" or "load failed" from ssh-keygen binary')
                print 'Got "Bad pass" from ssh-keygen binary'
                if existingPassphrase == '':
                    keyLockedCallback()
                else:
                    existingPassphraseIncorrectCallback()
            else:
                #logger_debug('Got unknown error from ssh-keygen binary')
                print 'Got unknown error from ssh-keygen binary'
                keyLockedCallback()
        else:
            # On Linux or BSD/OSX we can use pexpect to talk to ssh-keygen.

            import pexpect

            args = ["-f", self.privateKeyFilePath, "-p"]
            lp = pexpect.spawn(self.sshPathsObject.sshKeyGenBinary, args=args)

            idx = lp.expect(["Enter old passphrase", "Key has comment"])

            if idx == 0:
                #logger_debug("sending passphrase to " + sshKeyGenBinary + " -f " + self.privateKeyFilePath + " -p")
                lp.sendline(existingPassphrase)

            idx = lp.expect(["Enter new passphrase", "Bad pass", "load failed", pexpect.EOF])

            if idx == 0:
                lp.sendline(newPassphrase)
                idx = lp.expect(["Enter same passphrase again"])
                lp.sendline(newPassphrase)
                idx = lp.expect(["Your identification has been saved", "do not match.", "passphrase too short"])
                if idx == 0:
                    success = True
                    passphraseUpdatedSuccessfullyCallback()
                elif idx == 1:
                    # This shouldn't happen because changePassphrase 
                    # only takes one argument for newPassphrase,
                    # so repeated newPassphrase should have 
                    # already been checked before changePassphrase
                    # is called.
                    print "Passphrases do not match"
                elif idx == 2:
                    newPassphraseTooShortCallback()
            elif idx == 1 or idx == 2:
                existingPassphraseIncorrectCallback()
            else:
                #logger_debug("1 returning KEY_LOCKED %s %s"%(lp.before,lp.after))
                print "Unexpected result from attempt to change passphrase."
            lp.close()
        return success

    def deleteKeyAndRemoveFromAgent(self):
        # Delete key

        # Should we ask for the passphrase before deleting the key?

        (self.privateKeyDirectory, self.privateKeyFileName) = os.path.split(self.privateKeyFilePath)
        # sshKeyDist.sshpaths currently assumes that private key is in ~/.ssh
        self.sshPathsObject = sshpaths(self.privateKeyFileName)

        try:

            os.unlink(self.privateKeyFilePath)

            if os.path.exists(self.privateKeyFilePath + ".pub"):
                os.unlink(self.privateKeyFilePath + ".pub")

            # Remove key(s) from SSH agent:

            print "Removing Launcher public key(s) from agent."

            publicKeysInAgentProc = subprocess.Popen([self.sshPathsObject.sshAddBinary,"-L"],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            publicKeysInAgent = publicKeysInAgentProc.stdout.readlines()
            for publicKey in publicKeysInAgent:
                if "Launcher" in publicKey:
                    tempPublicKeyFile = tempfile.NamedTemporaryFile(delete=False)
                    tempPublicKeyFile.write(publicKey)
                    tempPublicKeyFile.close()
                    try:
                        removePublicKeyFromAgent = subprocess.Popen([self.sshPathsObject.sshAddBinary,"-d",tempPublicKeyFile.name],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                        stdout, stderr = removePublicKeyFromAgent.communicate()
                        if stderr is not None and len(stderr) > 0:
                            print stderr
                        success = ("Identity removed" in stdout)
                    finally:
                        os.unlink(tempPublicKeyFile.name)
        except:
            print traceback.format_exc()
            return False

        return True

    def addKeyToAgent(self, passphrase, keyAddedSuccessfullyCallback, passphraseIncorrectCallback, privateKeyFileNotFoundCallback):

        success = False

        if sys.platform.startswith('win'):
            # The patched OpenSSH binary on Windows/cygwin allows us
            # to send the passphrase via STDIN.
            cmdList = [self.sshPathsObject.sshAddBinary, double_quote(self.privateKeyFilePath)]
            #logger_debug('on Windows, so running: ' + cmd)
            proc = subprocess.Popen(cmdList,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate(input=passphrase + '\r\n')

            if "No such file or directory" in stderr:
                privateKeyFileNotFoundCallback()
                return False

            if stdout is None or str(stdout).strip() == '':
                #logger_debug('Got EOF from ssh-add binary')
                print '(1) Got EOF from ssh-add binary'
            elif "No such file or directory" in stdout:
                privateKeyFileNotFoundCallback()
                return False
            elif "Identity added" in stdout:
                success = True
                keyAddedSuccessfullyCallback()
            elif 'Bad pass' in stdout:
                #logger_debug('Got "Bad pass" from ssh-add binary')
                print 'Got "Bad pass" from ssh-add binary'
                proc.kill()
                passphraseIncorrectCallback()
            else:
                #logger_debug('Got unknown error from ssh-add binary')
                print 'Got unknown error from ssh-add binary'
        else:
            # On Linux or BSD/OSX we can use pexpect to talk to ssh-add.

            import pexpect

            args = [self.privateKeyFilePath]
            lp = pexpect.spawn(self.sshPathsObject.sshAddBinary, args=args)

            idx = lp.expect(["Enter passphrase"])

            if idx == 0:
                lp.sendline(passphrase)

                idx = lp.expect(["Identity added", "Bad pass"])
                if idx == 0:
                    success = True
                    keyAddedSuccessfullyCallback()
                elif idx == 1:
                    lp.kill(0)
                    passphraseIncorrectCallback()
                    return success
            else:
                print "Unexpected result from attempt to add key."
            lp.close()
        return success


    def removeKeyFromAgent(self):

        # FIXME
        # We use a method which doesn't require entering the key's passphrase :-)
        # but it just greps for Launcher in the agent's keys, rather than 
        # specifically identifying this key. :-(

        try:
            # Remove key(s) from SSH agent:

            print "Removing Launcher public key(s) from agent."

            publicKeysInAgentProc = subprocess.Popen([self.sshPathsObject.sshAddBinary,"-L"],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            publicKeysInAgent = publicKeysInAgentProc.stdout.readlines()
            for publicKey in publicKeysInAgent:
                if "Launcher" in publicKey:
                    tempPublicKeyFile = tempfile.NamedTemporaryFile(delete=False)
                    tempPublicKeyFile.write(publicKey)
                    tempPublicKeyFile.close()
                    try:
                        removePublicKeyFromAgent = subprocess.Popen([self.sshPathsObject.sshAddBinary,"-d",tempPublicKeyFile.name],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                        stdout, stderr = removePublicKeyFromAgent.communicate()
                        if stderr is not None and len(stderr) > 0:
                            print stderr
                        success = ("Identity removed" in stdout)
                    finally:
                        os.unlink(tempPublicKeyFile.name)
        except:
            print traceback.format_exc()
            return False

        return True
