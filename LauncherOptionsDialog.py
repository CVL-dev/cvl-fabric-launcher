import wx
import sys

import IconPys.MASSIVElogoTransparent64x64

class LauncherOptionsDialog(wx.Dialog):
    def __init__(self, parent, message, title, ButtonLabels=['OK'],onHelp=None,helpEmailAddress="help@massive.org.au",**kw):
        wx.Dialog.__init__(self, parent, style=wx.DEFAULT_DIALOG_STYLE, **kw)
       
        if parent!=None:
            self.CenterOnParent()
        else:
            self.Centre()

        self.helpEmailAddress = helpEmailAddress

        if not sys.platform.startswith("darwin"):
            self.SetTitle(title)

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)
        elif sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.dialogPanel = wx.Panel(self, wx.ID_ANY)
        self.dialogPanel.SetSizer(wx.FlexGridSizer(cols=2,rows=2))
        #self.dialogPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.ButtonLabels=ButtonLabels
        self.onHelp=onHelp

        iconAsBitmap = IconPys.MASSIVElogoTransparent64x64.getMASSIVElogoTransparent64x64Bitmap()
        self.iconBitmap = wx.StaticBitmap(self.dialogPanel, wx.ID_ANY, iconAsBitmap, pos=(25,15), size=(64,64))

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            smallFont.SetPointSize(11)

        self.messagePanel = wx.Panel(self.dialogPanel)
        if sys.platform.startswith("darwin"):
            self.messagePanel.SetSizer(wx.FlexGridSizer(cols=1,rows=2))
            self.titleLabel = wx.StaticText(self.messagePanel, wx.ID_ANY, title)
            titleFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            titleFont.SetWeight(wx.BOLD)
            titleFont.SetPointSize(13)
            self.titleLabel.SetFont(titleFont)
            self.messagePanel.GetSizer().Add(self.titleLabel,flag=wx.BOTTOM,border=10)
        else:
            self.messagePanel.SetSizer(wx.FlexGridSizer(cols=1,rows=1))
        messageWidth = 330
        self.messageLabel = wx.StaticText(self.messagePanel, wx.ID_ANY, message)
        self.messageLabel.SetForegroundColour((0,0,0))
        self.messageLabel.SetFont(smallFont)
        self.messageLabel.Wrap(messageWidth)
        self.messagePanel.GetSizer().Add(self.messageLabel)

        contactPanel = wx.Panel(self.dialogPanel)
        contactPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
        contactQueriesContactLabel = wx.StaticText(contactPanel, label = "For queries, please contact:")
        contactQueriesContactLabel.SetFont(smallFont)
        contactQueriesContactLabel.SetForegroundColour(wx.Colour(0,0,0))
        contactPanel.GetSizer().Add(contactQueriesContactLabel)

        contactEmailHyperlink = wx.HyperlinkCtrl(contactPanel, id = wx.ID_ANY, label = self.helpEmailAddress, url = "mailto:"+self.helpEmailAddress)
        contactEmailHyperlink.SetFont(smallFont)
        #hyperlinkPosition = wx.Point(self.contactQueriesContactLabel.GetPosition().x+self.contactQueriesContactLabel.GetSize().width+10,okButtonPosition.y)
        #hyperlinkPosition = wx.Point(self.contactQueriesContactLabel.GetPosition().x+self.contactQueriesContactLabel.GetSize().width,buttonPosition.y)
        #self.contactEmailHyperlink.SetPosition(hyperlinkPosition)
        contactPanel.GetSizer().Add(contactEmailHyperlink)
        contactPanel.Fit()

        buttonPanel = wx.Panel(self.dialogPanel,wx.ID_ANY)
        buttonPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        for label in ButtonLabels:
            b = wx.Button(buttonPanel, wx.ID_ANY, label)
            b.SetDefault()
            b.Bind(wx.EVT_BUTTON,self.onClose)
            buttonPanel.GetSizer().Add(b,flag=wx.ALL,border=5)
        if self.onHelp is not None:
            b = wx.Button(buttonPanel, wx.ID_ANY, 'Help')
            b.Bind(wx.EVT_BUTTON,self.onHelp)
            buttonPanel.GetSizer().Add(b,flag=wx.ALL,border=5)
        buttonPanel.Fit()



        
        self.dialogPanel.GetSizer().Add(self.iconBitmap,flag=wx.ALL,border=15)
        self.dialogPanel.GetSizer().Add(self.messagePanel,flag=wx.ALL,border=15)
        self.dialogPanel.GetSizer().Add(contactPanel,flag=wx.ALL,border=15)
        self.dialogPanel.GetSizer().Add(buttonPanel,flag=wx.ALL,border=15)

        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.dialogPanel.Fit()

        #self.SetClientSize(wx.Size(dialogPanelWidth,dialogPanelHeight))
        self.Layout()
        self.Fit()

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

