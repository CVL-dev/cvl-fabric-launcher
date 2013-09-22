# IdentityMenu.py

import wx
import subprocess
import os
import sys
if os.path.abspath("..") not in sys.path:
    sys.path.append(os.path.abspath(".."))

from cvlsshutils.ChangeKeyPassphraseDialog import ChangeKeyPassphraseDialog
from cvlsshutils.InspectKeyDialog import InspectKeyDialog
from cvlsshutils.ResetKeyDialog import ResetKeyDialog
from cvlsshutils.CreateNewKeyDialog import CreateNewKeyDialog
from cvlsshutils.KeyModel import KeyModel

from logger.Logger import logger

# For now, the private key file path in the CreateNewKeyDialog is read-only.
userCanModifyPrivateKeyFilePath = False

class IdentityMenu(wx.Menu):

    def initialize(self, launcherMainFrame, globalLauncherConfig, globalLauncherPreferencesFilePath):

        self.launcherMainFrame = launcherMainFrame
        self.globalLauncherConfig = globalLauncherConfig
        self.globalLauncherPreferencesFilePath = globalLauncherPreferencesFilePath

        createNewKeyMenuItemId = wx.NewId()
        self.Append(createNewKeyMenuItemId, "Create &new key")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onCreateNewKey, id=createNewKeyMenuItemId)

        inspectKeyMenuItemId = wx.NewId()
        self.Append(inspectKeyMenuItemId, "&Inspect key")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onInspectKey, id=inspectKeyMenuItemId)

        changePassphraseMenuItemId = wx.NewId()
        self.Append(changePassphraseMenuItemId, "&Change passphrase")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onChangePassphrase, id=changePassphraseMenuItemId)

        resetKeyMenuItemId = wx.NewId()
        self.Append(resetKeyMenuItemId, "&Reset key")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onResetKey, id=resetKeyMenuItemId)

        deleteKeyMenuItemId = wx.NewId()
        self.Append(deleteKeyMenuItemId, "&Delete key")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onDeleteKey, id=deleteKeyMenuItemId)

        self.AppendSeparator()

        #privacyOptionsMenuItemId = wx.NewId()
        self.authOpts=wx.MenuItem(self,wx.ID_ANY,"&Authentication options")
        self.AppendItem(self.authOpts)
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onAuthenticationOptions, id=self.authOpts.GetId())
        
        self.usePassword = wx.MenuItem(self,wx.ID_ANY,"Use a password for authentication",kind=wx.ITEM_RADIO)
        self.launcherMainFrame.Bind(wx.EVT_MENU,self.onUsePassword,id=self.usePassword.GetId())
        self.AppendItem(self.usePassword)
        self.useSSHKey = wx.MenuItem(self,wx.ID_ANY,"Use an SSH Key ",kind=wx.ITEM_RADIO)
        self.launcherMainFrame.Bind(wx.EVT_MENU,self.onSSHKey,id=self.useSSHKey.GetId())
        self.AppendItem(self.useSSHKey)
        

        self.AppendSeparator()

        helpAboutKeysMenuItem = wx.NewId()
        self.Append(helpAboutKeysMenuItem, "&Help about keys")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onHelpAboutKeys, id=helpAboutKeysMenuItem)
        self.setRadio()
        self.disableItems()

    def onUsePassword(self,event):
        auth_mode=self.launcherMainFrame.globalOptionsDialog.FindWindowByName('auth_mode')
        auth_mode.SetSelection(self.launcherMainFrame.TEMP_SSH_KEY)
        self.disableItems()
        self.launcherMainFrame.globalOptions['auth_mode']=self.launcherMainFrame.TEMP_SSH_KEY
        self.launcherMainFrame.saveGlobalOptions()

    def onSSHKey(self,event):
        auth_mode=self.launcherMainFrame.globalOptionsDialog.FindWindowByName('auth_mode')
        auth_mode.SetSelection(self.launcherMainFrame.PERM_SSH_KEY)
        self.disableItems()
        self.launcherMainFrame.globalOptions['auth_mode']=self.launcherMainFrame.PERM_SSH_KEY
        self.launcherMainFrame.saveGlobalOptions()

    def setRadio(self):
        state=self.launcherMainFrame.globalOptionsDialog.FindWindowByName('auth_mode').GetSelection()
        if state == self.launcherMainFrame.PERM_SSH_KEY:
            self.useSSHKey.Check(True)
            self.usePassword.Check(False)
        else:
            self.useSSHKey.Check(False)
            self.usePassword.Check(True)
    
    def disableItems(self):
        #print "toggling items"
        state=self.launcherMainFrame.globalOptionsDialog.FindWindowByName('auth_mode').GetSelection()
        #print state
        if state == self.launcherMainFrame.PERM_SSH_KEY:
            enable=True
        else:
            enable=False
        iditems = self.GetMenuItems()
        for item in iditems:
            item.Enable(enable)
        self.authOpts.Enable(True)
        self.usePassword.Enable(True)
        self.useSSHKey.Enable(True)

    def privateKeyExists(self,warnIfNotFoundInLocalSettings=False):

        if warnIfNotFoundInLocalSettings and (not self.globalLauncherConfig.has_option("Global Preferences", "massive_launcher_private_key_path")):
            dlg = wx.MessageDialog(None,
                        "Warning: Launcher key path was not found in your local settings.\n\n"
                        "I'll assume it to be: " + self.launcherMainFrame.keyModel.getPrivateKeyFilePath(),
                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()

        return self.launcherMainFrame.keyModel.privateKeyExists()

    def offerToCreateKey(self):

        dlg = wx.MessageDialog(None,
                        "You don't seem to have a Launcher key yet. The key will be\n" +
                         "generated automatically when you try logging into a remote\n" +
                         "server, e.g. MASSIVE.\n\n" +
                         "Would you like to generate a key now?",
                        "MASSIVE/CVL Launcher", wx.YES_NO | wx.ICON_QUESTION)
        return dlg.ShowModal()


    def createKey(self):

        createNewKeyDialog = CreateNewKeyDialog(None, None, wx.ID_ANY, 'MASSIVE/CVL Launcher Private Key',self.launcherMainFrame.keyModel.getPrivateKeyFilePath(),self.launcherMainFrame.displayStrings)
        createNewKeyDialog.Center()
        if createNewKeyDialog.ShowModal()==wx.ID_OK:
            logger.debug("User pressed OK from CreateNewKeyDialog.")
            password = createNewKeyDialog.getPassphrase()
            def success():
                pass
            def failure():
                pass
            self.launcherMainFrame.keyModel.generateNewKey(password,success,failure,failure)
            createdKey = True
        else:
            logger.debug("User canceled from CreateNewKeyDialog.")
            createdKey= False

        return createdKey


    def deleteKey(self):

        success = self.launcherMainFrame.keyModel.deleteKey(ignoreFailureToConnectToAgent=True)
        #success = success and self.launcherMainFrame.keyModel.removeKeyFromAgent()
        if success:
            message = "Launcher key was successfully deleted!"
            logger.debug(message)
        else:
            message = "An error occured while attempting to delete the existing key."
            logger.debug(message)

        return success


    def onCreateNewKey(self,event):

        if self.privateKeyExists():
            dlg = wx.MessageDialog(self.launcherMainFrame,
                            "You already have a MASSIVE Launcher key.\n\n" +
                            "Do you want to delete your existing key and create a new one?",
                            "MASSIVE/CVL Launcher", wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal()==wx.ID_YES:
                success = self.deleteKey()
                if not success:
                    dlg = wx.MessageDialog(self.launcherMainFrame, 
                        "An error occured while attempting to delete your existing key.",
                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                    dlg.ShowModal()
                    return
            else:
                return

        return self.createKey()

    def launcherKeyIsInAgent(self):

        publicKeyFingerprintInAgent = ""
        key = self.launcherMainFrame.keyModel.fingerprintAgent()
        if key != None:
            sshAddOutComponents = key.split(" ")
            if len(sshAddOutComponents)>1:
                publicKeyFingerprintInAgent = sshAddOutComponents[1]

        return publicKeyFingerprintInAgent != ""


    def onInspectKey(self,event):
        if not self.privateKeyExists(warnIfNotFoundInLocalSettings=userCanModifyPrivateKeyFilePath):
            if self.offerToCreateKey()==wx.ID_YES:
                self.createKey()
            else:
                return

        inspectKeyDialog = InspectKeyDialog(None, wx.ID_ANY, 'MASSIVE/CVL Launcher Key Properties', self.launcherMainFrame.keyModel)
        inspectKeyDialog.Center()
        inspectKeyDialog.ShowModal()


    def onChangePassphrase(self,event):

        if self.privateKeyExists(warnIfNotFoundInLocalSettings=userCanModifyPrivateKeyFilePath):
            changeKeyPassphraseDialog = ChangeKeyPassphraseDialog(self.launcherMainFrame, wx.ID_ANY, 'Change Key Passphrase', self.launcherMainFrame.keyModel)
            changeKeyPassphraseDialog.ShowModal()
        else:
            if self.offerToCreateKey()==wx.ID_YES:
                self.createKey()


    def onResetKey(self,event):

        if self.privateKeyExists(warnIfNotFoundInLocalSettings=userCanModifyPrivateKeyFilePath):
            resetKeyDialog = ResetKeyDialog(self.launcherMainFrame, wx.ID_ANY, 'Reset Key', self.launcherMainFrame.keyModel, self.launcherKeyIsInAgent())
            resetKeyDialog.ShowModal()
        else:
            if self.offerToCreateKey()==wx.ID_YES:
                self.createKey()


    def onDeleteKey(self,event):

        if self.privateKeyExists(warnIfNotFoundInLocalSettings=userCanModifyPrivateKeyFilePath):
            dlg = wx.MessageDialog(self.launcherMainFrame,
                "Are you sure you want to delete your key, located at:\n\n" +
                self.launcherMainFrame.keyModel.getPrivateKeyFilePath() +
                " ?",
                "MASSIVE/CVL Launcher", wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal()==wx.ID_YES:
                success = self.deleteKey()
                if success:
                    message = "Your Launcher key was successfully deleted!"
                else:
                    message = "An error occured while attempting to delete your key."
                dlg = wx.MessageDialog(self.launcherMainFrame, message,
                    "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
        else:
            dlg = wx.MessageDialog(None,
                        "You don't seem to have a Launcher key yet. The key will be\n" +
                         "generated automatically when you try logging into a remote\n" +
                         "server, e.g. MASSIVE.",
                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()


    def onAuthenticationOptions(self,event):
        from optionsDialog import LAUNCHER_VNC_OPTIONS_AUTHENTICATION_TAB_INDEX
        self.launcherMainFrame.onOptions(event, tabIndex=LAUNCHER_VNC_OPTIONS_AUTHENTICATION_TAB_INDEX)

    def onHelpAboutKeys(self,event):
        from help.HelpController import helpController
        if helpController is not None and helpController.initializationSucceeded:
            helpController.Display("SSH Keys")
        else:
            wx.MessageBox("Unable to open: " + helpController.launcherHelpUrl,
                          "Error", wx.OK|wx.ICON_EXCLAMATION)

