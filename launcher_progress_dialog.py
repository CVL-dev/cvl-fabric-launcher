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

import wx

class LauncherProgressDialog(wx.Frame):
    def __init__(self, parent, id, title, message, maxValue, userCanAbort):
        wx.Frame.__init__(self, parent, id, title, style=wx.STAY_ON_TOP)

        self.user_requested_abort = False

        self.panel = wx.Panel(self, wx.ID_ANY) 
        self.messageStaticText = wx.StaticText(self.panel, label = message)

        self.progressBar = wx.Gauge(self, -1, maxValue)

        self.progressBar.SetSize(wx.Size(250, -1))
        
        if userCanAbort:
            sizer = wx.FlexGridSizer(rows=3, cols=3, vgap=5, hgap=15)
        else:
            sizer = wx.FlexGridSizer(rows=2, cols=3, vgap=5, hgap=15)

        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))
        sizer.Add(self.messageStaticText, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP|wx.BOTTOM, border=15)
        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))

        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))
        sizer.Add(self.progressBar, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=15)
        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))

        if userCanAbort:
            sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))
            CANCEL_BUTTON_ID=12345
            self.cancelButton = wx.Button(self.panel, CANCEL_BUTTON_ID, "Cancel")
            self.Bind(wx.EVT_BUTTON, self.onCancel, id=CANCEL_BUTTON_ID)
            sizer.Add(self.cancelButton, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=15)
            sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))

        self.panel.SetSizerAndFit(sizer)
        self.Fit()
        self.Center()
        self.Show()

        return None

    def shouldAbort(self):
        return self.user_requested_abort

    def onCancel(self, event):
        self.messageStaticText.SetLabel("Aborting login...")
        self.user_requested_abort = True

    def Update(self, value, message):
        if self.user_requested_abort:
            return
        self.progressBar.SetValue(value)
        self.messageStaticText.SetLabel(message)

