# deleteKey.py

import os
import sys
import subprocess
import tempfile
import traceback

if os.path.abspath("..") not in sys.path:
    sys.path.append(os.path.abspath(".."))
from sshKeyDist import sshpaths

class DeleteKey():
    def deleteKeyAndRemoveFromAgent(self, privateKeyPath):
        # Delete key

        # Should we ask for the passphrase before deleting the key?

        (self.privateKeyDirectory, self.privateKeyFileName) = os.path.split(privateKeyPath)
        # sshKeyDist.sshpaths currently assumes that private key is in ~/.ssh
        self.sshPathsObject = sshpaths(self.privateKeyFileName)

        try:

            os.unlink(privateKeyPath)

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


