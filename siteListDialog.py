import wx
from wx.lib.agw import ultimatelistctrl as ULC

class newSiteDialog(wx.Dialog):
    def __init__(self,siteList=None,*args,**kwargs):
        super(newSiteDialog,self).__init__(*args,**kwargs)
        self.SetSizer(wx.BoxSizer(wx.VERTICAL))
        t = wx.StaticText(self,wx.ID_ANY,label='Name')
        self.GetSizer().Add(t)
        self.nametctrl=wx.TextCtrl(self,wx.ID_ANY,size=(400,-1))
        self.GetSizer().Add(self.nametctrl,flag=wx.EXPAND)
        t = wx.StaticText(self,wx.ID_ANY,label='URL')
        self.GetSizer().Add(t)
        self.urltctrl=wx.TextCtrl(self,wx.ID_ANY,size=(400,-1))
        self.GetSizer().Add(self.urltctrl,flag=wx.EXPAND)
        p=wx.Panel(self)
        s=wx.BoxSizer(wx.HORIZONTAL)
        p.SetSizer(s)
        self.GetSizer().Add(p)
        b=wx.Button(p,wx.ID_OK,label='OK')
        b.Bind(wx.EVT_BUTTON,self.onClose)
        s.Add(b,flag=wx.ALL,border=5)
        b=wx.Button(p,wx.ID_CANCEL,label='Cancel')
        b.Bind(wx.EVT_BUTTON,self.onClose)
        s.Add(b,flag=wx.ALL,border=5)
        self.Fit()

    def getSite(self):
        return self.urltctrl.GetValue()

    def getName(self):
        return self.nametctrl.GetValue()

    def onClose(self,evt):
        self.EndModal(evt.GetEventObject().GetId())
        
        


class siteListDialog(wx.Dialog):
    def __init__(self,siteList=None,newSites=[],*args,**kwargs):
        super(siteListDialog,self).__init__(*args,**kwargs)
        mainSizer=wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(mainSizer)
        
        t=wx.StaticText(self,wx.ID_ANY,label="Available Sites")
        mainSizer.Add(t)
        self.siteList=ULC.UltimateListCtrl(self,wx.ID_ANY,size=(1000,200),agwStyle=ULC.ULC_REPORT|ULC.ULC_HAS_VARIABLE_ROW_HEIGHT)
        self.siteList.InsertColumn(0,"Name")
        self.siteList.InsertColumn(1,"URL")
        self.siteList.InsertColumn(2,"Active")
        i=0
        for s in siteList:
            self.siteList.InsertStringItem(i,"%s"%s['name'])
            self.siteList.SetStringItem(i,1,"%s"%s['url'])
            cb=wx.CheckBox(self.siteList)
            cb.SetValue(s['enabled'])
            self.siteList.SetItemWindow(i,col=2,wnd=cb)
            i=i+1
        urls=[]
        for s in siteList:
            urls.append(s['url'])
        for s in newSites:
            if s['url'] not in urls:
                self.siteList.InsertStringItem(i,"%s"%s['name'])
                self.siteList.SetStringItem(i,1,"%s"%s['url'])
                cb=wx.CheckBox(self.siteList)
                cb.SetValue(False)
                self.siteList.SetItemWindow(i,col=2,wnd=cb)
                i=i+1
                
        

        self.siteList.SetColumnWidth(0,wx.LIST_AUTOSIZE)
        self.siteList.SetColumnWidth(1,wx.LIST_AUTOSIZE)
        self.siteList.SetColumnWidth(2,wx.LIST_AUTOSIZE_USEHEADER)
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
            self.siteList.InsertStringItem(idx,dlg.getName())
            self.siteList.SetStringItem(idx,1,dlg.getSite())
            cb=wx.CheckBox(self.siteList)
            cb.SetValue(True)
            self.siteList.SetItemWindow(idx,col=2,wnd=cb)

    def onDelete(self,evt):
        i=self.siteList.GetFirstSelected()
        if i >=0:
            self.siteList.DeleteItem(i)
    def onClose(self,evt):
        self.EndModal(evt.GetEventObject().GetId())

    def getList(self):
        r=[]
        for i in range(0,self.siteList.GetItemCount()):
            name=self.siteList.GetItem(i,0)
            url=self.siteList.GetItem(i,1)
            ri={'name':name.GetText(),'url':url.GetText(),'enabled':self.siteList.GetItemWindow(i,2).GetValue()}
            r.append(ri)
        return r  
        
