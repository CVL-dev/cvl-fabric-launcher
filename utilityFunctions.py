import threading
import wx
import logging
from StringIO import StringIO
import HTMLParser
import os
import time
import subprocess
import inspect
import sys
import itertools
import wx.lib.mixins.listctrl as listmix
import zipfile

from logger.Logger import logger

#LAUNCHER_URL = "https://www.massive.org.au/index.php?option=com_content&view=article&id=121"
global LAUNCHER_URL
LAUNCHER_URL = "https://www.massive.org.au/userguide/cluster-instructions/massive-launcher"

# TURBOVNC_BASE_URL = "http://www.virtualgl.org/DeveloperInfo/PreReleases"
global TURBOVNC_BASE_URL
TURBOVNC_BASE_URL = "http://sourceforge.net/projects/virtualgl/files/TurboVNC/"

class sshKeyDistDisplayStrings():
    def __init__(self):
        self.passwdPrompt="enter passwd"
        self.passwdPromptIncorrect="passwd incorrect. reenter"
        self.passphrasePrompt="enter key passphrase"
        self.passphrasePromptIncorrectl="Incorrect. enter key passphrase"
        self.newPassphraseEmptyForbidden="new passphrase. empty passphrase forbidden"
        self.newPassphraseTooShort="passphrase to short. enter a new passphrase"
        self.newPassphraseMismatch="passphrases don't match. enter new passphrases"
        self.newPassphrase="new passphrase for new key"
        self.newPassphraseTitle="Please enter a new passphrase"

class sshKeyDistDisplayStringsCVL():
    def __init__(self):
        self.passwdPrompt="""Please enter the password for your CVL account.
This is the password you entered when you requested an account
at the website https://web.cvl.massive.org.au/users"""
        self.passwdPromptIncorrect="Sorry, that password was incorrect.\n"+self.passwdPrompt
        self.passphrasePrompt="Please enter the passphrase for your SSH key"
        self.passphrasePromptIncorrect="""Sorry, that passphrase was incorrect.
Please enter the passphrase for you SSH Key
If you have forgoten the passphrase for you key, you may need to delete it and create a new key.
You can find this option under the Identity menu.
"""
        self.newPassphrase="""It looks like this is the first time you're using the CVL on this
computer. To use the CVL, the launcher will generate a local
passphrase protected key on your computer which is used to
authenticate you and set up your remote CVL environment.

Please enter a new passphrase (twice to avoid typos) to protect your local key. 
After you've done this, your passphrase will be the primary method of
authentication for the launcher.

WHY?

This new method of authentication allows you to create file system
mounts to remote computer systems, and in the future it will support
launching remote HPC jobs."""
        self.newPassphraseEmptyForbidden="Sorry, empty passphrases are forbidden.\n"+self.newPassphrase
        self.createNewKeyDialogNewPassphraseEmptyForbidden="Sorry, empty passphrases are forbidden."
        self.newPassphraseTooShort="Sorry, the passphrase must be at least six characters.\n"+self.newPassphrase
        self.createNewKeyDialogNewPassphraseTooShort="Passphrase is too short."
        self.newPassphraseMismatch="Sorry, the two passphrases you entered don't match.\n"+self.newPassphrase
        self.createNewKeyDialogNewPassphraseMismatch="Passphrases don't match!"
        self.newPassphraseTitle="Please enter a new passphrase"

class sshKeyDistDisplayStringsMASSIVE():
    def __init__(self):
        self.passwdPrompt="""Please enter the password for your MASSIVE account."""
        self.passwdPromptIncorrect="Sorry, that password was incorrect.\n"+self.passwdPrompt
        self.passphrasePrompt="Please enter the passphrase for your SSH key"
        self.passphrasePromptIncorrect="""
Sorry, that passphrase was incorrect.
Please enter the passphrase for you SSH Key
If you have forgoten the passphrase for you key, you may need to delete it and create a new key.
You can find this option under the Identity menu.
"""
        self.newPassphrase="""It looks like this is the first time you're logging in to MASSIVE with this version of the launcher.
To make logging in faster and more secure, the launcher will generate a local
passphrase protected key on your computer which is used to
authenticate you and set up your MASSIVE desktop.

Please enter a new passphrase (twice to avoid typos) to protect your local key. 
After you've done this, your passphrase will be the primary method of
authentication for the launcher."""

        self.newPassphraseEmptyForbidden="Sorry, empty passphrases are forbidden.\n"+self.newPassphrase
        self.createNewKeyDialogNewPassphraseEmptyForbidden="Sorry, empty passphrases are forbidden."
        self.newPassphraseTooShort="Sorry, the passphrase must be at least 6 characters.\n"+self.newPassphrase
        self.createNewKeyDialogNewPassphraseTooShort="Passphrase is too short."
        self.newPassphraseMismatch="Sorry, the two passphrases you entered don't match.\n"+self.newPassphrase
        self.createNewKeyDialogNewPassphraseMismatch="Passphrases don't match!"
        self.newPassphraseTitle="Please enter a new passphrase"

def buildSiteConfigDict(configName):
    import re
    siteConfig={}
    siteConfig['messageRegexs']=[re.compile("^INFO:(?P<info>.*(?:\n|\r\n?))",re.MULTILINE),re.compile("^WARN:(?P<warn>.*(?:\n|\r\n?))",re.MULTILINE),re.compile("^ERROR:(?P<error>.*(?:\n|\r\n?))",re.MULTILINE)]

    if ("m1" in configName or "m2" in configName):
        siteConfig['listAllCmd']='qstat -u {username}'
        siteConfig['listAllRegEx']='^\s*(?P<jobid>(?P<jobidNumber>[0-9]+).\S+)\s+{username}\s+(?P<queue>\S+)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>[^C])\s+(?P<elapTime>\S+)\s*$'
        siteConfig['runningCmd']='qstat -u {username}'
        siteConfig['runningRegEx']='^\s*(?P<jobid>{jobid})\s+{username}\s+(?P<queue>\S+)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>R)\s+(?P<elapTime>\S+)\s*$'
        # request_visnode is a little buggy, if you issue a qdel <jobid> ; request_visnode it may provide the id of the deleted job. Sleep to work around
        siteConfig['stopCmd']='\'qdel -a {jobid}\''
        siteConfig['stopCmdForRestart']='\'qdel {jobid} ; sleep 5\''
        siteConfig['execHostCmd']='qpeek {jobidNumber}'
        siteConfig['execHostRegEx']='\s*To access the desktop first create a secure tunnel to (?P<execHost>\S+)\s*$'
        siteConfig['startServerCmd']="\'/usr/local/desktop/request_visnode.sh {project} {hours} {nodes} True False False\'"
        siteConfig['runSanityCheckCmd']="\'/usr/local/desktop/sanity_check.sh {launcher_version_number}\'"
        siteConfig['setDisplayResolutionCmd']="\'/usr/local/desktop/set_display_resolution.sh {resolution}\'"
        siteConfig['getProjectsCmd']='\"gbalance -u {username} --show Name | tail -n +3\"'
        siteConfig['getProjectsCmd']='\"glsproject -A -q | grep \',{username},\|\s{username},\|,{username}\s\' \"'
        siteConfig['getProjectsRegEx']='^(?P<group>\S+)\s+.*$'
        siteConfig['startServerRegEx']="^(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s*$"
        siteConfig['showStartCmd']="showstart {jobid}"
        siteConfig['showStartRegEx']="Estimated Rsv based start .*?on (?P<estimatedStart>.*)"
        siteConfig['vncDisplayCmd']= '"/usr/bin/ssh {execHost} \' module load turbovnc ; vncserver -list\'"'
        siteConfig['vncDisplayRegEx']='^(?P<vncDisplay>:[0-9]+)\s*(?P<vncPID>[0-9]+)\s*$'
        siteConfig['otpCmd']= '"/usr/bin/ssh {execHost} \' module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\'"'
        siteConfig['otpRegEx']='^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$'
        siteConfig['directConnect']=False
        siteConfig['webDavIntermediatePortCmd']='/usr/local/desktop/get_ephemeral_port.py'
        siteConfig['webDavIntermediatePortRegEx']='^(?P<intermediateWebDavPortNumber>[0-9]+)$'
        siteConfig['webDavRemotePortCmd']='"/usr/bin/ssh {execHost} \'/usr/local/desktop/get_ephemeral_port.py\'"'
        siteConfig['webDavRemotePortRegEx']='^(?P<remoteWebDavPortNumber>[0-9]+)$'
        '(?P<port1>.*)\n(?P<port2>.*)'
        siteConfig['openWebDavShareInRemoteFileBrowserCmd']='"/usr/bin/ssh {execHost} \'DISPLAY={vncDisplay} /usr/bin/konqueror webdav://{localUsername}:{vncPasswd}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\'"'
        displayWebDavInfoDialogOnRemoteDesktop = False
        if displayWebDavInfoDialogOnRemoteDesktop:
            if sys.platform.startswith("win"):
                lt = "^<"
                gt = "^>"
            else:
                lt = "<"
                gt = ">"
            siteConfig['displayWebDavAccessInfoInRemoteDialogCmd']='"/usr/bin/ssh {execHost} \'echo -e \\"You can access your local home directory in Konqueror with the URL:%sbr%s\\nwebdav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}%sbr%s\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt; sleep 2; DISPLAY={vncDisplay} kdialog --title \\"MASSIVE/CVL Launcher\\" --textbox ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt 490 150\'"' % (lt,gt,lt,gt)
        else:
            siteConfig['displayWebDavAccessInfoInRemoteDialogCmd']='"/usr/bin/ssh {execHost} \'echo -e \\"You can access your local home directory in Konqueror with the URL:\\nwebdav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt;\'"'
    else:
        siteConfig['directConnect']=True
        siteConfig['execHostCmd']='\"module load pbs ; qstat -f {jobidNumber} | grep exec_host | sed \'s/\ \ */\ /g\' | cut -f 4 -d \' \' | cut -f 1 -d \'/\' | xargs -iname hostn name | grep address | sed \'s/\ \ */\ /g\' | cut -f 3 -d \' \' | xargs -iip echo execHost ip; qstat -f {jobidNumber}\"'
        siteConfig['execHostRegEx']='^\s*execHost (?P<execHost>\S+)\s*$'
        siteConfig['getProjectsCmd']='\"groups | sed \'s@ @\\n@g\'\"' # '\'groups | sed \'s\/\\\\ \/\\\\\\\\n\/g\'\''
        siteConfig['getProjectsRegEx']='^\s*(?P<group>\S+)\s*$'
        siteConfig['listAllCmd']='\"module load pbs ; module load maui ; qstat | grep {username}\"'
        siteConfig['listAllRegEx']='^\s*(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s+(?P<jobname>desktop_\S+)\s+{username}\s+(?P<elapTime>\S+)\s+(?P<state>R)\s+(?P<queue>\S+)\s*$'
        siteConfig['runningCmd']='\"module load pbs ; module load maui ; qstat | grep {username}\"'
        siteConfig['runningRegEx']='^\s*(?P<jobid>{jobidNumber}\.\S+)\s+(?P<jobname>desktop_\S+)\s+{username}\s+(?P<elapTime>\S+)\s+(?P<state>R)\s+(?P<queue>\S+)\s*$'
        if ("Hugyens" in configName):
            siteConfig['startServerCmd']="\"module load pbs ; module load maui ; echo \'module load pbs ; /usr/local/bin/vncsession --vnc turbovnc --geometry {resolution} ; sleep {wallseconds}\' |  qsub -q huygens -l nodes=1:ppn=1,walltime={wallseconds} -N desktop_{username} -o .vnc/ -e .vnc/\""
        else:
            siteConfig['startServerCmd']="\"module load pbs ; module load maui ; echo \'module load pbs ; /usr/local/bin/vncsession --vnc turbovnc --geometry {resolution} ; sleep {wallseconds}\' |  qsub -l nodes=1:ppn=1,walltime={wallseconds} -N desktop_{username} -o .vnc/ -e .vnc/\""
        siteConfig['startServerRegEx']="^(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s*$"
        siteConfig['stopCmd']='\"module load pbs ; module load maui ; qdel -a {jobidNumber}\"'
        siteConfig['stopCmdForRestart']='\"module load pbs ; module load maui ; qdel {jobidNumber}\"'
        siteConfig['showStartCmd']=None
        siteConfig['showStartRegEx']="Estimated Rsv based start on (?P<estimatedStart>^-.*)"
        siteConfig['vncDisplayCmd']= '" /usr/bin/ssh {execHost} \' cat /var/spool/torque/spool/{jobidNumber}.*\'"'
        siteConfig['vncDisplayRegEx']='^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$'
        siteConfig['otpCmd']= '"/usr/bin/ssh {execHost} \' module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\'"'
        siteConfig['otpRegEx']='^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$'
        siteConfig['passwdPrompt']='Please enter your CVL password for username {username}.\n\nIf you are using the CVL for the first time,\nthis is the password you entered when you applied for an account\non the webpage https://web.cvl.massive.org.au'
        siteConfig['runSanityCheckCmd']=None
        # Below, I initially tried to respect the user's Nautilus setting of always_use_location_entry and change it back after launching Nautilus,
        # but doing so changes this setting in already-running Nautilus windows, and I want the user to see Nautilus's location bar when showing 
        # them the WebDav share.  So now, I just brutally change the user's Nautilus location-bar setting to always_use_location_entry.
        # Note that we might end up mounting WebDAV in a completely different way (e.g. using wdfs), but for now I'm trying to make the user
        # experience similar on MASSIVE and the CVL.  On MASSIVE, users are not automatically added to the "fuse" group, but they can still 
        # access a WebDAV share within Konqueror.  The method below for the CVL/Nautilus does require fuse membership, but it ends up looking
        # similar to MASSIVE/Konqueror from the user's point of view.  Note that getting drag and drop working nicely depends on patching
        # gtk2 (see CVLFAB-622 on JIRA).
        if sys.platform.startswith("win"):
            pipe = "^|"
        else:
            pipe = "|"
        siteConfig['openWebDavShareInRemoteFileBrowserCmd']="\"/usr/bin/ssh {execHost} \\\". \\\\\\\"\\$HOME/.dbus/session-bus/\\$(cat /var/lib/dbus/machine-id)-`echo {vncDisplay} | tr -d ':' | tr -d '.0'`\\\\\\\"; export DBUS_SESSION_BUS_ADDRESS;echo \\\\\\\"import pexpect;child = pexpect.spawn('gvfs-mount dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}');child.expect('Password: ');child.sendline('{vncPasswd}')\\\\\\\" %s python;/usr/bin/gconftool-2 --type=Boolean --set /apps/nautilus/preferences/always_use_location_entry true;DISPLAY={vncDisplay} /usr/bin/nautilus dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName};\\\"\"" % (pipe)
        displayWebDavInfoDialogOnRemoteDesktop = False
        if displayWebDavInfoDialogOnRemoteDesktop:
            siteConfig['displayWebDavAccessInfoInRemoteDialogCmd']='"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" | DISPLAY={vncDisplay} zenity --title \\"MASSIVE/CVL Launcher\\" --text-info --width 490 --height 175\'"'
        else:
            siteConfig['displayWebDavAccessInfoInRemoteDialogCmd']='"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt\'"'

    if (siteConfig.has_key('directConnect') and siteConfig['directConnect']):
        # Carlo: I've disabled StrickHostKeyChecking here temporarily untill all CVL vms are added a a most known hosts file.
        # FIXME: This workaround for the server-side host key issue was only applied to the 'directConnect' case.
        # Do we need to add it to the non-directConnect case?  Or are we confident that the server-side host key
        # issues have been fixed now?
        siteConfig['agentCmd']='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -l {username} {execHost} "echo agent_hello; bash "'
        siteConfig['agentRegEx']='agent_hello'
        siteConfig['tunnelCmd']='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -L {localPortNumber}:localhost:{remotePortNumber} -l {username} {execHost} "echo tunnel_hello; bash"'
        siteConfig['tunnelRegEx']='tunnel_hello'
        #siteConfig['webDavTunnelCmd']='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -T -R {remoteWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {execHost} "echo tunnel_hello; bash"'
        siteConfig['webDavTunnelCmd']='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {remoteWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {execHost} "echo tunnel_hello; bash"'
        siteConfig['webDavTunnelRegEx']='tunnel_hello'
        siteConfig['webDavIntermediatePortCmd']='echo hello'
        siteConfig['webDavIntermediatePortRegEx']='hello'
        siteConfig['webDavRemotePortCmd']='"/usr/bin/ssh {execHost} \'/usr/local/bin/get_ephemeral_port.py\'"'
        siteConfig['webDavRemotePortRegEx']='^(?P<remoteWebDavPortNumber>[0-9]+)$'
    else:
        siteConfig['agentCmd']='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -l {username} {loginHost} \"/usr/bin/ssh -A {execHost} \\"echo agent_hello; bash \\"\"'
        siteConfig['agentRegEx']='agent_hello'
        siteConfig['tunnelCmd']='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -L {localPortNumber}:{execHost}:{remotePortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"'
        siteConfig['tunnelRegEx']='tunnel_hello'
        #siteConfig['webDavTunnelCmd']='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -T -R {intermediateWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "ssh -T -R {remoteWebDavPortNumber}:localhost:{intermediateWebDavPortNumber} {execHost} \'echo tunnel_hello; bash\'"'
        siteConfig['webDavTunnelCmd']='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {intermediateWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "ssh -R {remoteWebDavPortNumber}:localhost:{intermediateWebDavPortNumber} {execHost} \'echo tunnel_hello; bash\'"'
        siteConfig['webDavTunnelRegEx']='tunnel_hello'
    return siteConfig
    

def parseMessages(regexs,stdout,stderr):
    # compare each line of output against a list of regular expressions and build up a dictionary of messages to give the user
    messages={}
    for line  in itertools.chain(stdout.splitlines(True),stderr.splitlines(True)):
        for re in regexs:
            match = re.search(line)
            if (match):
                for key in match.groupdict().keys():
                    if messages.has_key(key):
                        messages[key]=messages[key]+match.group(key)
                    else:
                        messages[key]=match.group(key)
    return messages

class ListSelectionDialog(wx.Dialog):
    class ResizeListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
        def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
            wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
            listmix.ListCtrlAutoWidthMixin.__init__(self)


    def __init__(self, *args, **kw):
        if kw.has_key('parent'):
            self.parent=kw.get('parent')
            logger.debug("ListSelectionDialog: parent is not None.")
            logger.debug("ListSelectionDialog: parent class name is " + self.parent.__class__.__name__) 
        else:
            self.parent = None
            logger.debug("ListSelectionDialog: parent is None.")
        if kw.has_key('headers'):
            self.headers=kw.pop('headers')
        else:
            self.headers=None
        if kw.has_key('items'):
            self.items=kw.pop('items')
        else:
            self.items=None
        if kw.has_key('message'):
            self.message=kw.pop('message')
        else:
            self.message=None
        if kw.has_key('noSelectionMessage'):
            self.noSelectionMessage=kw.pop('noSelectionMessage')
        else:
            self.noSelectionMessage="Please select a valid item from the list.",
        if kw.has_key('okCallback'):
            self.okCallback=kw.pop('okCallback')
        else:
            logger.debug("okCallback set to none")
            self.okCallback=None
        if kw.has_key('cancelCallback'):
            self.cancelCallback=kw.pop('cancelCallback')
        else:
            logger.debug("cancelCallback set to none")
            self.cancelCallback=None
        super(ListSelectionDialog, self).__init__(*args, **kw)
        self.itemList=[]
       
        self.closedProgressDialog = False
        if self.parent is not None and self.parent.__class__.__name__=="LauncherMainFrame":
            launcherMainFrame = self.parent
            if launcherMainFrame is not None and launcherMainFrame.progressDialog is not None:
                launcherMainFrame.progressDialog.Show(False)
                self.closedProgressDialog = True

        self.CenterOnParent()

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        listSelectionDialogPanel = wx.Panel(self)
        listSelectionDialogSizer = wx.FlexGridSizer(rows=1, cols=1)
        self.SetSizer(listSelectionDialogSizer)
        listSelectionDialogSizer.Add(listSelectionDialogPanel, flag=wx.LEFT|wx.RIGHT|wx.TOP|wx.BOTTOM, border=10)

        iconPanel = wx.Panel(listSelectionDialogPanel)

        import MASSIVE_icon
        iconAsBitmap = MASSIVE_icon.getMASSIVElogoTransparent128x128Bitmap()
        wx.StaticBitmap(iconPanel, wx.ID_ANY,
            iconAsBitmap,
            (0, 25),
            (iconAsBitmap.GetWidth(), iconAsBitmap.GetHeight()))

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        lcSizer = wx.BoxSizer(wx.VERTICAL)
        rcSizer = wx.BoxSizer(wx.VERTICAL)


        contactPanel = wx.Panel(listSelectionDialogPanel)
        contactPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=5, hgap=5)
        contactPanel.SetSizer(contactPanelSizer)
        contactQueriesContactLabel = wx.StaticText(contactPanel, label = "For queries, please contact:")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(9)
        contactQueriesContactLabel.SetFont(font)

        contactEmailHyperlink = wx.HyperlinkCtrl(contactPanel, id = wx.ID_ANY, label = "help@massive.org.au", url = "mailto:help@massive.org.au")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(8)
        contactEmailHyperlink.SetFont(font)

        contactPanelSizer.Add(contactQueriesContactLabel, border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BORDER)
        contactPanelSizer.Add(contactEmailHyperlink, border=20, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.BORDER)

        contactPanelSizer.Fit(contactPanel)

        listSelectionPanel = wx.Panel(listSelectionDialogPanel)
        listSelectionPanelSizer = wx.BoxSizer(wx.VERTICAL)
        listSelectionPanel.SetSizer(listSelectionPanelSizer)
        if (self.message!=None):
            messageText = wx.StaticText(parent=listSelectionPanel,id=wx.ID_ANY,label=self.message)
            listSelectionPanelSizer.Add(messageText,border=5,flag=wx.ALL^wx.EXPAND)
        if (self.headers!=None):
            self.listSelectionList=ListSelectionDialog.ResizeListCtrl(listSelectionPanel,-1,style=wx.LC_REPORT|wx.EXPAND)
        else:
            self.listSelectionList=ListSelectionDialog.ResizeListCtrl(listSelectionPanel,-1,style=wx.LC_REPORT|wx.EXPAND|wx.LC_NO_HEADER)
        col=0
        if (self.headers!=None):
            for hdr in self.headers:
                self.listSelectionList.InsertColumn(col,hdr,width=-1)
                col=col+1
        elif (self.items!=None):
            if (len(self.items)>0 and isinstance(self.items[0],list)):
                for i in self.items[0]:
                    self.listSelectionList.InsertColumn(col,"",width=-1)
            else:
                self.listSelectionList.InsertColumn(col,"",width=-1)
        if (self.items!=None):
            for item in self.items:
                if (isinstance(item,list)):
                    self.listSelectionList.Append(item)
                    #self.listSelectionList.InsertStringItem(0,item)
                else:
                    self.listSelectionList.Append([item])
        #self.listSelectionList=wx.ListView(listSelectionPanel,style=wx.LC_REPORT)
        listSelectionPanelSizer.Add(self.listSelectionList,proportion=1,border=10,flag=wx.EXPAND|wx.ALL)

        self.buttonsPanel = wx.Panel(listSelectionDialogPanel, wx.ID_ANY)
        self.buttonsPanelSizer = wx.FlexGridSizer(rows=1, cols=2, hgap=5, vgap=5)
        self.buttonsPanel.SetSizer(self.buttonsPanelSizer)

        self.cancelButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Cancel')
        self.cancelButton.SetDefault()
        self.cancelButton.Bind(wx.EVT_BUTTON, self.onClose)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        # Bottom border of 5 is a workaround for an OS X bug where bottom of button can be clipped.
        self.buttonsPanelSizer.Add(self.cancelButton, flag=wx.BOTTOM, border=5)

        self.okButton = wx.Button(self.buttonsPanel, wx.ID_ANY, ' OK ')
        self.okButton.SetDefault()
        self.okButton.Bind(wx.EVT_BUTTON, self.onClose)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        #self.okButton.Disable()
        # Bottom border of 5 is a workaround for an OS X bug where bottom of button can be clipped.
        self.buttonsPanelSizer.Add(self.okButton, flag=wx.BOTTOM, border=5)

        self.buttonsPanel.Fit()

        #self.listSelectionList.Bind(wx.EVT_LIST_ITEM_SELECTED,self.onFocus)
        self.listSelectionList.Bind(wx.EVT_LIST_ITEM_ACTIVATED,self.onClose)

        lcSizer.Add(iconPanel,proportion=1,flag=wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_LEFT)
        lcSizer.Add(contactPanel,proportion=0,flag=wx.ALIGN_LEFT|wx.ALIGN_BOTTOM)
        rcSizer.Add(listSelectionPanel,proportion=1,flag=wx.EXPAND)
        #rcSizer.Add(self.okButton,proportion=0,flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.BOTTOM,border=5)
        rcSizer.Add(self.buttonsPanel,proportion=0,flag=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM)
        sizer.Add(lcSizer,proportion=0,flag=wx.EXPAND)
        sizer.Add(rcSizer,proportion=1,flag=wx.EXPAND)
        listSelectionDialogPanel.SetSizer(sizer)
        sizer.Fit(listSelectionDialogPanel)
        self.Fit()

        self.listSelectionList.SetFocus()

    def setItems(self,items,headers=None):
        self.itemList=items
        if headers!=None:
            col=0
            for hdr in headers:
                print hdr
                self.listSelectionList.InsertColumn(col,hdr,width=-1)
                col=col+1
        for item in self.itemList:
            self.listSelectionList.Append(item)

    #def onFocus(self,e):
        #if (self.listSelectionList.GetSelectedItemCount()>0):
            #self.okButton.Enable()
        #else:
            #self.okButton.Disable()

    def onClose(self, e):
   
        logger.debug("ListSelectionDialog.onClose: button ID %s okButton ID %s cancelButton ID %s"%(e.GetId(),self.okButton.GetId(),self.cancelButton.GetId()))
        if (e.GetId() == self.cancelButton.GetId()):
            logger.debug("ListSelectionDialog.onClose: User canceled.")
            if self.cancelCallback != None:
                #self.cancelCallback("User canceled from ListSelectionDialog.")
                self.cancelCallback("")
            self.Destroy()
            return

        if self.listSelectionList.GetFirstSelected()==-1:
            dlg = wx.MessageDialog(self.parent, 
                self.noSelectionMessage,
                "MASSIVE/CVL Launcher", 
                wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            self.listSelectionList.SetFocus()
            return

        itemnum=self.listSelectionList.GetFocusedItem()
        item=self.listSelectionList.GetItem(itemnum,0)
        if self.okCallback != None:
            self.okCallback(item)
        self.Destroy()

        if self.closedProgressDialog:
            if self.parent is not None and self.parent.__class__.__name__=="LauncherMainFrame":
                launcherMainFrame = self.parent
                if launcherMainFrame is not None and launcherMainFrame.progressDialog is not None:
                    launcherMainFrame.progressDialog.Show(True)


class HelpDialog(wx.Dialog):
    def __init__(self, *args, **kw):
        super(HelpDialog, self).__init__(*args, **kw)

        self.callback=None
         
        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.CenterOnParent()

        iconPanel = wx.Panel(self)

        import MASSIVE_icon
        iconAsBitmap = MASSIVE_icon.getMASSIVElogoTransparent128x128Bitmap()
        wx.StaticBitmap(iconPanel, wx.ID_ANY,
            iconAsBitmap,
            (0, 25),
            (iconAsBitmap.GetWidth(), iconAsBitmap.GetHeight()))

        sizer = wx.FlexGridSizer(rows=2, cols=2, vgap=5, hgap=5)


        contactPanel = wx.Panel(self)
        contactPanelSizer = wx.FlexGridSizer(rows=2, cols=1, vgap=5, hgap=5)
        contactPanel.SetSizer(contactPanelSizer)
        contactQueriesContactLabel = wx.StaticText(contactPanel, label = "For queries, please contact:")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(9)
        contactQueriesContactLabel.SetFont(font)

        contactEmailHyperlink = wx.HyperlinkCtrl(contactPanel, id = wx.ID_ANY, label = "help@massive.org.au", url = "mailto:help@massive.org.au")
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        if sys.platform.startswith("darwin"):
            font.SetPointSize(11)
        else:
            font.SetPointSize(8)
        contactEmailHyperlink.SetFont(font)

#        contactPanelSizer.Add(wx.StaticText(contactPanel, wx.ID_ANY, ""))
        contactPanelSizer.Add(contactQueriesContactLabel, border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BORDER)
        contactPanelSizer.Add(contactEmailHyperlink, border=20, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.BORDER)

        #contactPanelSizer.Add(wx.StaticText(contactPanel))
        contactPanelSizer.Fit(contactPanel)

        okButton = wx.Button(self, 1, ' OK ')
        okButton.SetDefault()
        okButton.Bind(wx.EVT_BUTTON, self.OnClose)

        sizer.Add(iconPanel, flag=wx.EXPAND|wx.ALIGN_TOP|wx.ALIGN_LEFT)
        sizer.Add(contactPanel)
        sizer.Add(okButton, flag=wx.RIGHT|wx.BOTTOM)
        #sizer.Add(wx.StaticText(self,label="       "))
        self.SetSizer(sizer)
        sizer.Fit(self)

    def setCallback(self,callback):
        self.callback=callback


    def addPanel(self,panel):
        self.GetSizer().Insert(1,panel,flag=wx.EXPAND)
        self.GetSizer().Fit(self)


    def OnClose(self, e):
        self.Destroy()
        if self.callback != None:
            self.callback()


class MyHtmlParser(HTMLParser.HTMLParser):
    def __init__(self, valueString):
        HTMLParser.HTMLParser.__init__(self)
        self.recording = 0
        self.data = []
        self.recordingLatestVersionNumber = 0
        self.latestVersionNumber = "0.0.0"
        self.htmlComments = ""
        self.valueString = valueString

    def handle_starttag(self, tag, attributes):
        if tag != 'span':
            return
        if tag == "span":
            if self.recordingLatestVersionNumber:
                self.recordingLatestVersionNumber += 1
                return
        foundLatestVersionNumberTag = False
        for name, value in attributes:
            if name == 'id' and value == self.valueString:
                foundLatestVersionNumberTag = True
                break
        else:
            return
        if foundLatestVersionNumberTag:
            self.recordingLatestVersionNumber = 1

    def handle_endtag(self, tag):
        if tag == 'span' and self.recordingLatestVersionNumber:
            self.recordingLatestVersionNumber -= 1

    def handle_data(self, data):
        if self.recordingLatestVersionNumber:
            #self.data.append(data)
            self.latestVersionNumber = data.strip()

    def handle_comment(self,data):
        self.htmlComments += data.strip()



def destroy_dialog(dialog):
    wx.CallAfter(dialog.Hide)
    wx.CallAfter(dialog.Show, False)

    while True:
        try:
            if dialog is None: break

            time.sleep(0.01)
            wx.CallAfter(dialog.Destroy)
            wx.Yield()
        except AttributeError:
            break
        except wx._core.PyDeadObjectError:
            break

def seconds_to_hours_minutes(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return int(h), int(m)

def job_has_been_canceled(ssh_cmd, launcherMainFrame,job_id):
    """
    When a visnode job is canceled, a file of the form
    $HOME/.vnc/shutdown_${JOB_ID}.${NODE} is created, e.g.
    $HOME/.vnc/shutdown_1234567.m2-m. This function checks if
    a particular shutdown file exists.

    We do minimal error checking because this code is used just as
    the launcher exits.
    """

    try:
        return str(job_id) in run_ssh_command(ssh_cmd, 'ls ~/.vnc/shutdown_%d*' % (job_id,), launcherMainFrame,ignore_errors=True)[0]
    except:
        logger.debug(traceback.format_exc())
        return None

def remaining_visnode_walltime(launcherMainFrame):
    """
    Get the remaining walltime for the user's visnode job. We do
    minimal error checking because this code is used just as the user
    is exiting the launcher.
    """

    try:

        job_id = int(launcherMainFrame.loginThread.massiveJobNumber)

        if job_has_been_canceled(sshCmd.format(username=launcherMainFrame.massiveUsername,host=launcherMainFrame.massiveLoginHost), launcherMainFrame,job_id):
            return
        else:
            return seconds_to_hours_minutes(float(run_ssh_command(sshCmd.format(username=launcherMainFrame.massiveUsername,host=launcherMainFrame.massiveLoginHost), 'qstat -f %d | grep Remaining' % (job_id,), launcherMainFrame,ignore_errors=True)[0].split()[-1]))
    except:
        logger.debug(traceback.format_exc())
        return

def die_from_login_thread(launcherMainFrame,error_message, display_error_dialog=True, submit_log=False):
    if (launcherMainFrame.progressDialog != None):
        wx.CallAfter(launcherMainFrame.progressDialog.Hide)
        wx.CallAfter(launcherMainFrame.progressDialog.Show, False)
        wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
        launcherMainFrame.progressDialog = None

        while True:
            try:
                if launcherMainFrame.progressDialog is None: break

                time.sleep(0.01)
                wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
                wx.Yield()
            except AttributeError:
                break
            except wx._core.PyDeadObjectError:
                break

    launcherMainFrame.progressDialog = None
    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
    wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))

    if display_error_dialog:
        def error_dialog():
            dlg = wx.MessageDialog(launcherMainFrame, error_message,
                            "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
            launcherMainFrame.loginThread.die_from_login_thread_completed = True

        launcherMainFrame.loginThread.die_from_login_thread_completed = False

        wx.CallAfter(error_dialog)
        while not launcherMainFrame.loginThread.die_from_login_thread_completed:
            time.sleep(0.1)

    wx.CallAfter(launcherMainFrame.logWindow.Show, False)
    wx.CallAfter(launcherMainFrame.logTextCtrl.Clear)
    wx.CallAfter(launcherMainFrame.massiveShowDebugWindowCheckBox.SetValue, False)
    wx.CallAfter(launcherMainFrame.cvlShowDebugWindowCheckBox.SetValue, False)

    logger.dump_log(launcherMainFrame,submit_log=submit_log)

def die_from_main_frame(launcherMainFrame,error_message):
    if (launcherMainFrame.progressDialog != None):
        wx.CallAfter(launcherMainFrame.progressDialog.Destroy)
        launcherMainFrame.progressDialog = None
    wx.CallAfter(launcherMainFrame.loginDialogStatusBar.SetStatusText, "")
    wx.CallAfter(launcherMainFrame.SetCursor, wx.StockCursor(wx.CURSOR_ARROW))

    def error_dialog():
        dlg = wx.MessageDialog(launcherMainFrame, "Error: " + error_message + "\n\n" + "The launcher cannot continue.\n",
                        "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
#        launcherMainFrame.loginThread.die_from_main_frame_dialog_completed = True

#    launcherMainFrame.loginThread.die_from_main_frame_dialog_completed = False
    wx.CallAfter(error_dialog)
 
    while not launcherMainFrame.loginThread.die_from_main_frame_dialog_completed:
        time.sleep(0.1)
 
    logger.dump_log(launcherMainFrame,submit_log=True)
    os._exit(1)

def run_ssh_command(sshCmd,command,ignore_errors=False,log_output=True,callback=None):
    stdout=""
    stderr=""
    if command != None:
        logger.debug('run_ssh_command: %s' % sshCmd+command)
        logger.debug('   called from %s:%d' % inspect.stack()[1][1:3])
        ssh_process=subprocess.Popen(sshCmd+command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True,universal_newlines=True)

        #(stdout,stderr) = ssh_process.communicate(command)
        (stdout,stderr) = ssh_process.communicate()
        ssh_process.wait()
        if log_output:
            logger.debug('command stdout: %s' % stdout)
            logger.debug('command stderr: %s' % stderr)
        if not ignore_errors and len(stderr) > 0:
            error_message = 'Error running command: "%s" at line %d' % (command, inspect.stack()[1][2])
            logger.error('Nonempty stderr and ignore_errors == False; exiting the launcher with error dialog: ' + error_message)
            if (callback != None):
                callback(error_message)

    return stdout, stderr


def unzip(zipFilePath, destDir):

    zfile = zipfile.ZipFile(zipFilePath)

    for name in zfile.namelist():

        (dirName, fileName) = os.path.split(name)

        absoluteDirectoryPath = os.path.join(destDir, dirName)
        if not os.path.exists(absoluteDirectoryPath):
            os.mkdir(absoluteDirectoryPath)

        if fileName != '':
            fd = open(os.path.join(absoluteDirectoryPath, fileName), 'wb')
            fd.write(zfile.read(name))
            fd.close()

    zfile.close()
