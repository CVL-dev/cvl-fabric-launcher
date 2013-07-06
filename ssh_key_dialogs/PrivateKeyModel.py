# PrivateKey.py

import sys
import os
import sys

if os.path.abspath("..") not in sys.path:
    sys.path.append(os.path.abspath(".."))
from sshKeyDist import sshpaths
from sshKeyDist import double_quote

class PrivateKeyModel():

    def __init__(self, privateKeyFilePath):

        self.privateKeyFilePath = privateKeyFilePath

        (self.privateKeyDirectory, self.privateKeyFileName) = os.path.split(self.privateKeyFilePath)
        # sshKeyDist.sshpaths currently assumes that private key is in ~/.ssh
        self.sshPathsObject = sshpaths(self.privateKeyFileName)

    def generatePrivateKey(self):
        print "generatePrivateKey"

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
                    elif "Pass phrases do not match" in stdout:
                        # This shouldn't happen because changePassphrase 
                        # only takes one argument for newPassphrase,
                        # so repeated newPassphrase should have 
                        # already been checked before changePassphrase
                        # is called.
                        print "Pass phrases do not match."
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
                idx = lp.expect(["Your identification has been saved", "Pass phrases do not match.", "passphrase too short"])
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

    def deleteKey(self):
        print "deleteKey"

