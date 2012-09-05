""" Dialog to ask a modal question, with coder-specified list of buttons. 
"""

import wx
from wx.lib.evtmgr import eventManager

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
                b = wx.Button(self, id=button)
            else:
                b = wx.Button(self, label=button)

            eventManager.Register(dropArgs(curry(self.EndModal, i)), wx.EVT_BUTTON, b)
            buttonSizer.Add(b, flag=wx.ALL|wx.BORDER, border=25)
            #buttonSizer.Add(b, flag=wx.ALL)

        self.Fit()

    def OnClose(self, evt):
        # Ignoring wx.EVT_CLOSE
        # Dummy non-comment line to keep Python indenting happy:
        shouldCloseDialog = False

def questionDialog(message, buttons=[wx.ID_OK, wx.ID_CANCEL], caption=''):
    """ Ask a question.

    Return value will be the button the user clicked, in whatever form it was specified.
    Allowable button specifications are strings or wxIDs of stock buttons.

    If the user clicks the 'x' close button in the corner, the return value will be None.
    """

    dlg = ModalQuestion(None, message, buttons, title=caption)
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
