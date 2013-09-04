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

        import sys
        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)
        elif sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        #self.iconBitmap = wx.StaticBitmap(self.dialogPanel,bitmap=wx.ArtProvider.GetBitmap(wx.ART_INFORMATION), pos=(25,15), size=(32,32))
        iconAsBitmap = IconPys.MASSIVElogoTransparent64x64.getMASSIVElogoTransparent64x64Bitmap()
        self.iconBitmap = wx.StaticBitmap(self.dialogPanel,bitmap=iconAsBitmap, pos=(25,15), size=(64,64))

        self.SetTitle(title)

        smallFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        #smallFont.SetPointSize(11)

        self.messageLabel = wx.StaticText(self.dialogPanel, wx.ID_ANY, message)
        messageWidth = self.messageLabel.GetSize().width
        self.messageLabel.Destroy()
        messageWidth = min(messageWidth,450)
        self.messageLabel = wx.StaticText(self.dialogPanel, wx.ID_ANY, message, pos=(105,15), size=(messageWidth,-1))
        self.messageLabel.SetForegroundColour((0,0,0))
        self.messageLabel.SetFont(smallFont)
        self.messageLabel.Wrap(messageWidth)
        self.dialogPanel.Layout()

        dialogPanelWidth = messageWidth + 125
        dialogPanelHeight = max(self.messageLabel.GetSize().height + 70, 140)

        self.SetClientSize(wx.Size(dialogPanelWidth,dialogPanelHeight))
        self.dialogPanel.SetSize(wx.Size(dialogPanelWidth,dialogPanelHeight))

        okButtonSize = wx.Size(72,22)
        okButtonPosition = wx.Point(dialogPanelWidth - okButtonSize.width - 25, dialogPanelHeight - okButtonSize.height - 18)
        self.okButton = wx.Button(self.dialogPanel, wx.ID_ANY, "OK", pos=okButtonPosition, size=okButtonSize)

        self.okButton.SetDefault()

        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_BUTTON, self.onClose, id=self.okButton.GetId())

        self.queriesContactLabel = wx.StaticText(self.dialogPanel, label = "For queries, please contact:")
        self.queriesContactLabel.SetFont(smallFont)
        self.queriesContactLabel.SetForegroundColour(wx.Colour(0,0,0))
        self.queriesContactLabel.SetPosition(wx.Point(25,okButtonPosition.y))

        self.contactEmailHyperlink = wx.HyperlinkCtrl(self.dialogPanel, id = wx.ID_ANY, label = "help@massive.org.au", url = "mailto:help@massive.org.au")
        self.contactEmailHyperlink.SetFont(smallFont) # Or maybe even smaller font?
        #hyperlinkPosition = wx.Point(self.queriesContactLabel.GetPosition().x+self.queriesContactLabel.GetSize().width+10,okButtonPosition.y)
        hyperlinkPosition = wx.Point(self.queriesContactLabel.GetPosition().x+self.queriesContactLabel.GetSize().width+10,okButtonPosition.y)
        self.contactEmailHyperlink.SetPosition(hyperlinkPosition)
        self.contactEmailHyperlink.SetSize(self.contactEmailHyperlink.GetBestSize())

    def onClose(self, event):
        self.Show(False) 
        self.Destroy()

