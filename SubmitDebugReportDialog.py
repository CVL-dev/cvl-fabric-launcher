#!/usr/bin/python

import wx
import os
import sys
import traceback

if os.path.abspath("..") not in sys.path:
    sys.path.append(os.path.abspath(".."))

class SubmitDebugReportDialog(wx.Dialog):
    def __init__(self, parent, id, title, debugLog, massiveLauncherConfig, massiveLauncherPreferencesFilePath,showFailedToOpenRemoteDesktopMessage=True):
        wx.Dialog.__init__(self, parent, id, title, wx.DefaultPosition)

        self.massiveLauncherConfig = massiveLauncherConfig
        self.massiveLauncherPreferencesFilePath = massiveLauncherPreferencesFilePath

        self.submitDebugReportDialogSizer = wx.FlexGridSizer(rows=1, cols=1)
        self.SetSizer(self.submitDebugReportDialogSizer)

        self.submitDebugReportDialogPanel = wx.Panel(self, wx.ID_ANY)
        self.submitDebugReportDialogPanelSizer = wx.FlexGridSizer(10,1)
        self.submitDebugReportDialogPanel.SetSizer(self.submitDebugReportDialogPanelSizer)

        self.submitDebugReportDialogSizer.Add(self.submitDebugReportDialogPanel, flag=wx.LEFT|wx.RIGHT|wx.TOP|wx.BOTTOM, border=15)

        # Instructions label

        if showFailedToOpenRemoteDesktopMessage:
            instructionsText = "The Launcher has failed to open a remote desktop.\n\n" 
        else:
            instructionsText = ""
        instructionsText = instructionsText + "You can submit a debug report to the Launcher developers."
        self.instructionsLabel = wx.StaticText(self.submitDebugReportDialogPanel, wx.ID_ANY, instructionsText)
        self.instructionsLabel.SetMinSize(wx.Size(600,-1))
        self.submitDebugReportDialogPanelSizer.Add(self.instructionsLabel, flag=wx.EXPAND|wx.BOTTOM, border=15)

        # Contact details panel

        self.contactDetailsPanel = wx.Panel(self.submitDebugReportDialogPanel, wx.ID_ANY)

        self.contactDetailsGroupBox = wx.StaticBox(self.contactDetailsPanel, wx.ID_ANY, label="Contact details")
        self.contactDetailsGroupBoxSizer = wx.StaticBoxSizer(self.contactDetailsGroupBox, wx.VERTICAL)
        self.contactDetailsPanel.SetSizer(self.contactDetailsGroupBoxSizer)

        self.innerContactDetailsPanel = wx.Panel(self.contactDetailsPanel, wx.ID_ANY)
        self.innerContactDetailsPanelSizer = wx.FlexGridSizer(5,2, hgap=10)
        self.innerContactDetailsPanel.SetSizer(self.innerContactDetailsPanelSizer)

        self.innerContactDetailsPanelSizer.AddGrowableCol(1)

        # Name

        self.nameLabel = wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, "Name:")
        self.innerContactDetailsPanelSizer.Add(self.nameLabel)

        name = ""
        if self.massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if self.massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "name"):
                name = self.massiveLauncherConfig.get("MASSIVE Launcher Preferences", "name")
        name = name.strip()

        self.nameField = wx.TextCtrl(self.innerContactDetailsPanel, wx.ID_ANY)
        self.nameField.SetValue(name)
        self.innerContactDetailsPanelSizer.Add(self.nameField, flag=wx.EXPAND)

        self.Bind(wx.EVT_TEXT, self.onNameOrEmailOrCommentsModified, id=self.nameField.GetId())

        # Blank space

        self.innerContactDetailsPanelSizer.Add(wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, ""))
        self.innerContactDetailsPanelSizer.Add(wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, ""))

        # Email

        self.emailLabel = wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, "Email address:")
        self.innerContactDetailsPanelSizer.Add(self.emailLabel)

        email = ""
        if self.massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            if self.massiveLauncherConfig.has_option("MASSIVE Launcher Preferences", "email"):
                email = self.massiveLauncherConfig.get("MASSIVE Launcher Preferences", "email")
        email = email.strip()

        self.emailField = wx.TextCtrl(self.innerContactDetailsPanel, wx.ID_ANY)
        self.emailField.SetValue(email)
        self.innerContactDetailsPanelSizer.Add(self.emailField, flag=wx.EXPAND)

        self.Bind(wx.EVT_TEXT, self.onNameOrEmailOrCommentsModified, id=self.emailField.GetId())

        # Blank space

        self.innerContactDetailsPanelSizer.Add(wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, ""))
        self.innerContactDetailsPanelSizer.Add(wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, ""))

        # Please contact me

        self.blankLabel = wx.StaticText(self.innerContactDetailsPanel, wx.ID_ANY, "")
        self.innerContactDetailsPanelSizer.Add(self.blankLabel)

        self.pleaseContactMeCheckBox = wx.CheckBox(self.innerContactDetailsPanel, wx.ID_ANY, "Please contact me")

        self.innerContactDetailsPanelSizer.Add(self.pleaseContactMeCheckBox, flag=wx.EXPAND)

        self.innerContactDetailsPanel.Fit()
        self.contactDetailsGroupBoxSizer.Add(self.innerContactDetailsPanel, flag=wx.EXPAND)
        self.contactDetailsPanel.Fit()

        self.submitDebugReportDialogPanelSizer.Add(self.contactDetailsPanel, flag=wx.EXPAND)

        # Blank space

        self.submitDebugReportDialogPanelSizer.Add(wx.StaticText(self.submitDebugReportDialogPanel, wx.ID_ANY, ""))

        # Comments panel

        self.commentsPanel = wx.Panel(self.submitDebugReportDialogPanel, wx.ID_ANY)

        self.commentsGroupBox = wx.StaticBox(self.commentsPanel, wx.ID_ANY, label="Comments")
        self.commentsGroupBoxSizer = wx.StaticBoxSizer(self.commentsGroupBox, wx.VERTICAL)
        self.commentsPanel.SetSizer(self.commentsGroupBoxSizer)

        self.innerCommentsPanel = wx.Panel(self.commentsPanel, wx.ID_ANY)
        self.innerCommentsPanelSizer = wx.FlexGridSizer(10,2, hgap=10)
        self.innerCommentsPanelSizer.AddGrowableCol(0)
        self.innerCommentsPanel.SetSizer(self.innerCommentsPanelSizer)

        self.commentsField = wx.TextCtrl(self.innerCommentsPanel, wx.ID_ANY, style=wx.TE_MULTILINE)
        self.innerCommentsPanelSizer.Add(self.commentsField, flag=wx.EXPAND)

        self.Bind(wx.EVT_TEXT, self.onNameOrEmailOrCommentsModified, id=self.commentsField.GetId())

        if self.nameField.GetValue().strip()=="":
            self.nameField.SetFocus()
        elif self.emailField.GetValue().strip()=="":
            self.emailField.SetFocus()
        else:
            self.commentsField.SetFocus()

        self.innerCommentsPanel.Fit()
        self.commentsGroupBoxSizer.Add(self.innerCommentsPanel, flag=wx.EXPAND)
        self.commentsPanel.Fit()

        self.submitDebugReportDialogPanelSizer.Add(self.commentsPanel, flag=wx.EXPAND)

        # Blank space

        self.submitDebugReportDialogPanelSizer.Add(wx.StaticText(self.submitDebugReportDialogPanel, wx.ID_ANY, ""))

        # Debug log panel

        self.debugLogPanel = wx.Panel(self.submitDebugReportDialogPanel, wx.ID_ANY)

        self.debugLogGroupBox = wx.StaticBox(self.debugLogPanel, wx.ID_ANY, label="Debug log")
        self.debugLogGroupBoxSizer = wx.StaticBoxSizer(self.debugLogGroupBox, wx.VERTICAL)
        self.debugLogPanel.SetSizer(self.debugLogGroupBoxSizer)

        self.innerDebugLogPanel = wx.Panel(self.debugLogPanel, wx.ID_ANY)
        self.innerDebugLogPanelSizer = wx.FlexGridSizer(10,2, hgap=10)
        self.innerDebugLogPanelSizer.AddGrowableCol(0)
        self.innerDebugLogPanel.SetSizer(self.innerDebugLogPanelSizer)


        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            smallFont.SetPointSize(11)

        self.debugLogField = wx.TextCtrl(self.innerDebugLogPanel, wx.ID_ANY, style=wx.TE_MULTILINE|wx.TE_READONLY)
        self.debugLogField.SetValue(debugLog)
        self.debugLogField.SetFont(smallFont)
        self.debugLogField.SetMinSize(wx.Size(-1,100))
        self.innerDebugLogPanelSizer.Add(self.debugLogField, flag=wx.EXPAND)

        self.innerDebugLogPanel.Fit()
        self.debugLogGroupBoxSizer.Add(self.innerDebugLogPanel, flag=wx.EXPAND)
        self.debugLogPanel.Fit()

        self.submitDebugReportDialogPanelSizer.Add(self.debugLogPanel, flag=wx.EXPAND)

        # Blank space

        self.submitDebugReportDialogPanelSizer.Add(wx.StaticText(self.submitDebugReportDialogPanel, wx.ID_ANY, ""))
        self.submitDebugReportDialogPanelSizer.Add(wx.StaticText(self.submitDebugReportDialogPanel, wx.ID_ANY, ""))

        # Buttons panel

        self.buttonsPanel = wx.Panel(self.submitDebugReportDialogPanel, wx.ID_ANY)
        self.buttonsPanelSizer = wx.FlexGridSizer(1,5, hgap=10, vgap=5)
        self.buttonsPanel.SetSizer(self.buttonsPanelSizer)

        self.cancelButton = wx.Button(self.buttonsPanel, wx.NewId(), "Cancel")
        self.buttonsPanelSizer.Add(self.cancelButton, flag=wx.BOTTOM, border=5)
        self.Bind(wx.EVT_BUTTON, self.onCancel, id=self.cancelButton.GetId())

        self.submitButton = wx.Button(self.buttonsPanel, wx.NewId(), "Submit")
        self.submitButton.SetDefault()
        self.Bind(wx.EVT_BUTTON, self.onSubmit, id=self.submitButton.GetId())
        self.buttonsPanelSizer.Add(self.submitButton, flag=wx.BOTTOM, border=5)

        self.buttonsPanel.Fit()

        self.submitDebugReportDialogPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT)

        # Calculate positions on dialog, using sizers

        self.submitDebugReportDialogPanel.Fit()
        self.Fit()

        self.CenterOnParent()

    def onCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def onSubmit(self, event):
        print "Submitting debug report."

        self.massiveLauncherConfig.set("MASSIVE Launcher Preferences", "name", self.nameField.GetValue().strip())
        with open(self.massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
            self.massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        self.massiveLauncherConfig.set("MASSIVE Launcher Preferences", "email", self.emailField.GetValue().strip())
        with open(self.massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
            self.massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)

        self.EndModal(wx.ID_OK)

    def getName(self):
        return self.nameField.GetValue().strip()

    def getEmail(self):
        return self.emailField.GetValue().strip()

    def getComments(self):
        return self.commentsField.GetValue().strip()

    def getPleaseContactMe(self):
        return self.pleaseContactMeCheckBox.GetValue()

    def onNameOrEmailOrCommentsModified(self, event):
        if self.commentsField.GetValue().strip()!="":
            self.pleaseContactMeCheckBox.SetValue(True)
        else:
            self.pleaseContactMeCheckBox.SetValue(False)

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

        sys.modules[__name__].massiveLauncherConfig = ConfigParser.RawConfigParser(allow_no_value=True)
        massiveLauncherConfig = sys.modules[__name__].massiveLauncherConfig
        sys.modules[__name__].massiveLauncherPreferencesFilePath = os.path.join(appUserDataDir,"MASSIVE Launcher Preferences.cfg")
        massiveLauncherPreferencesFilePath = sys.modules[__name__].massiveLauncherPreferencesFilePath
        if os.path.exists(massiveLauncherPreferencesFilePath):
            massiveLauncherConfig.read(massiveLauncherPreferencesFilePath)
        if not massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")

        debugLog = """
The quick brown fox jumped over the lazy dog.

"""
        dlg = SubmitDebugReportDialog(None,wx.ID_ANY,'MASSIVE/CVL Launcher',debugLog,massiveLauncherConfig,massiveLauncherPreferencesFilePath)
        dlg.ShowModal()
        os._exit(0)
        return True

if __name__ == '__main__':
    app = MyApp(False)
    app.MainLoop()

