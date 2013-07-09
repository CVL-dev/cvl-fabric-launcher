# KeyModel.py

import sys
import os
import subprocess
import tempfile
import traceback

if os.path.abspath("..") not in sys.path:
    sys.path.append(os.path.abspath(".."))
from sshKeyDist import sshpaths

from utilityFunctions import logger_debug

class KeyModel():

    def __init__(self, privateKeyFilePath):

        self.privateKeyFilePath = privateKeyFilePath

        (self.privateKeyDirectory, self.privateKeyFileName) = os.path.split(self.privateKeyFilePath)
        # sshKeyDist.sshpaths currently assumes that private key is in ~/.ssh
        self.sshPathsObject = sshpaths(self.privateKeyFileName)

    def generateNewKey(self, passphrase, keyComment, keyCreatedSuccessfullyCallback, keyFileAlreadyExistsCallback, passphraseTooShortCallback):

        success = False

        if sys.platform.startswith('win'):
            cmdList = [self.sshPathsObject.sshKeyGenBinary.strip('"'), "-f", self.privateKeyFilePath, "-C", keyComment, "-N", passphrase]
            proc = subprocess.Popen(cmdList,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate('\r\n')

            if stdout is None or str(stdout).strip() == '':
                logger_debug('(1) Got EOF from ssh-keygen binary')
            elif "Your identification has been saved" in stdout:
                success = True
                keyCreatedSuccessfullyCallback()
            elif "passphrase too short" in stdout:
                passphraseTooShortCallback()
            elif 'already exists' in stdout:
                keyFileAlreadyExistsCallback()
            elif 'Could not open a connection to your authentication agent' in stdout:
                logger_debug("Could not open a connection to your authentication agent.")
                failedToConnectToAgentCallback()
            else:
                logger_debug('Got unknown error from ssh-keygen binary')
                logger_debug(stdout)
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
                    logger_debug("Passphrases do not match")
                elif idx == 2:
                    passphraseTooShortCallback()
            elif idx == 1:
                keyFileAlreadyExistsCallback()
            else:
                #logger_debug("1 returning KEY_LOCKED %s %s"%(lp.before,lp.after))
                logger_debug("Unexpected result from attempt to create new key.")
            lp.close()
        return success

    def changePassphrase(self, existingPassphrase, newPassphrase, 
        passphraseUpdatedSuccessfullyCallback,
        existingPassphraseIncorrectCallback,
        newPassphraseTooShortCallback,
        keyLockedCallback):

        success = False

        if sys.platform.startswith('win'):
            cmdList = [self.sshPathsObject.sshKeyGenBinary.strip('"'), "-f", self.privateKeyFilePath, 
                        "-p", "-P", existingPassphrase, "-N", newPassphrase]
            proc = subprocess.Popen(cmdList,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate(input=existingPassphrase + '\r\n')

            if stdout is None or str(stdout).strip() == '':
                logger_debug('(1) Got EOF from ssh-keygen binary')
                keyLockedCallback()
            if "Your identification has been saved" in stdout:
                success = True
                passphraseUpdatedSuccessfullyCallback()
            elif "passphrase too short" in stdout:
                newPassphraseTooShortCallback()
            elif 'Bad pass' in stdout or 'load failed' in stdout:
                logger_debug('Got "Bad pass" from ssh-keygen binary')
                if existingPassphrase == '':
                    keyLockedCallback()
                else:
                    existingPassphraseIncorrectCallback()
            else:
                logger_debug('Got unknown error from ssh-keygen binary')
                logger_debug(stdout)
                keyLockedCallback()
        else:
            # On Linux or BSD/OSX we can use pexpect to talk to ssh-keygen.

            import pexpect

            args = ["-f", self.privateKeyFilePath, "-p"]
            lp = pexpect.spawn(self.sshPathsObject.sshKeyGenBinary, args=args)

            idx = lp.expect(["Enter old passphrase", "Key has comment"])

            if idx == 0:
                logger_debug("sending passphrase to " + self.sshPathsObject.sshKeyGenBinary + " -f " + self.privateKeyFilePath + " -p")
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
                    logger_debug("Passphrases do not match")
                elif idx == 2:
                    newPassphraseTooShortCallback()
            elif idx == 1 or idx == 2:
                existingPassphraseIncorrectCallback()
            else:
                #logger_debug("1 returning KEY_LOCKED %s %s"%(lp.before,lp.after))
                logger_debug("Unexpected result from attempt to change passphrase.")
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

            logger_debug("Removing Launcher public key(s) from agent.")

            publicKeysInAgentProc = subprocess.Popen([self.sshPathsObject.sshAddBinary.strip('"'),"-L"],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            publicKeysInAgent = publicKeysInAgentProc.stdout.readlines()
            for publicKey in publicKeysInAgent:
                if "Launcher" in publicKey:
                    tempPublicKeyFile = tempfile.NamedTemporaryFile(delete=False)
                    tempPublicKeyFile.write(publicKey)
                    tempPublicKeyFile.close()
                    try:
                        removePublicKeyFromAgent = subprocess.Popen([self.sshPathsObject.sshAddBinary.strip('"'),"-d",tempPublicKeyFile.name],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                        stdout, stderr = removePublicKeyFromAgent.communicate()
                        if stderr is not None and len(stderr) > 0:
                            logger_debug(stderr)
                        success = ("Identity removed" in stdout)
                    finally:
                        os.unlink(tempPublicKeyFile.name)
        except:
            logger_debug(traceback.format_exc())
            return False

        return True

    def addKeyToAgent(self, passphrase, keyAddedSuccessfullyCallback, passphraseIncorrectCallback, privateKeyFileNotFoundCallback, failedToConnectToAgentCallback):

        success = False

        if sys.platform.startswith('win'):
            # The patched OpenSSH binary on Windows/cygwin allows us
            # to send the passphrase via STDIN.
            cmdList = [self.sshPathsObject.sshAddBinary.strip('"'), self.privateKeyFilePath]
            logger_debug('on Windows, so running: ' + str(cmdList))
            proc = subprocess.Popen(cmdList,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate(input=passphrase + '\r\n')

            if stdout is None or str(stdout).strip() == '':
                logger_debug('(1) Got EOF from ssh-add binary, probably because an empty passphrase was entered for a passphrase-locked key.')
                passphraseIncorrectCallback()
            elif stdout is not None and "No such file or directory" in stdout:
                privateKeyFileNotFoundCallback()
                return False
            elif "Identity added" in stdout:
                success = True
                keyAddedSuccessfullyCallback()
            elif 'Bad pass' in stdout:
                logger_debug('Got "Bad pass" from ssh-add binary')
                proc.kill()
                passphraseIncorrectCallback()
            elif 'Could not open a connection to your authentication agent' in stdout:
                logger_debug("Could not open a connection to your authentication agent.")
                failedToConnectToAgentCallback()
            else:
                logger_debug('Got unknown error from ssh-add binary')
                logger_debug(stdout)
        else:
            # On Linux or BSD/OSX we can use pexpect to talk to ssh-add.

            import pexpect

            args = [self.privateKeyFilePath]
            lp = pexpect.spawn(self.sshPathsObject.sshAddBinary, args=args)

            idx = lp.expect(["Enter passphrase"])

            if idx == 0:
                lp.sendline(passphrase)

                idx = lp.expect(["Identity added", "Bad pass", pexpect.EOF])
                if idx == 0:
                    success = True
                    keyAddedSuccessfullyCallback()
                elif idx == 1:
                    lp.kill(0)
                    passphraseIncorrectCallback()
                    success = False
                    return success
                elif idx == 2:
                    # ssh-add seems to fail silently if you don't enter a passphrase
                    # It will exit without displaying "Identity added" or "Bad passphrase".
                    lp.kill(0)
                    passphraseIncorrectCallback()
                    success = False
                    return success
            else:
                logger_debug("Unexpected result from attempt to add key.")
            lp.close()
        return success


    def removeKeyFromAgent(self):

        # FIXME
        # We use a method which doesn't require entering the key's passphrase :-)
        # but it just greps for Launcher in the agent's keys, rather than 
        # specifically identifying this key. :-(

        try:
            # Remove key(s) from SSH agent:

            logger_debug("Removing Launcher public key(s) from agent.")

            publicKeysInAgentProc = subprocess.Popen([self.sshPathsObject.sshAddBinary.strip('"'),"-L"],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            publicKeysInAgent = publicKeysInAgentProc.stdout.readlines()
            for publicKey in publicKeysInAgent:
                if "Launcher" in publicKey:
                    tempPublicKeyFile = tempfile.NamedTemporaryFile(delete=False)
                    tempPublicKeyFile.write(publicKey)
                    tempPublicKeyFile.close()
                    try:
                        removePublicKeyFromAgent = subprocess.Popen([self.sshPathsObject.sshAddBinary.strip('"'),"-d",tempPublicKeyFile.name],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                        stdout, stderr = removePublicKeyFromAgent.communicate()
                        if stderr is not None and len(stderr) > 0:
                            logger_debug(stderr)
                        success = ("Identity removed" in stdout)
                    finally:
                        os.unlink(tempPublicKeyFile.name)
        except:
            logger_debug(traceback.format_exc())
            return False

        return True
