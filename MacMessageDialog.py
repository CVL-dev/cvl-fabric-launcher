import wx

import IconPys.MASSIVElogoTransparent64x64

class LauncherMessageDialog(wx.Dialog):
    def __init__(self, parent, message, title, **kw):
        wx.Dialog.__init__(self, parent, style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP, **kw)
       
        if parent!=None:
            self.CenterOnParent()
        else:
            self.Centre()

        self.dialogPanel = wx.Panel(self, wx.ID_ANY)

        iconAsBitmap = IconPys.MASSIVElogoTransparent64x64.getMASSIVElogoTransparent64x64Bitmap()
        self.iconBitmap = wx.StaticBitmap(self.dialogPanel, wx.ID_ANY, iconAsBitmap, pos=(25,15), size=(64,64))

        self.titleLabel = wx.StaticText(self.dialogPanel, wx.ID_ANY, title, pos=(105,15))
        titleFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        titleFont.SetWeight(wx.BOLD) 
        titleFont.SetPointSize(13)
        self.titleLabel.SetFont(titleFont) 

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        smallFont.SetPointSize(11)

        messageWidth = 330
        self.messageLabel = wx.StaticText(self.dialogPanel, wx.ID_ANY, message, pos=(105,39), size=(messageWidth,-1))
        self.messageLabel.SetForegroundColour((0,0,0))
        self.messageLabel.SetFont(smallFont)
        self.messageLabel.Wrap(messageWidth)

        dialogPanelWidth = 475
        dialogPanelHeight = max(self.messageLabel.GetPosition().y + self.messageLabel.GetSize().height + 70, 140)

        self.SetClientSize(wx.Size(dialogPanelWidth,dialogPanelHeight))
        self.dialogPanel.SetSize(wx.Size(dialogPanelWidth,dialogPanelHeight))

        okButtonSize = wx.Size(72,22)
        okButtonPosition = wx.Point(dialogPanelWidth - okButtonSize.width - 25, dialogPanelHeight - okButtonSize.height - 18)
        self.okButton = wx.Button(self.dialogPanel, wx.ID_ANY, "OK", pos=okButtonPosition, size=okButtonSize)

        self.okButton.SetDefault()

        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_BUTTON, self.onClose, id=self.okButton.GetId())

        self.contactQueriesContactLabel = wx.StaticText(self.dialogPanel, label = "For queries, please contact:")
        self.contactQueriesContactLabel.SetFont(smallFont)
        self.contactQueriesContactLabel.SetForegroundColour(wx.Colour(0,0,0))
        self.contactQueriesContactLabel.SetPosition(wx.Point(25,okButtonPosition.y))

        self.contactEmailHyperlink = wx.HyperlinkCtrl(self.dialogPanel, id = wx.ID_ANY, label = "help@massive.org.au", url = "mailto:help@massive.org.au")
        self.contactEmailHyperlink.SetFont(smallFont) # Or maybe even smaller font?
        #hyperlinkPosition = wx.Point(self.contactQueriesContactLabel.GetPosition().x+self.contactQueriesContactLabel.GetSize().width+10,okButtonPosition.y)
        hyperlinkPosition = wx.Point(self.contactQueriesContactLabel.GetPosition().x+self.contactQueriesContactLabel.GetSize().width,okButtonPosition.y)
        self.contactEmailHyperlink.SetPosition(hyperlinkPosition)

    def onClose(self, event):
        self.Show(False) 
        self.Destroy()

class MyApp(wx.App):
    def OnInit(self):
        message = "You have requested 2880 CPU hours, but you only have 455.0 CPU hours remaining in your quota for project \"Desc002\"."
        dialog = LauncherMessageDialog(parent=None, message=message, title="MASSIVE/CVL Launcher")
        dialog.ShowModal()
        return True

#app = MyApp(False)
#app.MainLoop()
