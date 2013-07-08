#!/usr/bin/python

import wx
import wx.html
import os
import sys
import subprocess
import re

from KeyModel import KeyModel

if os.path.abspath("..") not in sys.path:
    sys.path.append(os.path.abspath(".."))
from sshKeyDist import KeyDist
from sshKeyDist import sshpaths

global helpController
helpController = None

from utilityFunctions import logger_debug, configureLogger

class InspectKeyDialog(wx.Dialog):
    def __init__(self, parent, id, title, privateKeyFilePath):
        wx.Dialog.__init__(self, parent, id, title, wx.DefaultPosition)
        self.inspectKeyDialogPanel = wx.Panel(self, wx.ID_ANY)

        self.privateKeyFilePath = privateKeyFilePath

        (self.privateKeyDirectory, self.privateKeyFileName) = os.path.split(self.privateKeyFilePath)
        # sshKeyDist.sshpaths currently assumes that private key is in ~/.ssh
        self.sshPathsObject = sshpaths(self.privateKeyFileName)

        # I really miss Java Swing's BorderLayout and
        # BorderFactory.createEmptyBorder(...) sometimes.
        # All of this border stuff should be encapsulated in a class.

        self.inspectKeyDialogPanelSizer = wx.FlexGridSizer(1,3, hgap=15, vgap=15)
        self.inspectKeyDialogPanel.SetSizer(self.inspectKeyDialogPanelSizer)

        self.inspectKeyDialogLeftPanel = wx.Panel(self.inspectKeyDialogPanel, wx.ID_ANY)
        self.inspectKeyDialogPanelSizer.Add(self.inspectKeyDialogLeftPanel)
        self.inspectKeyDialogMiddlePanel = wx.Panel(self.inspectKeyDialogPanel, wx.ID_ANY)
        self.inspectKeyDialogPanelSizer.Add(self.inspectKeyDialogMiddlePanel, flag=wx.EXPAND)
        self.inspectKeyDialogRightPanel = wx.Panel(self.inspectKeyDialogPanel, wx.ID_ANY)
        self.inspectKeyDialogPanelSizer.Add(self.inspectKeyDialogRightPanel)

        self.inspectKeyDialogMiddlePanelSizer = wx.FlexGridSizer(3,1, hgap=15, vgap=15)
        self.inspectKeyDialogMiddlePanel.SetSizer(self.inspectKeyDialogMiddlePanelSizer)

        self.inspectKeyDialogTopPanel = wx.Panel(self.inspectKeyDialogMiddlePanel, wx.ID_ANY)
        self.inspectKeyDialogMiddlePanelSizer.Add(self.inspectKeyDialogTopPanel)
        self.inspectKeyDialogCenterPanel = wx.Panel(self.inspectKeyDialogMiddlePanel, wx.ID_ANY)
        self.inspectKeyDialogMiddlePanelSizer.Add(self.inspectKeyDialogCenterPanel, flag=wx.EXPAND)
        self.inspectKeyDialogBottomPanel = wx.Panel(self.inspectKeyDialogMiddlePanel, wx.ID_ANY)
        self.inspectKeyDialogMiddlePanelSizer.Add(self.inspectKeyDialogBottomPanel)

        self.inspectKeyDialogCenterPanelSizer = wx.FlexGridSizer(10,1)
        self.inspectKeyDialogCenterPanel.SetSizer(self.inspectKeyDialogCenterPanelSizer)

        # Instructions label

        self.instructionsLabel = wx.StaticText(self.inspectKeyDialogCenterPanel, wx.ID_ANY, 
            "The Launcher needs a private key to authenticate against remote servers such as MASSIVE.\n\n" + 
            "Here, you can inspect the properties of your MASSIVE Launcher key.")
        self.inspectKeyDialogCenterPanelSizer.Add(self.instructionsLabel, flag=wx.EXPAND|wx.BOTTOM, border=15)

        # Key properties panel

        self.keyPropertiesPanel = wx.Panel(self.inspectKeyDialogCenterPanel, wx.ID_ANY)

        self.keyPropertiesGroupBox = wx.StaticBox(self.keyPropertiesPanel, wx.ID_ANY, label="Key properties")
        self.keyPropertiesGroupBoxSizer = wx.StaticBoxSizer(self.keyPropertiesGroupBox, wx.VERTICAL)
        self.keyPropertiesPanel.SetSizer(self.keyPropertiesGroupBoxSizer)

        self.innerKeyPropertiesPanel = wx.Panel(self.keyPropertiesPanel, wx.ID_ANY)
        self.innerKeyPropertiesPanelSizer = wx.FlexGridSizer(10,2, hgap=10)
        self.innerKeyPropertiesPanel.SetSizer(self.innerKeyPropertiesPanelSizer)

        self.innerKeyPropertiesPanelSizer.AddGrowableCol(1)

        # Private key location

        self.privateKeyLocationLabel = wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, "Private key file:")
        self.innerKeyPropertiesPanelSizer.Add(self.privateKeyLocationLabel)

        self.privateKeyLocationField = wx.TextCtrl(self.innerKeyPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)
        self.privateKeyLocationField.SetValue(self.privateKeyFilePath)
        self.innerKeyPropertiesPanelSizer.Add(self.privateKeyLocationField, flag=wx.EXPAND)

        # Blank space

        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))
        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))

        # Public key location

        self.publicKeyLocationLabel = wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, "Public key file:")
        self.innerKeyPropertiesPanelSizer.Add(self.publicKeyLocationLabel)

        self.publicKeyLocationField = wx.TextCtrl(self.innerKeyPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)
        self.populatePublicKeyLocationField()
        self.innerKeyPropertiesPanelSizer.Add(self.publicKeyLocationField, flag=wx.EXPAND)

        # Blank space

        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))
        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))

        # Public key fingerprint

        self.publicKeyFingerprintLabel = wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, "Public key fingerprint:")
        self.innerKeyPropertiesPanelSizer.Add(self.publicKeyFingerprintLabel)

        self.publicKeyFingerprintField = wx.TextCtrl(self.innerKeyPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)

        self.innerKeyPropertiesPanelSizer.Add(self.publicKeyFingerprintField, flag=wx.EXPAND)

        # Blank space

        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))
        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))

        # Key type

        self.keyTypeLabel = wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, "Key type:")
        self.innerKeyPropertiesPanelSizer.Add(self.keyTypeLabel)

        #self.keyTypeField = wx.TextCtrl(self.innerKeyPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)
        #self.keyTypeField.SetValue(keyType)
        self.keyTypeField = wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, "")

        self.populateFingerprintAndKeyTypeFields()

        self.innerKeyPropertiesPanelSizer.Add(self.keyTypeField, flag=wx.EXPAND)

        self.innerKeyPropertiesPanel.Fit()
        self.keyPropertiesGroupBoxSizer.Add(self.innerKeyPropertiesPanel, flag=wx.EXPAND)
        self.keyPropertiesPanel.Fit()

        self.inspectKeyDialogCenterPanelSizer.Add(self.keyPropertiesPanel, flag=wx.EXPAND)

        # Key in agent explanation label

        self.keyInAgentExplanationLabel = wx.StaticText(self.inspectKeyDialogCenterPanel, wx.ID_ANY, 
            "When you log into a remote server, the Launcher will add your key to an SSH agent,\n" +
            "if it has not been added already. If SSH_AUTH_SOCK is non-empty and the Launcher's\n" +
            "public key fingerprint is present in the SSH agent, then the Launcher key has been\n" +
            "successfully added to the SSH agent.")
        self.inspectKeyDialogCenterPanelSizer.Add(self.keyInAgentExplanationLabel, flag=wx.EXPAND|wx.BOTTOM|wx.TOP, border=15)

        # SSH Agent Properties

        self.agentPropertiesPanel = wx.Panel(self.inspectKeyDialogCenterPanel, wx.ID_ANY)

        self.agentPropertiesGroupBox = wx.StaticBox(self.agentPropertiesPanel, wx.ID_ANY, label="Agent properties")
        self.agentPropertiesGroupBoxSizer = wx.StaticBoxSizer(self.agentPropertiesGroupBox, wx.VERTICAL)
        self.agentPropertiesPanel.SetSizer(self.agentPropertiesGroupBoxSizer)

        self.innerAgentPropertiesPanel = wx.Panel(self.agentPropertiesPanel, wx.ID_ANY)
        self.innerAgentPropertiesPanelSizer = wx.FlexGridSizer(10,2, hgap=10)
        self.innerAgentPropertiesPanelSizer.AddGrowableCol(1)
        self.innerAgentPropertiesPanel.SetSizer(self.innerAgentPropertiesPanelSizer)

        self.innerAgentPropertiesPanelSizer.AddGrowableCol(1)

        self.sshAuthSockLabel = wx.StaticText(self.innerAgentPropertiesPanel, wx.ID_ANY, "SSH_AUTH_SOCK:")
        self.innerAgentPropertiesPanelSizer.Add(self.sshAuthSockLabel)

        self.sshAuthSockField = wx.TextCtrl(self.innerAgentPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)

        self.populateSshAuthSockField()

        self.innerAgentPropertiesPanelSizer.Add(self.sshAuthSockField, flag=wx.EXPAND)

        # Blank space

        self.innerAgentPropertiesPanelSizer.Add(wx.StaticText(self.innerAgentPropertiesPanel, wx.ID_ANY, ""))
        self.innerAgentPropertiesPanelSizer.Add(wx.StaticText(self.innerAgentPropertiesPanel, wx.ID_ANY, ""))

        self.fingerprintInAgentLabel = wx.StaticText(self.innerAgentPropertiesPanel, wx.ID_ANY, "Launcher key fingerprint in agent:")
        self.innerAgentPropertiesPanelSizer.Add(self.fingerprintInAgentLabel)

        self.fingerprintInAgentField = wx.TextCtrl(self.innerAgentPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)

        self.populateFingerprintInAgentField()

        self.innerAgentPropertiesPanelSizer.Add(self.fingerprintInAgentField, flag=wx.EXPAND)

        self.inspectKeyDialogCenterPanelSizer.Add(self.agentPropertiesPanel, flag=wx.EXPAND)

        # Blank space

        self.innerAgentPropertiesPanelSizer.Add(wx.StaticText(self.innerAgentPropertiesPanel, wx.ID_ANY, ""))

        self.addKeyToOrRemoveKeyFromAgentButton = wx.Button(self.innerAgentPropertiesPanel, wx.ID_ANY, "")
        if self.fingerprintInAgentField.GetValue()=="":
            self.addKeyToOrRemoveKeyFromAgentButton.SetLabel("Add MASSIVE Launcher key to agent")
        else:
            self.addKeyToOrRemoveKeyFromAgentButton.SetLabel("Remove MASSIVE Launcher key from agent")

        self.innerAgentPropertiesPanelSizer.Add(self.addKeyToOrRemoveKeyFromAgentButton, flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
        self.Bind(wx.EVT_BUTTON, self.onAddKeyToOrRemoveFromAgent, id=self.addKeyToOrRemoveKeyFromAgentButton.GetId())

        self.innerAgentPropertiesPanel.Fit()
        self.agentPropertiesGroupBoxSizer.Add(self.innerAgentPropertiesPanel, flag=wx.EXPAND)
        self.agentPropertiesPanel.Fit()

        # Blank space

        self.inspectKeyDialogCenterPanelSizer.Add(wx.StaticText(self.inspectKeyDialogCenterPanel, wx.ID_ANY, ""))

        # Buttons panel

        self.buttonsPanel = wx.Panel(self.inspectKeyDialogCenterPanel, wx.ID_ANY)
        self.buttonsPanelSizer = wx.FlexGridSizer(1,5, hgap=5, vgap=5)
        self.buttonsPanel.SetSizer(self.buttonsPanelSizer)

        self.deleteKeyButton = wx.Button(self.buttonsPanel, wx.NewId(), "Delete Key")
        self.buttonsPanelSizer.Add(self.deleteKeyButton, flag=wx.BOTTOM, border=5)
        self.Bind(wx.EVT_BUTTON, self.onDeleteKey, id=self.deleteKeyButton.GetId())

        self.changePassphraseButton = wx.Button(self.buttonsPanel, wx.NewId(), "Change Passphrase")
        self.buttonsPanelSizer.Add(self.changePassphraseButton, flag=wx.BOTTOM, border=5)
        self.Bind(wx.EVT_BUTTON, self.onChangePassphrase, id=self.changePassphraseButton.GetId())

        self.resetPassphraseButton = wx.Button(self.buttonsPanel, wx.NewId(), "Reset Passphrase")
        self.buttonsPanelSizer.Add(self.resetPassphraseButton, flag=wx.BOTTOM, border=5)
        self.Bind(wx.EVT_BUTTON, self.onResetPassphrase, id=self.resetPassphraseButton.GetId())

        self.helpButton = wx.Button(self.buttonsPanel, wx.NewId(), "Help")
        self.buttonsPanelSizer.Add(self.helpButton, flag=wx.BOTTOM, border=5)
        self.Bind(wx.EVT_BUTTON, self.onHelp, id=self.helpButton.GetId())

        self.closeButton = wx.Button(self.buttonsPanel, wx.NewId(), "Close")
        self.closeButton.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.onClose, id=self.closeButton.GetId())
        self.buttonsPanelSizer.Add(self.closeButton, flag=wx.BOTTOM, border=5)

        self.buttonsPanel.Fit()

        self.inspectKeyDialogCenterPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT)

        # Calculate positions on dialog, using sizers

        self.inspectKeyDialogCenterPanel.Fit()
        self.inspectKeyDialogMiddlePanel.Fit()
        self.inspectKeyDialogPanel.Fit()
        self.Fit()
        self.CenterOnParent()

    def reloadAllFields(self):
        self.privateKeyLocationField.SetValue(self.privateKeyFilePath)
        self.populatePublicKeyLocationField()
        self.populateFingerprintAndKeyTypeFields()
        self.populateFingerprintInAgentField()
        if self.fingerprintInAgentField.GetValue()=="":
            self.addKeyToOrRemoveKeyFromAgentButton.SetLabel("Add MASSIVE Launcher key to agent")
        else:
            self.addKeyToOrRemoveKeyFromAgentButton.SetLabel("Remove MASSIVE Launcher key from agent")

    def populateSshAuthSockField(self):
        if "SSH_AUTH_SOCK" not in os.environ:
            self.startAgent()
        if "SSH_AUTH_SOCK" in os.environ:
            self.sshAuthSockField.SetValue(os.environ["SSH_AUTH_SOCK"])
        else:
            self.sshAuthSockField.SetValue("")

    def populatePublicKeyLocationField(self):
        self.publicKeyFilePath = ""
        if os.path.exists(self.privateKeyFilePath + ".pub"):
            self.publicKeyFilePath = self.privateKeyFilePath + ".pub"
        self.publicKeyLocationField.SetValue(self.publicKeyFilePath)

    def populateFingerprintAndKeyTypeFields(self):

        # ssh-keygen can give us public key fingerprint, key type and size from private key

        proc = subprocess.Popen([self.sshPathsObject.sshKeyGenBinary.strip('"'),"-yl","-f",self.privateKeyFilePath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        stdout,stderr = proc.communicate()
        sshKeyGenOutComponents = stdout.split(" ")
        if len(sshKeyGenOutComponents)>1:
            publicKeyFingerprint = sshKeyGenOutComponents[1]
        else:
            publicKeyFingerprint = ""
        self.publicKeyFingerprintField.SetValue(publicKeyFingerprint)
        if len(sshKeyGenOutComponents)>3:
            keyType = sshKeyGenOutComponents[-1].strip().strip("(").strip(")")
        else:
            keyType = ""
        self.keyTypeField.SetLabel(keyType)

    def populateFingerprintInAgentField(self):

        # ssh-add -l | grep Launcher

        publicKeyFingerprintInAgent = ""
        proc = subprocess.Popen([self.sshPathsObject.sshAddBinary.strip('"'),"-l"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        fingerprintLinesInAgent = proc.stdout.readlines()
        for fingerprintLine in fingerprintLinesInAgent:
            if "Launcher" in fingerprintLine:
                sshAddOutComponents = fingerprintLine.split(" ")
                if len(sshAddOutComponents)>1:
                    publicKeyFingerprintInAgent = sshAddOutComponents[1]
        self.fingerprintInAgentField.SetValue(publicKeyFingerprintInAgent)

    def onAddKeyToOrRemoveFromAgent(self, event):
        if self.addKeyToOrRemoveKeyFromAgentButton.GetLabel()=="Add MASSIVE Launcher key to agent":
            keyModelObject = KeyModel(self.privateKeyFilePath)

            ppd = KeyDist.passphraseDialog(None,wx.ID_ANY,'Unlock Key',"Please enter the passphrase for the key","OK","Cancel")
            (canceled,passphrase) = ppd.getPassword()
            if (canceled):
                return
            else:
                def keyAddedSuccessfullyCallback():
                    logger_debug("InspectKeyDialog.onAddKeyToOrRemoveFromAgent callback: Key added successfully! :-)")
                def passphraseIncorrectCallback():
                    logger_debug("InspectKeyDialog.onAddKeyToOrRemoveFromAgent callback: Passphrase incorrect. :-(")
                def privateKeyFileNotFoundCallback():
                    logger_debug("InspectKeyDialog.onAddKeyToOrRemoveFromAgent callback: Private key file not found. :-(")
                def failedToConnectToAgentCallback():
                    dlg = wx.MessageDialog(self, 
                        "Could not open a connection to your authentication agent.",
                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                    dlg.ShowModal()
                success = keyModelObject.addKeyToAgent(passphrase, keyAddedSuccessfullyCallback, passphraseIncorrectCallback, privateKeyFileNotFoundCallback, failedToConnectToAgentCallback)
                if success:
                    logger_debug("Adding key to agent succeeded.")
                    self.populateFingerprintInAgentField()
                    self.addKeyToOrRemoveKeyFromAgentButton.SetLabel("Remove MASSIVE Launcher key from agent")
                else:
                    logger_debug("Adding key to agent failed.")
        elif self.addKeyToOrRemoveKeyFromAgentButton.GetLabel()=="Remove MASSIVE Launcher key from agent":
            keyModelObject = KeyModel(self.privateKeyFilePath)
            success = keyModelObject.removeKeyFromAgent()
            if success:
                self.populateFingerprintInAgentField()
                self.addKeyToOrRemoveKeyFromAgentButton.SetLabel("Add MASSIVE Launcher key to agent")

    def onDeleteKey(self,event):
        dlg = wx.MessageDialog(self, 
            "Are you sure you want to delete your key?",
            "MASSIVE/CVL Launcher", wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal()==wx.ID_YES:

            keyModelObject = KeyModel(self.privateKeyFilePath)
            success = keyModelObject.deleteKeyAndRemoveFromAgent()
            if success:
                message = "Your Launcher key was successfully deleted! :-)"
            else:
                message = "An error occured while attempting to delete your key. :-("
            dlg = wx.MessageDialog(self, 
                message,
                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()

            if success:
                self.Show(False)

    def onChangePassphrase(self,event):
        from ChangeKeyPassphraseDialog import ChangeKeyPassphraseDialog
        changeKeyPassphraseDialog = ChangeKeyPassphraseDialog(self, wx.ID_ANY, 'Change Key Passphrase', self.privateKeyFilePath)
        if changeKeyPassphraseDialog.ShowModal()==wx.ID_OK:
            logger_debug("Passphrase changed successfully! :-)")

    def onResetPassphrase(self, event):
        from ResetKeyPassphraseDialog import ResetKeyPassphraseDialog
        keyInAgent = self.fingerprintInAgentField.GetValue()!=""
        resetKeyPassphraseDialog = ResetKeyPassphraseDialog(self, wx.ID_ANY, 'Reset Key Passphrase', self.privateKeyFilePath, keyInAgent)
        resetKeyPassphraseDialog.ShowModal()

        self.reloadAllFields()

    def onHelp(self, event):
        global helpController
        if helpController is None:
            helpController = wx.html.HtmlHelpController()
            launcherHelpFile = "helpfiles/launcher.hhp"
            if not helpController.AddBook(launcherHelpFile):
                wx.MessageBox("Unable to open: " + launcherHelpFile,
                              "Error", wx.OK|wx.ICON_EXCLAMATION)
        #helpController.DisplayContents()
        helpController.Display("SSH Keys")

    def onClose(self, event):
        self.Show(False)

    def startAgent(self):
        agentenv = None
        try:
            agentenv = os.environ['SSH_AUTH_SOCK']
        except:
            try:
                agent = subprocess.Popen(self.sshPathsObject.sshAgentBinary.strip('"'),stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
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
                    logger_debug("I tried to start an ssh agent, but failed with the error message %s"%str(stdout))
                    return
            except Exception as e:
                logger_debug(message="I tried to start an ssh agent, but failed with the error message %s" % str(e))
                return


class MyApp(wx.App):
    def OnInit(self):

        configureLogger('launcher')

        import appdirs
        import ConfigParser
        appDirs = appdirs.AppDirs("MASSIVE Launcher", "Monash University")
        appUserDataDir = appDirs.user_data_dir
        # Add trailing slash:
        appUserDataDir = os.path.join(appUserDataDir,"")
        if not os.path.exists(appUserDataDir):
            os.makedirs(appUserDataDir)

        global massiveLauncherConfig
        massiveLauncherConfig = ConfigParser.RawConfigParser(allow_no_value=True)

        massiveLauncherPreferencesFilePath = os.path.join(appUserDataDir,"MASSIVE Launcher Preferences.cfg")
        if os.path.exists(massiveLauncherPreferencesFilePath):
            massiveLauncherConfig.read(massiveLauncherPreferencesFilePath)
        if not massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")

        massiveLauncherPrivateKeyPath = os.path.join(os.path.expanduser('~'), '.ssh', "MassiveLauncherKey")
        if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_launcher_private_key_path"):
            massiveLauncherPrivateKeyPath = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_launcher_private_key_path")
        else:
            defaultKeyPath = os.path.join(os.path.expanduser('~'), '.ssh', "MassiveLauncherKey")
            dlg = wx.MessageDialog(None, 
                            "Warning: Launcher key path was not found in your local settings.\n\n"
                            "I'll assume it to be: " + defaultKeyPath,
                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_launcher_private_key_path",
                defaultKeyPath)
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        if not os.path.exists(massiveLauncherPrivateKeyPath):
            dlg = wx.MessageDialog(None, 
                            "You don't seem to have a Launcher key yet. The key will be\n" +
                             "generated automatically when you try logging into a remote\n" +
                             "server, e.g. MASSIVE.\n\n" +
                             "Would you like to generate a key now?",
                            "MASSIVE/CVL Launcher", wx.YES_NO | wx.ICON_INFORMATION)
            if dlg.ShowModal()==wx.ID_YES:
                from CreateNewKeyDialog import CreateNewKeyDialog
                createNewKeyDialog = CreateNewKeyDialog(None, wx.ID_ANY, 'MASSIVE/CVL Launcher Private Key')
                createNewKeyDialog.Center()
                if createNewKeyDialog.ShowModal()==wx.ID_OK:
                    logger_debug("User pressed OK from CreateNewKeyDialog.")
                else:
                    logger_debug("User canceled from CreateNewKeyDialog.")
                    return False
            else:
                logger_debug("User said they didn't want to create a key now.")
                return False

        inspectKeyDialog = InspectKeyDialog(None, wx.ID_ANY, 'MASSIVE/CVL Launcher Key Properties', massiveLauncherPrivateKeyPath)
        inspectKeyDialog.Center()
        inspectKeyDialog.ShowModal()
        return True

#app = MyApp(0)
#app.MainLoop()
