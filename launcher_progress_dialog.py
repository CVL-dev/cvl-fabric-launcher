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
#import time # Just for testing.
#import os # Just for testing.

class LauncherProgressDialog(wx.Frame):
    def __init__(self, parent, id, title, message, maxValue, onCancel):
        wx.Frame.__init__(self, parent, id, title, style=wx.STAY_ON_TOP|wx.FRAME_FLOAT_ON_PARENT)

        self.panel = wx.Panel(self, wx.ID_ANY) 
        self.messageStaticText = wx.StaticText(self.panel, label = message)

        self.progressBar = wx.Gauge(self, -1, maxValue)

        self.progressBar.SetSize(wx.Size(250, -1))
        
        sizer = wx.FlexGridSizer(rows=3, cols=3, vgap=5, hgap=15)

        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))
        sizer.Add(self.messageStaticText, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP|wx.BOTTOM, border=15)
        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))

        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))
        sizer.Add(self.progressBar, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=15)
        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))

        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))
        CANCEL_BUTTON_ID=123
        self.cancelButton = wx.Button(self.panel, CANCEL_BUTTON_ID, "Cancel")
        self.Bind(wx.EVT_BUTTON, onCancel, id=CANCEL_BUTTON_ID)
        sizer.Add(self.cancelButton, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=15)
        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))

        self.panel.SetSizerAndFit(sizer)
        self.Fit()

        return None

    def Update(self, value, message):
        self.progressBar.SetValue(value)
        self.messageStaticText.SetLabel(message)
        wx.Yield()

#class TestApp(wx.App):
    #def OnInit(self):

        #def onCancel(event):
            #os._exit(1)
        ## Parent shouldn't really be None because the progress dialgo uses the wx.FRAME_FLOAT_ON_PARENT style.
        #progressDialog = LauncherProgressDialog(None, wx.ID_ANY, "Connecting to MASSIVE...", "Connecting to MASSIVE...", 10, onCancel)
        #progressDialog.Show()

        #self.SetTopWindow(progressDialog)

        #time.sleep(0.5)
        #progressDialog.Update(1, "One")
        #time.sleep(0.5)
        #progressDialog.Update(2, "Two")
        #time.sleep(0.5)
        #progressDialog.Update(3, "Three")

        #return True

#app = TestApp(0)
#app.MainLoop()

