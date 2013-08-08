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


class IdentityMenu(wx.Menu):

    def initialize(self, launcherMainFrame, massiveLauncherConfig, massiveLauncherPreferencesFilePath):

        self.launcherMainFrame = launcherMainFrame
        self.massiveLauncherConfig = massiveLauncherConfig
        self.massiveLauncherPreferencesFilePath = massiveLauncherPreferencesFilePath

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

        privacyOptionsMenuItemId = wx.NewId()
        self.Append(privacyOptionsMenuItemId, "&Privacy options")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onPrivacyOptions, id=privacyOptionsMenuItemId)

        self.AppendSeparator()

        helpAboutKeysMenuItem = wx.NewId()
        self.Append(helpAboutKeysMenuItem, "&Help about keys")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onHelpAboutKeys, id=helpAboutKeysMenuItem)


    def privateKeyExists(self, warnIfNotFoundInLocalSettings):

        self.privateKeyFilePath = os.path.join(os.path.expanduser('~'), '.ssh', "MassiveLauncherKey")
        if self.massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_launcher_private_key_path"):
            self.privateKeyFilePath = self.massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_launcher_private_key_path")
        else:
            defaultKeyPath = os.path.join(os.path.expanduser('~'), '.ssh', "MassiveLauncherKey")
            if warnIfNotFoundInLocalSettings:
                dlg = wx.MessageDialog(None,
                            "Warning: Launcher key path was not found in your local settings.\n\n"
                            "I'll assume it to be: " + defaultKeyPath,
                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
            self.massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_launcher_private_key_path", defaultKeyPath)
            with open(self.massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                self.massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        #self.sshPathsObject = sshpaths

        return os.path.exists(self.privateKeyFilePath)


    def offerToCreateKey(self):

        dlg = wx.MessageDialog(None,
                        "You don't seem to have a Launcher key yet. The key will be\n" +
                         "generated automatically when you try logging into a remote\n" +
                         "server, e.g. MASSIVE.\n\n" +
                         "Would you like to generate a key now?",
                        "MASSIVE/CVL Launcher", wx.YES_NO | wx.ICON_QUESTION)
        return dlg.ShowModal()


    def createKey(self):

        createNewKeyDialog = CreateNewKeyDialog(None, wx.ID_ANY, 'MASSIVE/CVL Launcher Private Key')
        createNewKeyDialog.Center()
        if createNewKeyDialog.ShowModal()==wx.ID_OK:
            logger.debug("User pressed OK from CreateNewKeyDialog.")
            createdKey = True
        else:
            logger.debug("User canceled from CreateNewKeyDialog.")
            createdKey= False

        return createdKey


    def deleteKey(self):

        keyModelObject = KeyModel(self.privateKeyFilePath)
        success = keyModelObject.deleteKeyAndRemoveFromAgent()
        if success:
            message = "Launcher key was successfully deleted!"
            logger.debug(message)
        else:
            message = "An error occured while attempting to delete the existing key."
            logger.debug(message)
            dlg = wx.MessageDialog(self.launcherMainFrame, message,
                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()

        return success


    def onCreateNewKey(self,event):

        if self.privateKeyExists(warnIfNotFoundInLocalSettings=False):
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

        createNewKeyDialog = CreateNewKeyDialog(self.launcherMainFrame, wx.ID_ANY, 'MASSIVE/CVL Launcher Private Key')
        createNewKeyDialog.Center()
        if createNewKeyDialog.ShowModal()==wx.ID_OK:
            logger.debug("User pressed OK from CreateNewKeyDialog.")
        else:
            logger.debug("User canceled from CreateNewKeyDialog.")
            return False


    def keyIsInAgent(self):

        publicKeyFingerprintInAgent = ""
        # This will give an error if no agent is running:
        proc = subprocess.Popen([self.sshPathsObject.sshAddBinary.strip('"'),"-l"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        fingerprintLinesInAgent = proc.stdout.readlines()
        for fingerprintLine in fingerprintLinesInAgent:
            if "Launcher" in fingerprintLine:
                sshAddOutComponents = fingerprintLine.split(" ")
                if len(sshAddOutComponents)>1:
                    publicKeyFingerprintInAgent = sshAddOutComponents[1]
        return publicKeyFingerprintInAgent != ""


    def onInspectKey(self,event):
        if not self.privateKeyExists(warnIfNotFoundInLocalSettings=True):
            if self.offerToCreateKey()==wx.ID_YES:
                self.createKey()
            else:
                return

        inspectKeyDialog = InspectKeyDialog(None, wx.ID_ANY, 'MASSIVE/CVL Launcher Key Properties', self.launcherMainFrame.sshpaths)
        inspectKeyDialog.Center()
        inspectKeyDialog.ShowModal()


    def onChangePassphrase(self,event):

        if self.privateKeyExists(warnIfNotFoundInLocalSettings=True):
            changeKeyPassphraseDialog = ChangeKeyPassphraseDialog(self.launcherMainFrame, wx.ID_ANY, 'Change Key Passphrase', self.launcherMainFrame.sshpaths)
            if changeKeyPassphraseDialog.ShowModal()==wx.ID_OK:
                dlg = wx.MessageDialog(self.launcherMainFrame,
                    "Passphrase changed successfully!",
                    "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
        else:
            if self.offerToCreateKey()==wx.ID_YES:
                self.createKey()


    def onResetKey(self,event):

        if self.privateKeyExists(warnIfNotFoundInLocalSettings=True):
            resetKeyDialog = ResetKeyDialog(self.launcherMainFrame, wx.ID_ANY, 'Reset Key', self.privateKeyFilePath, self.keyIsInAgent())
            resetKeyDialog.ShowModal()
        else:
            if self.offerToCreateKey()==wx.ID_YES:
                self.createKey()


    def onDeleteKey(self,event):

        if self.privateKeyExists(warnIfNotFoundInLocalSettings=True):
            dlg = wx.MessageDialog(self.launcherMainFrame,
                "Are you sure you want to delete your key?",
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


    def onPrivacyOptions(self,event):
        from optionsDialog import LAUNCHER_VNC_OPTIONS_PRIVACY_TAB_INDEX
        self.launcherMainFrame.onOptions(event, tabIndex=LAUNCHER_VNC_OPTIONS_PRIVACY_TAB_INDEX)

    def onHelpAboutKeys(self,event):
        from help.HelpController import helpController
        if helpController is not None and helpController.initializationSucceeded:
            helpController.Display("SSH Keys")
        else:
            wx.MessageBox("Unable to open: " + helpController.launcherHelpUrl,
                          "Error", wx.OK|wx.ICON_EXCLAMATION)

