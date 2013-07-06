# PrivateKey.py

class PrivateKeyModel():
    def generatePrivateKey(self):
        print "generatePrivateKey"

    def changePassphrase(self):

        print "changePassphrase"

        if sys.platform.startswith('win'):
            # The patched OpenSSH binary on Windows/cygwin allows us
            # to send the passphrase via STDIN.
            cmdList = [self.sshPathsObject.sshKeyGenBinary, "-f", double_quote(self.privateKeyFilePath), "-p"]
            #cmd = self.keydistObject.sshpaths.sshAddBinary + ' ' + double_quote(self.keydistObject.sshpaths.sshKeyPath)
            #logger_debug('on Windows, so running: ' + cmd)
            stdout, stderr = subprocess.Popen(cmdList,
                                              stdin=subprocess.PIPE,
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT,
                                              universal_newlines=True).communicate(input=self.existingPassphraseField.GetValue + '\r\n')

            if stdout is None or str(stdout).strip() == '':
                #logger_debug('Got EOF from ssh-add binary')
                print 'Got EOF from ssh-add binary'
                #newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
            elif 'Identity added' in stdout:
                #logger_debug('Got "Identity added" from ssh-add binary')
                print 'Got "Identity added" from ssh-add binary'
                #newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_GETPUBKEY, self.keydistObject)
            elif 'Bad pass' in stdout:
                #logger_debug('Got "Bad pass" from ssh-add binary')
                print 'Got "Bad pass" from ssh-add binary'
                #if passphrase == '':
                    #newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED, self.keydistObject)
                #else:
                    #newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_WRONGPASS, self.keydistObject)
            else:
                #logger_debug('Got unknown error from ssh-add binary')
                print 'Got unknown error from ssh-add binary'
                #newevent = KeyDist.sshKeyDistEvent(KeyDist.EVT_KEYDIST_KEY_LOCKED,self.keydistObject)
        else:
            # On Linux or BSD/OSX we can use pexpect to talk to ssh-keygen.

            import pexpect

            args = ["-f", self.privateKeyFilePath, "-p"]
            lp = pexpect.spawn(self.sshPathsObject.sshKeyGenBinary, args=args)

            idx = lp.expect(["Enter old passphrase", "Key has comment"])

            if idx == 0:
                #logger_debug("sending passphrase to " + sshKeyGenBinary + " -f " + self.privateKeyFilePath + " -p")
                lp.sendline(self.existingPassphraseField.GetValue())

            idx = lp.expect(["Enter new passphrase", "Bad passphrase", pexpect.EOF])

            if idx == 0:
                lp.sendline(self.newPassphraseField.GetValue())
                idx = lp.expect(["Enter same passphrase again"])
                lp.sendline(self.repeatNewPassphraseField.GetValue())
                idx = lp.expect(["Your identification has been saved", "Pass phrases do not match.", "passphrase too short"])
                if idx == 0:
                    print "Passphrase updated successfully :-)"
                elif idx == 1:
                    print "Passphrases do not match"
                elif idx == 2:
                    print "Passphrase is too short"
            elif idx == 1:
                message = "Your existing passphrase appears to be incorrect.\nPlease enter it again."
                dlg = wx.MessageDialog(self, message,
                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                self.existingPassphraseField.SetSelection(-1,-1)
                self.existingPassphraseField.SetFocus()
                return
            else:
                #logger_debug("1 returning KEY_LOCKED %s %s"%(lp.before,lp.after))
                print "Unexpected result from attempt to change passphrase."
                return
            lp.close()

    def deleteKey(self):
        print "deleteKey"

privateKeyModelObject = PrivateKeyModel()
