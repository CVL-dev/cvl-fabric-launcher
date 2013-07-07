#!/usr/bin/python

import wx
import wx.html
import os
import sys

from KeyModel import KeyModel

global helpController
helpController = None

class CreateNewKeyDialog(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title, wx.DefaultPosition)
        self.createNewKeyDialogPanel = wx.Panel(self, wx.ID_ANY)

        # I really miss Java Swing's BorderLayout and
        # BorderFactory.createEmptyBorder(...) sometimes.
        # All of this border stuff should be encapsulated in a class.

        self.createNewKeyDialogPanelSizer = wx.FlexGridSizer(1,3, hgap=15, vgap=15)
        self.createNewKeyDialogPanel.SetSizer(self.createNewKeyDialogPanelSizer)

        self.createNewKeyDialogLeftPanel = wx.Panel(self.createNewKeyDialogPanel, wx.ID_ANY)
        self.createNewKeyDialogPanelSizer.Add(self.createNewKeyDialogLeftPanel)
        self.createNewKeyDialogMiddlePanel = wx.Panel(self.createNewKeyDialogPanel, wx.ID_ANY)
        self.createNewKeyDialogPanelSizer.Add(self.createNewKeyDialogMiddlePanel, flag=wx.EXPAND)
        self.createNewKeyDialogRightPanel = wx.Panel(self.createNewKeyDialogPanel, wx.ID_ANY)
        self.createNewKeyDialogPanelSizer.Add(self.createNewKeyDialogRightPanel)

        self.createNewKeyDialogMiddlePanelSizer = wx.FlexGridSizer(3,1, hgap=15, vgap=15)
        self.createNewKeyDialogMiddlePanel.SetSizer(self.createNewKeyDialogMiddlePanelSizer)

        self.createNewKeyDialogTopPanel = wx.Panel(self.createNewKeyDialogMiddlePanel, wx.ID_ANY)
        self.createNewKeyDialogMiddlePanelSizer.Add(self.createNewKeyDialogTopPanel)
        self.createNewKeyDialogCenterPanel = wx.Panel(self.createNewKeyDialogMiddlePanel, wx.ID_ANY)
        self.createNewKeyDialogMiddlePanelSizer.Add(self.createNewKeyDialogCenterPanel, flag=wx.EXPAND)
        self.createNewKeyDialogBottomPanel = wx.Panel(self.createNewKeyDialogMiddlePanel, wx.ID_ANY)
        self.createNewKeyDialogMiddlePanelSizer.Add(self.createNewKeyDialogBottomPanel)

        self.createNewKeyDialogCenterPanelSizer = wx.FlexGridSizer(8,1)
        self.createNewKeyDialogCenterPanel.SetSizer(self.createNewKeyDialogCenterPanelSizer)

        self.instructionsLabel1 = wx.StaticText(self.createNewKeyDialogCenterPanel, wx.ID_ANY, 
            "The Launcher needs to create a private key to authenticate against remote servers such as MASSIVE.\n" + 
            "If in doubt, you can use the default values provided for the fields below.")
        self.createNewKeyDialogCenterPanelSizer.Add(self.instructionsLabel1, flag=wx.EXPAND|wx.BOTTOM, border=15)

        # Radio buttons panel

        self.radioButtonsPanel = wx.Panel(self.createNewKeyDialogCenterPanel, wx.ID_ANY)

        self.radioButtonsGroupBox = wx.StaticBox(self.radioButtonsPanel, wx.ID_ANY, label="Private key lifetime and passphrase")
        self.radioButtonsGroupBoxSizer = wx.StaticBoxSizer(self.radioButtonsGroupBox, wx.VERTICAL)
        self.radioButtonsPanel.SetSizer(self.radioButtonsGroupBoxSizer)

        self.innerRadioButtonsPanel = wx.Panel(self.radioButtonsPanel, wx.ID_ANY)
        self.innerRadioButtonsPanelSizer = wx.FlexGridSizer(4,1)
        self.innerRadioButtonsPanel.SetSizer(self.innerRadioButtonsPanelSizer)

        self.ID_SAVE_KEY_WITH_PASSPHRASE = wx.NewId()
        self.savePrivateKeyAndSecureWithPassphraseRadioButton = wx.RadioButton(self.innerRadioButtonsPanel, 
            self.ID_SAVE_KEY_WITH_PASSPHRASE,
            "Save the private key for use in future Launcher sessions and secure the key with a passphrase (recommended).", 
            style=wx.RB_GROUP)
        self.savePrivateKeyAndSecureWithPassphraseRadioButton.SetValue(True)
        self.innerRadioButtonsPanelSizer.Add(self.savePrivateKeyAndSecureWithPassphraseRadioButton, flag=wx.EXPAND)

        self.ID_SAVE_KEY_WITH_BLANK_PASSPHRASE = wx.NewId()
        self.savePrivateKeyWithBlankPassphraseRadioButton = wx.RadioButton(self.innerRadioButtonsPanel, 
            self.ID_SAVE_KEY_WITH_BLANK_PASSPHRASE,
            "Save the private key for use in future Launcher sessions, using a blank passphrase (less secure).")
        self.innerRadioButtonsPanelSizer.Add(self.savePrivateKeyWithBlankPassphraseRadioButton, flag=wx.EXPAND)

        self.DISCARD_KEY_UPON_EXIT = wx.NewId()
        self.discardPrivateKeyUponExitRadioButton = wx.RadioButton(self.innerRadioButtonsPanel, 
            self.DISCARD_KEY_UPON_EXIT,
            "Discard the private key when the Launcher exits. (A random passphrase will be generated for this session.)")
        self.innerRadioButtonsPanelSizer.Add(self.discardPrivateKeyUponExitRadioButton, flag=wx.EXPAND)

        self.Bind(wx.EVT_RADIOBUTTON, self.onRadioButtonSelectionChanged, id=self.savePrivateKeyAndSecureWithPassphraseRadioButton.GetId())
        self.Bind(wx.EVT_RADIOBUTTON, self.onRadioButtonSelectionChanged, id=self.savePrivateKeyWithBlankPassphraseRadioButton.GetId())
        self.Bind(wx.EVT_RADIOBUTTON, self.onRadioButtonSelectionChanged, id=self.discardPrivateKeyUponExitRadioButton.GetId())

        self.instructionsLabel2 = wx.StaticText(self.innerRadioButtonsPanel, wx.ID_ANY, "If using a shared computer or a \"Guest\" account, you should choose the third option.")
        self.innerRadioButtonsPanelSizer.Add(self.instructionsLabel2, flag=wx.EXPAND|wx.TOP, border=10)

        self.innerRadioButtonsPanel.Fit()
        self.radioButtonsGroupBoxSizer.Add(self.innerRadioButtonsPanel, flag=wx.EXPAND)
        self.radioButtonsPanel.Fit()

        self.createNewKeyDialogCenterPanelSizer.Add(self.radioButtonsPanel, flag=wx.EXPAND|wx.BOTTOM, border=15)

        # Passphrase panel

        self.validPassphrase = False

        self.passphrasePanel = wx.Panel(self.createNewKeyDialogCenterPanel, wx.ID_ANY)

        self.passphraseGroupBox = wx.StaticBox(self.passphrasePanel, wx.ID_ANY, label="Enter a passphrase to protect your private key")
        self.passphraseGroupBoxSizer = wx.StaticBoxSizer(self.passphraseGroupBox, wx.VERTICAL)
        self.passphrasePanel.SetSizer(self.passphraseGroupBoxSizer)

        self.innerPassphrasePanel = wx.Panel(self.passphrasePanel, wx.ID_ANY)
        self.innerPassphrasePanelSizer = wx.FlexGridSizer(2,3, hgap=10)
        self.innerPassphrasePanel.SetSizer(self.innerPassphrasePanelSizer)

        self.passphraseLabel = wx.StaticText(self.innerPassphrasePanel, wx.ID_ANY, "Passphrase:")
        self.innerPassphrasePanelSizer.Add(self.passphraseLabel, flag=wx.EXPAND)

        self.passphraseField = wx.TextCtrl(self.innerPassphrasePanel, wx.ID_ANY,style=wx.TE_PASSWORD)
        self.innerPassphrasePanelSizer.Add(self.passphraseField, flag=wx.EXPAND)
        self.passphraseField.SetFocus()

        self.passphraseStatusLabel1 = wx.StaticText(self.innerPassphrasePanel, wx.ID_ANY, "")
        self.innerPassphrasePanelSizer.Add(self.passphraseStatusLabel1, flag=wx.EXPAND|wx.LEFT, border=50)

        self.repeatPassphraseLabel = wx.StaticText(self.innerPassphrasePanel, wx.ID_ANY, "Repeat passphrase:")
        self.innerPassphrasePanelSizer.Add(self.repeatPassphraseLabel, flag=wx.EXPAND)

        self.repeatPassphraseField = wx.TextCtrl(self.innerPassphrasePanel, wx.ID_ANY,style=wx.TE_PASSWORD)
        self.innerPassphrasePanelSizer.Add(self.repeatPassphraseField, flag=wx.EXPAND)

        self.passphraseStatusLabel2 = wx.StaticText(self.innerPassphrasePanel, wx.ID_ANY, "")
        self.innerPassphrasePanelSizer.Add(self.passphraseStatusLabel2, flag=wx.EXPAND|wx.LEFT, border=50)

        self.innerPassphrasePanel.Fit()
        self.passphraseGroupBoxSizer.Add(self.innerPassphrasePanel, flag=wx.EXPAND)
        self.passphrasePanel.Fit()

        self.Bind(wx.EVT_TEXT, self.onPassphraseFieldsModified, id=self.passphraseField.GetId())
        self.Bind(wx.EVT_TEXT, self.onPassphraseFieldsModified, id=self.repeatPassphraseField.GetId())

        self.createNewKeyDialogCenterPanelSizer.Add(self.passphrasePanel, flag=wx.EXPAND|wx.BOTTOM, border=15)

        # Private key location

        self.privateKeyLocationPanel = wx.Panel(self.createNewKeyDialogCenterPanel, wx.ID_ANY)

        self.privateKeyLocationGroupBox = wx.StaticBox(self.privateKeyLocationPanel, wx.ID_ANY, label="Choose a location for your private key")
        self.privateKeyLocationGroupBoxSizer = wx.StaticBoxSizer(self.privateKeyLocationGroupBox, wx.VERTICAL)
        self.privateKeyLocationPanel.SetSizer(self.privateKeyLocationGroupBoxSizer)

        self.innerPrivateKeyLocationPanel = wx.Panel(self.privateKeyLocationPanel, wx.ID_ANY)
        self.innerPrivateKeyLocationPanelSizer = wx.FlexGridSizer(1,3, hgap=10)
        self.innerPrivateKeyLocationPanelSizer.AddGrowableCol(1)
        self.innerPrivateKeyLocationPanel.SetSizer(self.innerPrivateKeyLocationPanelSizer)

        self.privateKeyLocationLabel = wx.StaticText(self.innerPrivateKeyLocationPanel, wx.ID_ANY, "Private key file:")
        self.innerPrivateKeyLocationPanelSizer.Add(self.privateKeyLocationLabel)

        self.privateKeyLocationField = wx.TextCtrl(self.innerPrivateKeyLocationPanel, wx.ID_ANY, style=wx.TE_READONLY)
        defaultPrivateKeyLocation = os.path.join(os.path.expanduser('~'), '.ssh', "MassiveLauncherKey")
        self.privateKeyDir = os.path.join(os.path.expanduser('~'), '.ssh')
        self.privateKeyFilename = "MassiveLauncherKey"
        self.privateKeyLocationField.SetValue(defaultPrivateKeyLocation)

        self.innerPrivateKeyLocationPanelSizer.Add(self.privateKeyLocationField, flag=wx.EXPAND)

        self.browseButton = wx.Button(self.innerPrivateKeyLocationPanel, wx.NewId(), "Browse")
        self.Bind(wx.EVT_BUTTON, self.onBrowse, id=self.browseButton.GetId())
        self.innerPrivateKeyLocationPanelSizer.Add(self.browseButton, flag=wx.BOTTOM, border=5)

        self.innerPrivateKeyLocationPanel.Fit()
        self.privateKeyLocationGroupBoxSizer.Add(self.innerPrivateKeyLocationPanel, flag=wx.EXPAND)
        self.privateKeyLocationPanel.Fit()

        self.createNewKeyDialogCenterPanelSizer.Add(self.privateKeyLocationPanel, flag=wx.EXPAND)

        # Keep SSH Agent running checkbox.

        self.leaveKeyInAgentAfterExitCheckBox = wx.CheckBox(self.createNewKeyDialogCenterPanel, wx.ID_ANY, 
            "Allow my SSH Agent to continue managing my key after the Launcher exits, so I don't need to enter my passphrase next time.")
        self.leaveKeyInAgentAfterExitCheckBox.SetValue(True)
        self.createNewKeyDialogCenterPanelSizer.Add(self.leaveKeyInAgentAfterExitCheckBox, flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=15)

        # Blank space

        #self.createNewKeyDialogCenterPanelSizer.Add(wx.StaticText(self.createNewKeyDialogCenterPanel, wx.ID_ANY, ""))

        # Buttons panel

        self.buttonsPanel = wx.Panel(self.createNewKeyDialogCenterPanel, wx.ID_ANY)
        self.buttonsPanelSizer = wx.FlexGridSizer(1,3, hgap=5, vgap=5)
        self.buttonsPanel.SetSizer(self.buttonsPanelSizer)
        self.helpButton = wx.Button(self.buttonsPanel, wx.NewId(), "Help")
        self.buttonsPanelSizer.Add(self.helpButton, flag=wx.BOTTOM, border=5)
        self.Bind(wx.EVT_BUTTON, self.onHelp, id=self.helpButton.GetId())
        self.cancelButton = wx.Button(self.buttonsPanel, wx.ID_CANCEL, "Cancel")
        self.buttonsPanelSizer.Add(self.cancelButton, flag=wx.BOTTOM, border=5)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=wx.ID_CANCEL)
        self.okButton = wx.Button(self.buttonsPanel, wx.ID_OK, "OK")
        self.okButton.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
        self.buttonsPanelSizer.Add(self.okButton, flag=wx.BOTTOM, border=5)
        self.buttonsPanel.Fit()

        self.createNewKeyDialogCenterPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT)

        # Calculate positions on dialog, using sizers

        self.createNewKeyDialogCenterPanel.Fit()
        self.createNewKeyDialogMiddlePanel.Fit()
        self.createNewKeyDialogPanel.Fit()
        self.Fit()
        self.CenterOnParent()

    def onRadioButtonSelectionChanged(self, event):
        if self.savePrivateKeyAndSecureWithPassphraseRadioButton.GetValue()==True:

            self.passphrasePanel.Show(True)
            self.privateKeyLocationPanel.Show(True)
            self.leaveKeyInAgentAfterExitCheckBox.SetValue(True)
            self.leaveKeyInAgentAfterExitCheckBox.Show(True)

            self.createNewKeyDialogCenterPanel.Fit()
            self.createNewKeyDialogMiddlePanel.Fit()
            self.createNewKeyDialogPanel.Fit()
            self.Fit()

        else:
            self.passphrasePanel.Show(False)

            if self.discardPrivateKeyUponExitRadioButton.GetValue()==True:
                self.privateKeyLocationPanel.Show(False)
                self.leaveKeyInAgentAfterExitCheckBox.SetValue(False)
                self.leaveKeyInAgentAfterExitCheckBox.Show(False)
            else:
                self.privateKeyLocationPanel.Show(True)
                self.leaveKeyInAgentAfterExitCheckBox.SetValue(True)
                self.leaveKeyInAgentAfterExitCheckBox.Show(True)

            self.createNewKeyDialogCenterPanel.Fit()
            self.createNewKeyDialogMiddlePanel.Fit()
            self.createNewKeyDialogPanel.Fit()
            self.Fit()

            self.passphraseField.SetValue("")
            self.repeatPassphraseField.SetValue("")
            self.passphraseStatusLabel1.SetLabel("")
            self.passphraseStatusLabel2.SetLabel("")

    def onPassphraseFieldsModified(self, event):
        self.validPassphrase = False
        if len(self.passphraseField.GetValue())>0 and len(self.passphraseField.GetValue())<6:
            self.passphraseStatusLabel1.SetLabel("Passphrase is too short.  :-(")
            self.passphraseStatusLabel2.SetLabel("")
        elif self.passphraseField.GetValue()!=self.repeatPassphraseField.GetValue():
            if self.repeatPassphraseField.GetValue()=="":
                self.passphraseStatusLabel1.SetLabel("")
                self.passphraseStatusLabel2.SetLabel("Please enter your passphrase again.")
            else:
                self.passphraseStatusLabel1.SetLabel("")
                self.passphraseStatusLabel2.SetLabel("Passphrases don't match! :-(")
        else:
            self.passphraseStatusLabel1.SetLabel("")
            self.passphraseStatusLabel2.SetLabel("Passphrases match! :-)")
            self.validPassphrase = True

    def onOK(self, event):
        privateKeyLifetimeAndPassphraseChoice = self.getPrivateKeyLifetimeAndPassphraseChoice()
        if privateKeyLifetimeAndPassphraseChoice==self.ID_SAVE_KEY_WITH_PASSPHRASE:
            # If we're using a passphrase, make sure it is valid.
            if self.passphraseField.GetValue().strip()=="" or not self.validPassphrase:
                if self.passphraseField.GetValue().strip()=="":
                    message = "Please enter a passphrase."
                    self.passphraseField.SetFocus()
                elif self.passphraseStatusLabel1.GetLabelText()!="":
                    message = self.passphraseStatusLabel1.GetLabelText()
                    self.passphraseField.SetFocus()
                elif self.passphraseStatusLabel2.GetLabelText()!="" and self.passphraseStatusLabel2.GetLabelText()!="Passphrases match! :-)":
                    message = self.passphraseStatusLabel2.GetLabelText()
                    self.repeatPassphraseField.SetFocus()
                else:
                    message = "Please enter a valid passphrase."
                    self.passphraseField.SetFocus()

                dlg = wx.MessageDialog(self, message,
                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                return

        if self.getPrivateKeyLifetimeAndPassphraseChoice()==self.ID_SAVE_KEY_WITH_PASSPHRASE:
            keyModelObject = KeyModel(self.getPrivateKeyFileLocation())
            keyComment = os.path.basename(self.getPrivateKeyFileLocation())
            def keyCreatedSuccessfullyCallback():
                print "CreateNewKeyDialog callback: Key created successfully! :-)"
            def keyFileAlreadyExistsCallback():
                print "CreateNewKeyDialog callback: Key file already exists! :-("
            def passphraseTooShortCallback():
                print "CreateNewKeyDialog callback: Passphrase was too short! :-("
            success = keyModelObject.generateNewKey(self.getPassphrase(),keyComment,keyCreatedSuccessfullyCallback,keyFileAlreadyExistsCallback,passphraseTooShortCallback)
            if success:
                message = "Your Launcher key was created successfully! :-)"
            else:
                message = "An error occured while attempting to create your key. :-("
            dlg = wx.MessageDialog(None,
                message,
                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()

        if success:
            self.Show(False)
            self.EndModal(wx.ID_OK)

    def onCancel(self, event):
        self.Show(False)
        self.EndModal(wx.ID_CANCEL)

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

    def onBrowse(self, event):
        saveFileDialog = wx.FileDialog (self, message = 'MASSIVE Launcher private key file...', defaultDir=self.privateKeyDir, defaultFile=self.privateKeyFilename, style = wx.SAVE)
        if saveFileDialog.ShowModal() == wx.ID_OK:
            privateKeyFilePath = saveFileDialog.GetPath()
            (self.privateKeyDir, self.privateKeyFilename) = os.path.split(privateKeyFilePath)
            self.privateKeyLocationField.SetValue(privateKeyFilePath)

    def getPassphrase(self):
        return self.passphraseField.GetValue()

    def getWhetherToLeaveKeyInAgentAfterExit(self):
        return self.leaveKeyInAgentAfterExitCheckBox.GetValue()

    def getPrivateKeyLifetimeAndPassphraseChoice(self):
        privateKeyLifetimeAndPassphraseChoice = -1 
        if self.savePrivateKeyAndSecureWithPassphraseRadioButton.GetValue()==True:
            privateKeyLifetimeAndPassphraseChoice = self.savePrivateKeyAndSecureWithPassphraseRadioButton.GetId()
        elif self.savePrivateKeyWithBlankPassphraseRadioButton.GetValue()==True:
            privateKeyLifetimeAndPassphraseChoice = self.savePrivateKeyWithBlankPassphraseRadioButton.GetId()
        elif self.discardPrivateKeyUponExitRadioButton.GetValue()==True:
            privateKeyLifetimeAndPassphraseChoice = self.discardPrivateKeyUponExitRadioButton.GetId()

        return privateKeyLifetimeAndPassphraseChoice

    def getPrivateKeyFileLocation(self):
        return self.privateKeyLocationField.GetValue()

class MyApp(wx.App):
    def OnInit(self):
        createNewKeyDialog = CreateNewKeyDialog(None, wx.ID_ANY, 'MASSIVE/CVL Launcher Private Key')
        createNewKeyDialog.Center()
        if createNewKeyDialog.ShowModal()==wx.ID_OK:
            if createNewKeyDialog.getPrivateKeyLifetimeAndPassphraseChoice()==createNewKeyDialog.ID_SAVE_KEY_WITH_PASSPHRASE:
                print "Passphrase = " + createNewKeyDialog.getPassphrase()
        else:
            print "User canceled."
            return False

        import appdirs
        import ConfigParser
        appDirs = appdirs.AppDirs("MASSIVE Launcher", "Monash University")
        appUserDataDir = appDirs.user_data_dir
        # Add trailing slash:
        appUserDataDir = os.path.join(appUserDataDir,"")
        if not os.path.exists(appUserDataDir):
            os.makedirs(appUserDataDir)

        massiveLauncherConfig = ConfigParser.RawConfigParser(allow_no_value=True)

        massiveLauncherPreferencesFilePath = os.path.join(appUserDataDir,"MASSIVE Launcher Preferences.cfg")
        if os.path.exists(massiveLauncherPreferencesFilePath):
            massiveLauncherConfig.read(massiveLauncherPreferencesFilePath)
        if not massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")

        # Write fields to local settings

        massiveLauncherConfig.set("MASSIVE Launcher Preferences", "private_key_lifetime_and_passphrase_choice", createNewKeyDialog.getPrivateKeyLifetimeAndPassphraseChoice())
        massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_launcher_private_key_path", createNewKeyDialog.getPrivateKeyFileLocation())
        massiveLauncherConfig.set("MASSIVE Launcher Preferences", "leave_key_in_agent_after_exit", createNewKeyDialog.getWhetherToLeaveKeyInAgentAfterExit())
        with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
            massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        # Read fields from local settings

        privateKeyLifetimeAndPassphraseChoice = createNewKeyDialog.ID_SAVE_KEY_WITH_PASSPHRASE
        if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "private_key_lifetime_and_passphrase_choice"):
            privateKeyLifetimeAndPassphraseChoice = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "private_key_lifetime_and_passphrase_choice")
        else:
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "private_key_lifetime_and_passphrase_choice", createNewKeyDialog.ID_SAVE_KEY_WITH_PASSPHRASE)
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        if privateKeyLifetimeAndPassphraseChoice==createNewKeyDialog.ID_SAVE_KEY_WITH_PASSPHRASE:
            print "From local settings: createNewKeyDialog.ID_SAVE_KEY_WITH_PASSPHRASE" 
        elif privateKeyLifetimeAndPassphraseChoice==createNewKeyDialog.ID_SAVE_KEY_WITH_BLANK_PASSPHRASE:
            print "From local settings: createNewKeyDialog.ID_SAVE_KEY_WITH_BLANK_PASSPHRASE" 
        elif privateKeyLifetimeAndPassphraseChoice==createNewKeyDialog.DISCARD_KEY_UPON_EXIT:
            print "From local settings: createNewKeyDialog.DISCARD_KEY_UPON_EXIT"

        massiveLauncherPrivateKeyPath = os.path.join(os.path.expanduser('~'), '.ssh', "MassiveLauncherKey")
        if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "massive_launcher_private_key_path"):
            massiveLauncherPrivateKeyPath = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "massive_launcher_private_key_path")
        else:
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_launcher_private_key_path", 
                os.path.join(os.path.expanduser('~'), '.ssh', "MassiveLauncherKey"))
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        print "From local settings: massiveLauncherPrivateKeyPath = " + massiveLauncherPrivateKeyPath

        leaveKeyInAgentAfterExit = True
        if massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "leave_key_in_agent_after_exit"):
            leaveKeyInAgentAfterExit = massiveLauncherConfig.get("MASSIVE Launcher Preferences", "leave_key_in_agent_after_exit")
        else:
            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "leave_key_in_agent_after_exit", True)
            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        print "From local settings: Leave key in agent after exit = " + str(leaveKeyInAgentAfterExit)

        return True

#app = MyApp(0)
#app.MainLoop()
