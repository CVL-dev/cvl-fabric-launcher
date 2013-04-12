#  MASSIVE/CVL Launcher - easy secure login for the MASSIVE Desktop and the CVL
#  Copyright (C) 2012  James Wettenhall, Monash University
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  Enquires: James.Wettenhall@monash.edu or help@massive.org.au

import sys
import wx
import launcher_version_number

class NewVersionAlertDialog(wx.Dialog):

    def __init__(self, parent, id, title, latestVersionNumber, latestVersionChanges, LAUNCHER_URL):

        wx.Dialog.__init__(self, parent, id, title, size=(680, 290), pos=(200,150))

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        massiveIconPanel = wx.Panel(self)

        import MASSIVE_icon
        massiveIconAsBitmap = MASSIVE_icon.getMASSIVElogoTransparent128x128Bitmap()
        wx.StaticBitmap(massiveIconPanel, wx.ID_ANY,
            massiveIconAsBitmap,
            (0, 50),
            (massiveIconAsBitmap.GetWidth(), massiveIconAsBitmap.GetHeight()))

        newVersionAlertPanel = wx.Panel(self)

        newVersionAlertPanelSizer = wx.FlexGridSizer(rows=8, cols=1, vgap=5, hgap=5)
        newVersionAlertPanel.SetSizer(newVersionAlertPanelSizer)

        newVersionAlertTitleLabel = wx.StaticText(newVersionAlertPanel,
            label = "MASSIVE/CVL Launcher")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetPointSize(14)
        font.SetWeight(wx.BOLD)
        newVersionAlertTitleLabel.SetFont(font)
        newVersionAlertPanelSizer.Add(wx.StaticText(newVersionAlertPanel))
        newVersionAlertPanelSizer.Add(newVersionAlertTitleLabel, flag=wx.EXPAND)
        newVersionAlertPanelSizer.Add(wx.StaticText(newVersionAlertPanel))

        newVersionAlertTextLabel1 = wx.StaticText(newVersionAlertPanel,
            label =
            "You are running version " + launcher_version_number.version_number + "\n\n" +
            "The latest version is " + latestVersionNumber + "\n\n" +
            "Please download a new version from:\n\n")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(9)
        newVersionAlertTextLabel1.SetFont(font)
        newVersionAlertPanelSizer.Add(newVersionAlertTextLabel1, flag=wx.EXPAND)

        newVersionAlertHyperlink = wx.HyperlinkCtrl(newVersionAlertPanel,
            id = wx.ID_ANY,
            label = LAUNCHER_URL,
            url = LAUNCHER_URL)
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(8)
        newVersionAlertHyperlink.SetFont(font)
        newVersionAlertPanelSizer.Add(newVersionAlertHyperlink, border=10, flag=wx.LEFT|wx.BORDER)
        newVersionAlertPanelSizer.Add(wx.StaticText(newVersionAlertPanel))

        self.latestVersionChangesTextCtrl = wx.TextCtrl(newVersionAlertPanel,
            size=(600, 200), style=wx.TE_MULTILINE|wx.TE_READONLY)
        newVersionAlertPanelSizer.Add(self.latestVersionChangesTextCtrl, flag=wx.EXPAND)
        if sys.platform.startswith("darwin"):
            font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        else:
            font = wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
        self.latestVersionChangesTextCtrl.SetFont(font)
        self.latestVersionChangesTextCtrl.AppendText(latestVersionChanges)
        self.latestVersionChangesTextCtrl.SetInsertionPoint(0)

        newVersionAlertPanelSizer.Add(wx.StaticText(newVersionAlertPanel, wx.ID_ANY, ""))
        newVersionAlertQueriesContactLabel = wx.StaticText(newVersionAlertPanel,
            label =
            "For queries, please contact:")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(9)
        newVersionAlertQueriesContactLabel.SetFont(font)
        newVersionAlertPanelSizer.Add(newVersionAlertQueriesContactLabel, border=10, flag=wx.EXPAND|wx.BORDER)

        contactEmailHyperlink = wx.HyperlinkCtrl(newVersionAlertPanel,
            id = wx.ID_ANY,
            label = "help@massive.org.au",
            url = "mailto:help@massive.org.au")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(8)
        contactEmailHyperlink.SetFont(font)
        newVersionAlertPanelSizer.Add(contactEmailHyperlink, border=20, flag=wx.LEFT|wx.BORDER)

        contactEmail2Hyperlink = wx.HyperlinkCtrl(newVersionAlertPanel,
            id = wx.ID_ANY,
            label = "James.Wettenhall@monash.edu",
            url = "mailto:James.Wettenhall@monash.edu")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(8)
        contactEmail2Hyperlink.SetFont(font)
        newVersionAlertPanelSizer.Add(contactEmail2Hyperlink, border=20, flag=wx.LEFT|wx.BORDER)

        def onOK(event):
            self.EndModal(wx.ID_OK)
            self.Destroy()

        okButton = wx.Button(newVersionAlertPanel, 1, ' OK ')
        okButton.SetDefault()
        newVersionAlertPanelSizer.Add(okButton, flag=wx.ALIGN_RIGHT)
        newVersionAlertPanelSizer.Add(wx.StaticText(newVersionAlertPanel))
        newVersionAlertPanelSizer.Fit(newVersionAlertPanel)

        self.Bind(wx.EVT_BUTTON, onOK, id=1)

        newVersionAlertDialogSizer = wx.FlexGridSizer(rows=1, cols=3, vgap=5, hgap=5)
        newVersionAlertDialogSizer.Add(massiveIconPanel, flag=wx.EXPAND)
        newVersionAlertDialogSizer.Add(newVersionAlertPanel, flag=wx.EXPAND)
        newVersionAlertDialogSizer.Add(wx.StaticText(self,label="       "))
        self.SetSizer(newVersionAlertDialogSizer)
        newVersionAlertDialogSizer.Fit(self)

