# MASSIVE/CVL Launcher - easy secure login for the MASSIVE Desktop and the CVL
# Copyright (c) 2012-2013, Monash e-Research Centre (Monash University, Australia)
# All rights reserved.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
# 
# In addition, redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# -  Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 
# -  Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
# 
# -  Neither the name of the Monash University nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. SEE THE
# GNU GENERAL PUBLIC LICENSE FOR MORE DETAILS.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
# Enquiries: help@massive.org.au

import wx
from logger.Logger import logger

class LauncherProgressDialog(wx.Frame):
    def __init__(self, parent, id, title, message, maxValue, userCanAbort,cancelCallback=None):
        wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_DIALOG_STYLE|wx.FRAME_FLOAT_ON_PARENT)

        self.user_requested_abort = False
        self.cancelCallback=cancelCallback

        self.panel = wx.Panel(self, wx.ID_ANY) 
        # We'll just set a temporary message while the dialog,
        # is constructed, to represent the longest message
        # likely to appear in the progress dialog.
        # At the end of the __init__ method, we will use
        # SetLabel to set the initial message correctly.
        temporaryMessage = "Getting the one time password for the VNC server"
        self.messageStaticText = wx.StaticText(self.panel, label = temporaryMessage)

        self.progressBar = wx.Gauge(self, -1, maxValue)

        import sys
        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)
        elif sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())
        else:
            # FIXME OSX is handled somewhere else?
            pass

        #self.progressBar.SetSize(wx.Size(250, -1))
        statusMessageWidth = self.messageStaticText.GetSize().width
        self.progressBar.SetSize(wx.Size(statusMessageWidth, -1))
        
        if userCanAbort:
            sizer = wx.FlexGridSizer(rows=3, cols=3, vgap=5, hgap=15)
        else:
            sizer = wx.FlexGridSizer(rows=2, cols=3, vgap=5, hgap=15)

        sizer.AddGrowableCol(1)

        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))
        sizer.Add(self.messageStaticText, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP|wx.BOTTOM, border=15)
        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))

        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))
        sizer.Add(self.progressBar, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, border=15)
        sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))

        if userCanAbort:
            self.Bind(wx.EVT_CLOSE, self.onCancel)
            sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))
            CANCEL_BUTTON_ID=12345
            self.cancelButton = wx.Button(self.panel, CANCEL_BUTTON_ID, "Cancel")
            self.Bind(wx.EVT_BUTTON, self.onCancel, id=CANCEL_BUTTON_ID)
            sizer.Add(self.cancelButton, flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=15)
            sizer.Add(wx.StaticText(self.panel, wx.ID_ANY, " "))
        else:
            # Currently the Launcher only uses this class with userCanAbort=True,
            # so this event handler should never be called.
            self.Bind(wx.EVT_CLOSE, self.doNothing)

        self.panel.SetSizerAndFit(sizer)
        self.Fit()
        self.messageStaticText.SetLabel(message)
        self.Center()
        self.Show()

        return None

    def getProgress(self):
        return self.progressBar.GetValue()

    def shouldAbort(self):
        return self.user_requested_abort

    def doNothing(self, event):
        # Currently the Launcher only uses this class with userCanAbort=True,
        # so this event handler should never be called.
        logger.debug("User tried to close the progress dialog, even though userCanAbort is False.")

    def onCancel(self, event):
        self.messageStaticText.SetLabel("Aborting login...")
        self.user_requested_abort = True
        self.cancelButton.Enable(False)
        if (self.cancelCallback != None):
            self.cancelCallback()
    
    def setCancelCallback(self,callback):
        self.cancelCallback = callback

    def Update(self, value, message):
        if self.user_requested_abort:
            return
        self.progressBar.SetValue(value)
        self.messageStaticText.SetLabel(message)

