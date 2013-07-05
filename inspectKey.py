#!/usr/bin/python

import wx
import wx.html
import os
import sys

global helpController
helpController = None

class InspectKeyDialog(wx.Dialog):
    def __init__(self, parent, id, title, massiveLauncherPrivateKeyPath):
        wx.Dialog.__init__(self, parent, id, title, wx.DefaultPosition)
        self.inspectKeyDialogPanel = wx.Panel(self, wx.ID_ANY)

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
        self.privateKeyLocationField.SetValue(massiveLauncherPrivateKeyPath)
        self.innerKeyPropertiesPanelSizer.Add(self.privateKeyLocationField, flag=wx.EXPAND)

        # Blank space

        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))
        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))

        # Public key location

        self.publicKeyLocationLabel = wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, "Public key file:")
        self.innerKeyPropertiesPanelSizer.Add(self.publicKeyLocationLabel)

        self.publicKeyLocationField = wx.TextCtrl(self.innerKeyPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)
        massiveLauncherPublicKeyPath = ""
        if os.path.exists(massiveLauncherPrivateKeyPath + ".pub"):
            massiveLauncherPublicKeyPath = massiveLauncherPrivateKeyPath + ".pub"
        self.publicKeyLocationField.SetValue(massiveLauncherPublicKeyPath)
        self.innerKeyPropertiesPanelSizer.Add(self.publicKeyLocationField, flag=wx.EXPAND)

        # Blank space

        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))
        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))

        # ssh-keygen can give us public key fingerprint, key type and size from private key

        import subprocess
        sshKeyGenBinary = "/usr/bin/ssh-keygen"
        proc = subprocess.Popen([sshKeyGenBinary,"-yl","-f",massiveLauncherPrivateKeyPath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        stdout,stderr = proc.communicate()
        sshKeyGenOutComponents = stdout.split(" ")
        if len(sshKeyGenOutComponents)>1:
            publicKeyFingerprint = sshKeyGenOutComponents[1]
        else:
            publicKeyFingerprint = ""
        if len(sshKeyGenOutComponents)>3:
            keyType = sshKeyGenOutComponents[-1].strip().strip("(").strip(")")
        else:
            keyType = ""

        # Public key fingerprint

        self.publicKeyFingerprintLabel = wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, "Public key fingerprint:")
        self.innerKeyPropertiesPanelSizer.Add(self.publicKeyFingerprintLabel)

        self.publicKeyFingerprintField = wx.TextCtrl(self.innerKeyPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)
        self.publicKeyFingerprintField.SetValue(publicKeyFingerprint)

        self.innerKeyPropertiesPanelSizer.Add(self.publicKeyFingerprintField, flag=wx.EXPAND)

        # Blank space

        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))
        self.innerKeyPropertiesPanelSizer.Add(wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, ""))

        # Key type

        self.keyTypeLabel = wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, "Key type:")
        self.innerKeyPropertiesPanelSizer.Add(self.keyTypeLabel)

        #self.keyTypeField = wx.TextCtrl(self.innerKeyPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)
        #self.keyTypeField.SetValue(keyType)
        self.keyTypeField = wx.StaticText(self.innerKeyPropertiesPanel, wx.ID_ANY, keyType)

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
        self.innerAgentPropertiesPanel.SetSizer(self.innerAgentPropertiesPanelSizer)

        self.innerAgentPropertiesPanelSizer.AddGrowableCol(1)

        self.sshAuthSockLabel = wx.StaticText(self.innerAgentPropertiesPanel, wx.ID_ANY, "SSH_AUTH_SOCK:")
        self.innerAgentPropertiesPanelSizer.Add(self.sshAuthSockLabel)

        self.sshAuthSockField = wx.TextCtrl(self.innerAgentPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)
        self.sshAuthSockField.SetValue(os.environ["SSH_AUTH_SOCK"])

        self.innerAgentPropertiesPanelSizer.Add(self.sshAuthSockField, flag=wx.EXPAND)

        #self.innerAgentPropertiesPanelSizer.Add(wx.StaticText(self.innerAgentPropertiesPanel, wx.ID_ANY, sshAuthSockQueryResult))
        #sshAgentQueryResult = "ssh agent query result"

        sshAddBinary = "/usr/bin/ssh-add"
        proc = subprocess.Popen([sshAddBinary,"-l","|","grep","Launcher"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        stdout,stderr = proc.communicate()
        sshAddOutComponents = stdout.split(" ")
        if len(sshAddOutComponents)>1:
            publicKeyFingerprintInAgent = sshAddOutComponents[1]
        else:
            publicKeyFingerprintInAgent = ""

        # Blank space

        self.innerAgentPropertiesPanelSizer.Add(wx.StaticText(self.innerAgentPropertiesPanel, wx.ID_ANY, ""))
        self.innerAgentPropertiesPanelSizer.Add(wx.StaticText(self.innerAgentPropertiesPanel, wx.ID_ANY, ""))

        # ssh-add -l | grep Launcher

        self.sshAgentQueryLabel = wx.StaticText(self.innerAgentPropertiesPanel, wx.ID_ANY, "Launcher key fingerprint in agent:")
        self.innerAgentPropertiesPanelSizer.Add(self.sshAgentQueryLabel)

        self.sshAgentQueryResultField = wx.TextCtrl(self.innerAgentPropertiesPanel, wx.ID_ANY, style=wx.TE_READONLY)
        self.sshAgentQueryResultField.SetValue(publicKeyFingerprintInAgent)

        self.innerAgentPropertiesPanelSizer.Add(self.sshAgentQueryResultField, flag=wx.EXPAND)

        self.innerAgentPropertiesPanel.Fit()
        self.agentPropertiesGroupBoxSizer.Add(self.innerAgentPropertiesPanel, flag=wx.EXPAND)
        self.agentPropertiesPanel.Fit()

        self.inspectKeyDialogCenterPanelSizer.Add(self.agentPropertiesPanel, flag=wx.EXPAND)

        # Blank space

        self.inspectKeyDialogCenterPanelSizer.Add(wx.StaticText(self.inspectKeyDialogCenterPanel, wx.ID_ANY, ""))

        # Buttons panel

        self.buttonsPanel = wx.Panel(self.inspectKeyDialogCenterPanel, wx.ID_ANY)
        self.buttonsPanelSizer = wx.FlexGridSizer(1,5, hgap=5, vgap=5)
        self.buttonsPanel.SetSizer(self.buttonsPanelSizer)

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

    def onChangePassphrase(self,event):
        dlg = wx.MessageDialog(None, 
                        "Not implemented yet.\n\n" +
                        "The Change Passphrase Dialog can be used to change your passphrase.\n\n" +
                        "You will need to enter your existing passphrase, and then\n" + 
                        "you will need to enter your new passphrase twice.\n\n"+
                        "You will still be able to access servers without a password\n" +
                        "if you have connected to them previously with the Launcher.",
                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()

    def onResetPassphrase(self, event):
        dlg = wx.MessageDialog(None, 
                        "Not implemented yet.\n\n" +
                        "The Reset Passphrase Dialog can be used if you forget your passphrase.\n\n" +
                        "A new key will be generated, replacing the existing key, and\n" +
                        "all servers you had access to without a password, will again\n" +
                        "require a password on the first login after resetting your\n" +
                        "passphrase.",
                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()

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
        self.EndModal(wx.ID_OK)

class MyApp(wx.App):
    def OnInit(self):

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
                             "server, e.g. MASSIVE.",
                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            return False


        inspectKeyDialog = InspectKeyDialog(None, wx.ID_ANY, 'MASSIVE/CVL Launcher Key Properties', massiveLauncherPrivateKeyPath)
        inspectKeyDialog.Center()
        inspectKeyDialog.ShowModal()
        return True

app = MyApp(0)
app.MainLoop()
