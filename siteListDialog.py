import wx
from wx.lib.agw import ultimatelistctrl as ULC

class newSiteDialog(wx.Dialog):
    def __init__(self,siteList=None,*args,**kwargs):
        super(newSiteDialog,self).__init__(*args,**kwargs)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        self.tctrl=wx.TextCtrl(self,wx.ID_ANY,size=(400,-1))
        self.GetSizer().Add(self.tctrl,flag=wx.EXPAND)
        p=wx.Panel(self)
        s=wx.BoxSizer(wx.HORIZONTAL)
        p.SetSizer(s)
        self.GetSizer().Add(p)
        b=wx.Button(p,wx.ID_OK,label='OK')
        b.Bind(wx.EVT_BUTTON,self.onClose)
        s.Add(b)
        b=wx.Button(p,wx.ID_CANCEL,label='Cancel')
        b.Bind(wx.EVT_BUTTON,self.onClose)
        s.Add(b)
        self.Fit()

    def getSite(self):
        return self.tctrl.GetValue()

    def onClose(self,evt):
        self.EndModal(evt.GetEventObject().GetId())
        
        


class siteListDialog(wx.Dialog):
    def __init__(self,siteList=None,*args,**kwargs):
        super(siteListDialog,self).__init__(*args,**kwargs)
        mainSizer=wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(mainSizer)
        
        t=wx.StaticText(self,wx.ID_ANY,label="Available Sites")
        mainSizer.Add(t)
        self.siteList=ULC.UltimateListCtrl(self,wx.ID_ANY,size=(500,100),agwStyle=ULC.ULC_REPORT|ULC.ULC_HAS_VARIABLE_ROW_HEIGHT)
        self.siteList.InsertColumn(0,"Site")
        self.siteList.InsertColumn(1,"Active")
        i=0
        for s in siteList:
            self.siteList.InsertStringItem(i,"%s"%s[0])
            cb=wx.CheckBox(self.siteList)
            cb.SetValue(s[1])
            self.siteList.SetItemWindow(i,col=1,wnd=cb)
            i=i+1
        self.siteList.SetColumnWidth(0,wx.LIST_AUTOSIZE)
        self.siteList.SetColumnWidth(1,wx.LIST_AUTOSIZE_USEHEADER)
        mainSizer.Add(self.siteList,flag=wx.EXPAND)

        p=wx.Panel(self,wx.ID_ANY)
        s=wx.BoxSizer(wx.HORIZONTAL)
        b=wx.Button(p,id=wx.ID_OK,label="OK")
        s.Add(b)
        b.Bind(wx.EVT_BUTTON,self.onClose)
        b=wx.Button(p,id=wx.ID_NEW,label="New")
        s.Add(b)
        b.Bind(wx.EVT_BUTTON,self.onNew)
        b=wx.Button(p,id=wx.ID_DELETE,label="Delete")
        s.Add(b)
        b.Bind(wx.EVT_BUTTON,self.onDelete)
        p.SetSizer(s)
        mainSizer.Add(p,1,flag=wx.EXPAND)
        self.Fit()
        self.Refresh()
        self.Update()

    def onNew(self,evt):
        dlg=newSiteDialog(parent=self)
        r=dlg.ShowModal()
        print r
        if r==wx.ID_OK:
            idx=self.siteList.GetItemCount()
            self.siteList.InsertStringItem(idx,dlg.getSite())
            cb=wx.CheckBox(self.siteList)
            cb.SetValue(True)
            self.siteList.SetItemWindow(idx,col=1,wnd=cb)

    def onDelete(self,evt):
        i=self.siteList.GetFirstSelected()
        if i >=0:
            self.siteList.DeleteItem(i)
    def onClose(self,evt):
        self.EndModal(evt.GetEventObject().GetId())

    def getList(self):
        r=[]
        for i in range(0,self.siteList.GetItemCount()):
            ri=[self.siteList.GetItemText(i),self.siteList.GetItemWindow(i,1).GetValue()]
            r.append(ri)
        return r  
        
