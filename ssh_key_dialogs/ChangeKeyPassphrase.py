#!/usr/bin/python

import wx
import wx.html
import os

global helpController
helpController = None

class ChangeKeyPassphraseDialog(wx.Dialog):
    def __init__(self, parent, id, title, privateKeyFilePath):
        wx.Dialog.__init__(self, parent, id, title, wx.DefaultPosition)
        self.changeKeyPassphraseDialogPanel = wx.Panel(self, wx.ID_ANY)

        self.privateKeyFilePath = privateKeyFilePath

        self.changeKeyPassphraseDialogPanelSizer = wx.FlexGridSizer(1,3, hgap=15, vgap=15)
        self.changeKeyPassphraseDialogPanel.SetSizer(self.changeKeyPassphraseDialogPanelSizer)

        self.changeKeyPassphraseDialogLeftPanel = wx.Panel(self.changeKeyPassphraseDialogPanel, wx.ID_ANY)
        self.changeKeyPassphraseDialogPanelSizer.Add(self.changeKeyPassphraseDialogLeftPanel)
        self.changeKeyPassphraseDialogMiddlePanel = wx.Panel(self.changeKeyPassphraseDialogPanel, wx.ID_ANY)
        self.changeKeyPassphraseDialogPanelSizer.Add(self.changeKeyPassphraseDialogMiddlePanel, flag=wx.EXPAND)
        self.changeKeyPassphraseDialogRightPanel = wx.Panel(self.changeKeyPassphraseDialogPanel, wx.ID_ANY)
        self.changeKeyPassphraseDialogPanelSizer.Add(self.changeKeyPassphraseDialogRightPanel)

        self.changeKeyPassphraseDialogMiddlePanelSizer = wx.FlexGridSizer(3,1, hgap=15, vgap=15)
        self.changeKeyPassphraseDialogMiddlePanel.SetSizer(self.changeKeyPassphraseDialogMiddlePanelSizer)

        self.changeKeyPassphraseDialogTopPanel = wx.Panel(self.changeKeyPassphraseDialogMiddlePanel, wx.ID_ANY)
        self.changeKeyPassphraseDialogMiddlePanelSizer.Add(self.changeKeyPassphraseDialogTopPanel)
        self.changeKeyPassphraseDialogCenterPanel = wx.Panel(self.changeKeyPassphraseDialogMiddlePanel, wx.ID_ANY)
        self.changeKeyPassphraseDialogMiddlePanelSizer.Add(self.changeKeyPassphraseDialogCenterPanel, flag=wx.EXPAND)
        self.changeKeyPassphraseDialogBottomPanel = wx.Panel(self.changeKeyPassphraseDialogMiddlePanel, wx.ID_ANY)
        self.changeKeyPassphraseDialogMiddlePanelSizer.Add(self.changeKeyPassphraseDialogBottomPanel)

        self.changeKeyPassphraseDialogCenterPanelSizer = wx.FlexGridSizer(8,1)
        self.changeKeyPassphraseDialogCenterPanel.SetSizer(self.changeKeyPassphraseDialogCenterPanelSizer)

        self.instructionsLabel = wx.StaticText(self.changeKeyPassphraseDialogCenterPanel, wx.ID_ANY, 
                        "To change your passphrase, you will first need to enter your existing passphrase,\n" +
                        "then you will need to enter your new passphrase twice.\n\n"+
                        "You will still be able to access servers without a password if you have connected\n" +
                        "to them previously with the Launcher.")
        self.changeKeyPassphraseDialogCenterPanelSizer.Add(self.instructionsLabel, flag=wx.EXPAND|wx.BOTTOM, border=15)

        # Existing passphrase panel

        self.existingPassphrasePanel = wx.Panel(self.changeKeyPassphraseDialogCenterPanel, wx.ID_ANY)

        self.existingPassphraseGroupBox = wx.StaticBox(self.existingPassphrasePanel, wx.ID_ANY, label="Enter your existing passphrase")
        self.existingPassphraseGroupBoxSizer = wx.StaticBoxSizer(self.existingPassphraseGroupBox, wx.VERTICAL)
        self.existingPassphrasePanel.SetSizer(self.existingPassphraseGroupBoxSizer)

        self.innerExistingPassphrasePanel = wx.Panel(self.existingPassphrasePanel, wx.ID_ANY)
        self.innerExistingPassphrasePanelSizer = wx.FlexGridSizer(2,3, hgap=10)
        self.innerExistingPassphrasePanel.SetSizer(self.innerExistingPassphrasePanelSizer)

        self.passphraseLabel = wx.StaticText(self.innerExistingPassphrasePanel, wx.ID_ANY, "Existing passphrase:")
        self.innerExistingPassphrasePanelSizer.Add(self.passphraseLabel, flag=wx.EXPAND)

        self.existingPassphraseField = wx.TextCtrl(self.innerExistingPassphrasePanel, wx.ID_ANY,style=wx.TE_PASSWORD)
        self.innerExistingPassphrasePanelSizer.Add(self.existingPassphraseField, flag=wx.EXPAND)
        self.existingPassphraseField.SetFocus()

        self.innerExistingPassphrasePanel.Fit()
        self.existingPassphraseGroupBoxSizer.Add(self.innerExistingPassphrasePanel, flag=wx.EXPAND)
        self.existingPassphrasePanel.Fit()

        self.changeKeyPassphraseDialogCenterPanelSizer.Add(self.existingPassphrasePanel, flag=wx.EXPAND)

        # Blank space

        self.changeKeyPassphraseDialogCenterPanelSizer.Add(wx.StaticText(self.changeKeyPassphraseDialogCenterPanel, wx.ID_ANY, ""))

        # New passphrase panel

        self.validNewPassphrase = False

        self.newPassphrasePanel = wx.Panel(self.changeKeyPassphraseDialogCenterPanel, wx.ID_ANY)

        self.newPassphraseGroupBox = wx.StaticBox(self.newPassphrasePanel, wx.ID_ANY, label="Enter a new passphrase to protect your private key")
        self.newPassphraseGroupBoxSizer = wx.StaticBoxSizer(self.newPassphraseGroupBox, wx.VERTICAL)
        self.newPassphrasePanel.SetSizer(self.newPassphraseGroupBoxSizer)

        self.innerNewPassphrasePanel = wx.Panel(self.newPassphrasePanel, wx.ID_ANY)
        self.innerNewPassphrasePanelSizer = wx.FlexGridSizer(2,3, hgap=10)
        self.innerNewPassphrasePanel.SetSizer(self.innerNewPassphrasePanelSizer)

        self.passphraseLabel = wx.StaticText(self.innerNewPassphrasePanel, wx.ID_ANY, "New passphrase:")
        self.innerNewPassphrasePanelSizer.Add(self.passphraseLabel, flag=wx.EXPAND)

        self.newPassphraseField = wx.TextCtrl(self.innerNewPassphrasePanel, wx.ID_ANY,style=wx.TE_PASSWORD)
        self.innerNewPassphrasePanelSizer.Add(self.newPassphraseField, flag=wx.EXPAND)

        self.newPassphraseStatusLabel1 = wx.StaticText(self.innerNewPassphrasePanel, wx.ID_ANY, "")
        self.innerNewPassphrasePanelSizer.Add(self.newPassphraseStatusLabel1, flag=wx.EXPAND|wx.LEFT, border=20)

        self.repeatNewPassphraseLabel = wx.StaticText(self.innerNewPassphrasePanel, wx.ID_ANY, "Repeat passphrase:")
        self.innerNewPassphrasePanelSizer.Add(self.repeatNewPassphraseLabel, flag=wx.EXPAND)

        self.repeatNewPassphraseField = wx.TextCtrl(self.innerNewPassphrasePanel, wx.ID_ANY,style=wx.TE_PASSWORD)
        self.innerNewPassphrasePanelSizer.Add(self.repeatNewPassphraseField, flag=wx.EXPAND)

        self.newPassphraseStatusLabel2 = wx.StaticText(self.innerNewPassphrasePanel, wx.ID_ANY, "")
        self.innerNewPassphrasePanelSizer.Add(self.newPassphraseStatusLabel2, flag=wx.EXPAND|wx.LEFT, border=20)

        self.innerNewPassphrasePanel.Fit()
        self.newPassphraseGroupBoxSizer.Add(self.innerNewPassphrasePanel, flag=wx.EXPAND)
        self.newPassphrasePanel.Fit()

        self.Bind(wx.EVT_TEXT, self.onPassphraseFieldsModified, id=self.newPassphraseField.GetId())
        self.Bind(wx.EVT_TEXT, self.onPassphraseFieldsModified, id=self.repeatNewPassphraseField.GetId())

        self.changeKeyPassphraseDialogCenterPanelSizer.Add(self.newPassphrasePanel, flag=wx.EXPAND)

        # Blank space

        self.changeKeyPassphraseDialogCenterPanelSizer.Add(wx.StaticText(self.changeKeyPassphraseDialogCenterPanel, wx.ID_ANY, ""))

        # Buttons panel

        self.buttonsPanel = wx.Panel(self.changeKeyPassphraseDialogCenterPanel, wx.ID_ANY)
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

        self.changeKeyPassphraseDialogCenterPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT)

        # Calculate positions on dialog, using sizers

        self.changeKeyPassphraseDialogCenterPanel.Fit()
        self.changeKeyPassphraseDialogMiddlePanel.Fit()
        self.changeKeyPassphraseDialogPanel.Fit()
        self.Fit()
        self.CenterOnParent()

    def onPassphraseFieldsModified(self, event):
        self.validNewPassphrase = False
        if len(self.newPassphraseField.GetValue())>0 and len(self.newPassphraseField.GetValue())<6:
            self.newPassphraseStatusLabel1.SetLabel("Passphrase is too short.  :-(")
            self.newPassphraseStatusLabel2.SetLabel("")
        elif self.newPassphraseField.GetValue()!=self.repeatNewPassphraseField.GetValue():
            if self.repeatNewPassphraseField.GetValue()=="":
                self.newPassphraseStatusLabel1.SetLabel("")
                self.newPassphraseStatusLabel2.SetLabel("Enter your new passphrase again.")
            else:
                self.newPassphraseStatusLabel1.SetLabel("")
                self.newPassphraseStatusLabel2.SetLabel("Passphrases don't match! :-(")
        else:
            self.newPassphraseStatusLabel1.SetLabel("")
            self.newPassphraseStatusLabel2.SetLabel("Passphrases match! :-)")
            self.validNewPassphrase = True

    def onOK(self, event):

        if self.newPassphraseStatusLabel1.GetLabelText()!="":
            message = self.newPassphraseStatusLabel1.GetLabelText()
            dlg = wx.MessageDialog(self, message,
                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            self.newPassphraseField.SetFocus()
            return

        if self.newPassphraseStatusLabel2.GetLabelText()!="" and self.newPassphraseStatusLabel2.GetLabelText()!="Passphrases match! :-)":
            message = self.newPassphraseStatusLabel2.GetLabelText()
            dlg = wx.MessageDialog(self, message,
                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            self.repeatNewPassphraseField.SetFocus()
            return

        # On Linux or BSD/OSX we can use pexpect to talk to ssh-add.

        print "\nFIXME: Still need to do Windows implementation which doesn't use pexpect.\n"

        import pexpect

        args = ["-f", self.privateKeyFilePath, "-p"]
        sshKeyGenBinary = "/usr/bin/ssh-keygen"
        lp = pexpect.spawn(sshKeyGenBinary, args=args)

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

    def getNewPassphrase(self):
        return self.newPassphraseField.GetValue()

class MyApp(wx.App):
    def OnInit(self):
        changeKeyPassphraseDialog = ChangeKeyPassphraseDialog(None, wx.ID_ANY, 'Change Key Passphrase', os.path.join(os.path.expanduser('~'), '.ssh', "MassiveLauncherKey"))
        changeKeyPassphraseDialog.Center()
        if changeKeyPassphraseDialog.ShowModal()==wx.ID_OK:
            print "New passphrase = " + changeKeyPassphraseDialog.getNewPassphrase()
        else:
            print "User canceled."
            return False

        return True

#app = MyApp(0)
#app.MainLoop()
