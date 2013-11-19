import wx

import IconPys.MASSIVElogoTransparent64x64

class LauncherMessageDialog(wx.Dialog):
    def __init__(self, parent, message, title, ButtonLabels=['OK'],**kw):
        wx.Dialog.__init__(self, parent, style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP, **kw)
       
        if parent!=None:
            self.CenterOnParent()
        else:
            self.Centre()

        self.dialogPanel = wx.Panel(self, wx.ID_ANY)
        #self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.ButtonLabels=ButtonLabels

        iconAsBitmap = IconPys.MASSIVElogoTransparent64x64.getMASSIVElogoTransparent64x64Bitmap()
        self.iconBitmap = wx.StaticBitmap(self.dialogPanel, wx.ID_ANY, iconAsBitmap, pos=(25,15), size=(64,64))


        #self.setTitle(title)

#        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
#        smallFont.SetPointSize(11)

        messageWidth = 330
        self.messageLabel = wx.StaticText(self.dialogPanel, wx.ID_ANY, message, pos=(105,39), size=(messageWidth,-1))
        #self.messageLabel = wx.StaticText(self.dialogPanel, wx.ID_ANY, message)
        self.messageLabel.SetForegroundColour((0,0,0))
        self.messageLabel.SetFont(smallFont)
        self.messageLabel.Wrap(messageWidth)

        buttonSize = wx.Size(72,22)
        buttonPanel = wx.Panel(self.dialogPanel,wx.ID_ANY)
        buttonPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        for label in ButtonLabels:
            #b = wx.Button(buttonPanel, wx.ID_ANY, label,size=buttonSize)
            b = wx.Button(buttonPanel, wx.ID_ANY, label)
            b.SetDefault()
            b.Bind(wx.EVT_BUTTON,self.onClose)
            buttonPanel.GetSizer().Add(b,border=5)
        buttonPanel.Fit()


        dialogPanelWidth = max(messageWidth,buttonPanel.GetSize().width)+145
        dialogPanelHeight = max(self.messageLabel.GetPosition().y + self.messageLabel.GetSize().height + 70, 140)

        self.SetClientSize(wx.Size(dialogPanelWidth,dialogPanelHeight))
        self.dialogPanel.SetSize(wx.Size(dialogPanelWidth,dialogPanelHeight))

        #self.GetSizer().Add(buttonPanel)
        
        buttonPosition = wx.Point(dialogPanelWidth - buttonPanel.GetSize().width - 25 , dialogPanelHeight - buttonPanel.GetSize().height - 18)
        buttonPanel.SetPosition(buttonPosition)

        self.Bind(wx.EVT_CLOSE, self.onClose)
        #self.Bind(wx.EVT_BUTTON, self.onClose, id=self.okButton.GetId())

        self.contactQueriesContactLabel = wx.StaticText(self.dialogPanel, label = "For queries, please contact:")
        self.contactQueriesContactLabel.SetFont(smallFont)
        self.contactQueriesContactLabel.SetForegroundColour(wx.Colour(0,0,0))
        self.contactQueriesContactLabel.SetPosition(wx.Point(25,buttonPosition.y))

        self.contactEmailHyperlink = wx.HyperlinkCtrl(self.dialogPanel, id = wx.ID_ANY, label = "help@massive.org.au", url = "mailto:help@massive.org.au")
        self.contactEmailHyperlink.SetFont(smallFont) # Or maybe even smaller font?
        #hyperlinkPosition = wx.Point(self.contactQueriesContactLabel.GetPosition().x+self.contactQueriesContactLabel.GetSize().width+10,okButtonPosition.y)
        hyperlinkPosition = wx.Point(self.contactQueriesContactLabel.GetPosition().x+self.contactQueriesContactLabel.GetSize().width,buttonPosition.y)
        self.contactEmailHyperlink.SetPosition(hyperlinkPosition)

    def onClose(self, event):
        obj=event.GetEventObject()
        if (isinstance(obj,wx.Button)):
            label=obj.GetLabel()
            ln=0
            for i in self.ButtonLabels:
                if (label==i):
                    self.EndModal(ln)
                else:
                    ln=ln+1
        else:
            self.EndModal(-1)

class MyApp(wx.App):
    def OnInit(self):
        message = "You have requested 2880 CPU hours, but you only have 455.0 CPU hours remaining in your quota for project \"Desc002\"."
        dialog = LauncherMessageDialog(parent=None, message=message, title="Undefined program name")
        dialog.ShowModal()
        return True
if __name__ == '__main__':
    app = MyApp(False)
    app.MainLoop()
