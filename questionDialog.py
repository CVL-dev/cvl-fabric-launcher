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
# Enquires: James.Wettenhall@monash.edu or help@massive.org.au

# questionDialog.py

""" Dialog to ask a modal question, with coder-specified list of buttons. 
"""

import wx

class ModalQuestion(wx.Dialog):
    """ Ask a question.

    Modal return value will be the index into the list of buttons.  Buttons can be specified
    either as strings or as IDs.
    """

    def __init__(self, parent, message, buttons, **kw):
        wx.Dialog.__init__(self, parent, **kw)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        if parent==None:
            self.Centre()

        topSizer = wx.BoxSizer(orient=wx.VERTICAL)
        self.SetSizer(topSizer)

        topSizer.Add(wx.StaticText(self, label=message), flag=wx.ALIGN_CENTRE|wx.ALL|wx.BORDER, border=25)

        buttonSizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        topSizer.Add(buttonSizer, flag=wx.ALIGN_CENTRE)

        for i, button in enumerate(buttons):
            if isinstance(button, (int, long)):
                # A built-in button ID was passed in, like wx.ID_CANCEL
                b = wx.Button(self, id=button)
            else:
                # A button label string was passed in.
                b = wx.Button(self, label=button)

            self.Bind(wx.EVT_BUTTON, dropArgs(curry(self.EndModal, i)), id=b.GetId())
            buttonSizer.Add(b, flag=wx.ALL|wx.BORDER, border=25)
            #buttonSizer.Add(b, flag=wx.ALL)

        self.Fit()

    def OnClose(self, evt):
        # Ignoring wx.EVT_CLOSE
        # Dummy non-comment line to keep Python indenting happy:
        shouldCloseDialog = False

def questionDialog(message, buttons=[wx.ID_OK, wx.ID_CANCEL], caption='', **kwargs):
    """ Ask a question.

    Return value will be the button the user clicked, in whatever form it was specified.
    Allowable button specifications are strings or wxIDs of stock buttons.

    If the user clicks the 'x' close button in the corner, the return value will be None.
    """

    dlg = ModalQuestion(None, message, buttons, title=caption, **kwargs)
    try:
        return buttons[dlg.ShowModal()]
    except IndexError:
        return None

class curry(object):
    """Taken from the Python Cookbook, this class provides an easy way to
    tie up a function with some default parameters and call it later.
    See http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52549 for more.
    """
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.pending = args[:]
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        if kwargs and self.kwargs:
            kw = self.kwargs.copy()
            kw.update(kwargs)
        else:
            kw = kwargs or self.kwargs
        return self.func(*(self.pending + args), **kw)

class dropArgs(object):
    """ Same as curry, but once the function is built, further args are ignored. """

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args[:]
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        return self.func(*self.args, **self.kwargs)
