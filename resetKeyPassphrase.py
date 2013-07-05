#!/usr/bin/python

import wx
import wx.html
import os
import sys

global helpController
helpController = None

class ResetKeyPassphraseDialog(wx.Dialog):
    def __init__(self, parent, id, title):
        wx.Dialog.__init__(self, parent, id, title, wx.DefaultPosition)
        self.resetKeyPassphraseDialogPanel = wx.Panel(self, wx.ID_ANY)

        self.resetKeyPassphraseDialogPanelSizer = wx.FlexGridSizer(1,3, hgap=15, vgap=15)
        self.resetKeyPassphraseDialogPanel.SetSizer(self.resetKeyPassphraseDialogPanelSizer)

        self.resetKeyPassphraseDialogLeftPanel = wx.Panel(self.resetKeyPassphraseDialogPanel, wx.ID_ANY)
        self.resetKeyPassphraseDialogPanelSizer.Add(self.resetKeyPassphraseDialogLeftPanel)
        self.resetKeyPassphraseDialogMiddlePanel = wx.Panel(self.resetKeyPassphraseDialogPanel, wx.ID_ANY)
        self.resetKeyPassphraseDialogPanelSizer.Add(self.resetKeyPassphraseDialogMiddlePanel, flag=wx.EXPAND)
        self.resetKeyPassphraseDialogRightPanel = wx.Panel(self.resetKeyPassphraseDialogPanel, wx.ID_ANY)
        self.resetKeyPassphraseDialogPanelSizer.Add(self.resetKeyPassphraseDialogRightPanel)

        self.resetKeyPassphraseDialogMiddlePanelSizer = wx.FlexGridSizer(3,1, hgap=15, vgap=15)
        self.resetKeyPassphraseDialogMiddlePanel.SetSizer(self.resetKeyPassphraseDialogMiddlePanelSizer)

        self.resetKeyPassphraseDialogTopPanel = wx.Panel(self.resetKeyPassphraseDialogMiddlePanel, wx.ID_ANY)
        self.resetKeyPassphraseDialogMiddlePanelSizer.Add(self.resetKeyPassphraseDialogTopPanel)
        self.resetKeyPassphraseDialogCenterPanel = wx.Panel(self.resetKeyPassphraseDialogMiddlePanel, wx.ID_ANY)
        self.resetKeyPassphraseDialogMiddlePanelSizer.Add(self.resetKeyPassphraseDialogCenterPanel, flag=wx.EXPAND)
        self.resetKeyPassphraseDialogBottomPanel = wx.Panel(self.resetKeyPassphraseDialogMiddlePanel, wx.ID_ANY)
        self.resetKeyPassphraseDialogMiddlePanelSizer.Add(self.resetKeyPassphraseDialogBottomPanel)

        self.resetKeyPassphraseDialogCenterPanelSizer = wx.FlexGridSizer(8,1)
        self.resetKeyPassphraseDialogCenterPanel.SetSizer(self.resetKeyPassphraseDialogCenterPanelSizer)

        self.instructionsLabel = wx.StaticText(self.resetKeyPassphraseDialogCenterPanel, wx.ID_ANY, 
                        "A new key can be generated, replacing the existing key, allowing you to enter a new passphrase.\n\n" +
                        "Any servers you had access to without a password, will again require a password on the first\n" +
                        "login after resetting your key's passphrase.")
        self.resetKeyPassphraseDialogCenterPanelSizer.Add(self.instructionsLabel, flag=wx.EXPAND|wx.BOTTOM, border=15)

        # Passphrase panel

        self.validPassphrase = False

        self.passphrasePanel = wx.Panel(self.resetKeyPassphraseDialogCenterPanel, wx.ID_ANY)

        self.passphraseGroupBox = wx.StaticBox(self.passphrasePanel, wx.ID_ANY, label="Enter a new passphrase to protect your private key")
        self.passphraseGroupBoxSizer = wx.StaticBoxSizer(self.passphraseGroupBox, wx.VERTICAL)
        self.passphrasePanel.SetSizer(self.passphraseGroupBoxSizer)

        self.innerPassphrasePanel = wx.Panel(self.passphrasePanel, wx.ID_ANY)
        self.innerPassphrasePanelSizer = wx.FlexGridSizer(2,3, hgap=10)
        self.innerPassphrasePanel.SetSizer(self.innerPassphrasePanelSizer)

        self.passphraseLabel = wx.StaticText(self.innerPassphrasePanel, wx.ID_ANY, "New passphrase:")
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

        self.resetKeyPassphraseDialogCenterPanelSizer.Add(self.passphrasePanel, flag=wx.EXPAND)

        # Blank space

        self.resetKeyPassphraseDialogCenterPanelSizer.Add(wx.StaticText(self.resetKeyPassphraseDialogCenterPanel, wx.ID_ANY, ""))

        # Buttons panel

        self.buttonsPanel = wx.Panel(self.resetKeyPassphraseDialogCenterPanel, wx.ID_ANY)
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

        self.resetKeyPassphraseDialogCenterPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT)

        # Calculate positions on dialog, using sizers

        self.resetKeyPassphraseDialogCenterPanel.Fit()
        self.resetKeyPassphraseDialogMiddlePanel.Fit()
        self.resetKeyPassphraseDialogPanel.Fit()
        self.Fit()
        self.CenterOnParent()

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

    def getPassphrase(self):
        return self.passphraseField.GetValue()

class MyApp(wx.App):
    def OnInit(self):
        resetKeyPassphraseDialog = ResetKeyPassphraseDialog(None, wx.ID_ANY, 'Reset Key Passphrase')
        resetKeyPassphraseDialog.Center()
        if resetKeyPassphraseDialog.ShowModal()==wx.ID_OK:
            print "Passphrase = " + resetKeyPassphraseDialog.getPassphrase()
        else:
            print "User canceled."
            return False

        return True

#app = MyApp(0)
#app.MainLoop()
