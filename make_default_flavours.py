
from utilityFunctions import siteConfig,cmdRegEx
import sys

def buildSiteConfigCmdRegExDict(configName):
    import re
#    if sys.platform.startswith("win"):
#        lt = "^<"
#        gt = "^>"
#        pipe = "^|"
#    else:
#        lt = "<"
#        gt = ">"
#        pipe = "|"
    pipe = "|"
    siteConfigDict={}
    siteConfigDict['messageRegexs']=[re.compile("^INFO:(?P<info>.*(?:\n|\r\n?))",re.MULTILINE),re.compile("^WARN:(?P<warn>.*(?:\n|\r\n?))",re.MULTILINE),re.compile("^ERROR:(?P<error>.*(?:\n|\r\n?))",re.MULTILINE)]
    if ("m1" in configName or "m2" in configName):
        siteConfigDict['loginHost']="%s.massive.org.au"%configName
        siteConfigDict['listAll']=cmdRegEx('qstat -u {username}','^\s*(?P<jobid>(?P<jobidNumber>[0-9]+).\S+)\s+{username}\s+(?P<queue>\S+)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>[^C])\s+(?P<elapTime>\S+)\s*$',requireMatch=False)
        siteConfigDict['running']=cmdRegEx('qstat -u {username}','^\s*(?P<jobid>{jobid})\s+{username}\s+(?P<queue>\S+)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>R)\s+(?P<elapTime>\S+)\s*$')
        siteConfigDict['stop']=cmdRegEx('\'qdel -a {jobid}\'')
        siteConfigDict['stopForRestart']=cmdRegEx('qdel {jobid} ; sleep 5\'')
        siteConfigDict['execHost']=cmdRegEx('qpeek {jobidNumber}','\s*To access the desktop first create a secure tunnel to (?P<execHost>\S+)\s*$')
        siteConfigDict['startServer']=cmdRegEx("\'/usr/local/desktop/request_visnode.sh {project} {hours} {nodes} True False False\'","^(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s*$")
        siteConfigDict['runSanityCheck']=cmdRegEx("\'/usr/local/desktop/sanity_check.sh {launcher_version_number}\'")
        siteConfigDict['setDisplayResolution']=cmdRegEx("\'/usr/local/desktop/set_display_resolution.sh {resolution}\'")
        siteConfigDict['getProjects']=cmdRegEx('\"glsproject -A -q | grep \',{username},\|\s{username},\|,{username}\s\' \"','^(?P<group>\S+)\s+.*$')
        siteConfigDict['showStart']=cmdRegEx("showstart {jobid}","Estimated Rsv based start .*?on (?P<estimatedStart>.*)")
        siteConfigDict['vncDisplay']= cmdRegEx('"/usr/bin/ssh {execHost} \' module load turbovnc ; vncserver -list\'"','^(?P<vncDisplay>:[0-9]+)\s*(?P<vncPID>[0-9]+)\s*$')
        siteConfigDict['otp']= cmdRegEx('"/usr/bin/ssh {execHost} \' module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\'"','^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$')
        siteConfigDict['agent']=cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -l {username} {loginHost} \"/usr/bin/ssh -A {execHost} \\"echo agent_hello; bash \\"\"','agent_hello',async=True)
        siteConfigDict['tunnel']=cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=yes -L {localPortNumber}:{execHost}:{remotePortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"','tunnel_hello',async=True)

        cmd='"echo DBUS_SESSION_BUS_ADDRESS=dummy_dbus_session_bus_address"'
        regex='^DBUS_SESSION_BUS_ADDRESS=(?P<dbusSessionBusAddress>.*)$'
        siteConfigDict['dbusSessionBusAddress']=cmdRegEx(cmd,regex)

        cmd='\"/usr/local/desktop/get_ephemeral_port.py\"'
        regex='^(?P<intermediateWebDavPortNumber>[0-9]+)$'
        siteConfigDict['webDavIntermediatePort']=cmdRegEx(cmd,regex)

        cmd='\"/usr/bin/ssh {execHost} /usr/local/desktop/get_ephemeral_port.py\"'
        regex='^(?P<remoteWebDavPortNumber>[0-9]+)$'
        siteConfigDict['webDavRemotePort']=cmdRegEx(cmd,regex)

        #cmd='"/usr/bin/ssh {execHost} \'DISPLAY={vncDisplay} /usr/bin/konqueror webdav://{localUsername}:{vncPasswd}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName} && /usr/local/desktop/get_pid_of_active_window.sh\'"'
        #regex='^(?P<webDavKonquerorWindowPid>[0-9]+)$'
        #siteConfigDict['openWebDavShareInRemoteFileBrowser']=siteConfig.cmdRegEx(cmd,regex)
        cmd='"/usr/bin/ssh {execHost} \'DISPLAY={vncDisplay} /usr/bin/konqueror webdav://{localUsername}:{vncPasswd}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\'"'
        siteConfigDict['openWebDavShareInRemoteFileBrowser']=cmdRegEx(cmd)

#        cmd='"/usr/bin/ssh {execHost} \'echo -e \\"You can access your local home directory in Konqueror with the URL:%sbr%s\\nwebdav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}%sbr%s\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt; sleep 2; DISPLAY={vncDisplay} kdialog --title \\"MASSIVE/CVL Launcher\\" --textbox ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt 490 150\'"' % (lt,gt,lt,gt)
        cmd='"/usr/bin/ssh {execHost} \'echo -e \\"You can access your local home directory in Konqueror with the URL:%sbr%s\\nwebdav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}%sbr%s\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt;\'"'
        siteConfigDict['displayWebDavInfoDialogOnRemoteDesktop'] = cmdRegEx(cmd)

        # Chris trying to avoid using the intermediate port:
        #cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {execHost}:{remoteWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"'
        cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {intermediateWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "ssh -R {remoteWebDavPortNumber}:localhost:{intermediateWebDavPortNumber} {execHost} \'echo tunnel_hello; bash\'"'
        regex='tunnel_hello'
        siteConfigDict['webDavTunnel']=cmdRegEx(cmd,regex,async=True)

        cmd = '"/usr/bin/ssh {execHost} \'DISPLAY={vncDisplay} /usr/local/desktop/close_webdav_window.sh webdav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\'"'
        # Maybe call server-side script to do something like this:
        #for konq in `dcop konqueror-*`; do KONQPID=`echo $konq | tr '-' '\n' | tail -1`; if [ "`dcop $konq konqueror-mainwindow#1 currentTitle`" == 'webdav://wettenhj@localhost:56865/wettenhj' ]; then kill $KONQPID; fi; done

        siteConfigDict['webDavUnmount']=cmdRegEx(cmd)

        cmd='echo hello;exit'
        regex='hello'

    elif ('cvl' in configName or 'CVL' in configName or 'Huygens' in configName):
        siteConfigDict['loginHost']='login.cvl.massive.org.au'
        siteConfigDict['directConnect']=True
        cmd='\"module load pbs ; qstat -f {jobidNumber} | grep exec_host | sed \'s/\ \ */\ /g\' | cut -f 4 -d \' \' | cut -f 1 -d \'/\' | xargs -iname hostn name | grep address | sed \'s/\ \ */\ /g\' | cut -f 3 -d \' \' | xargs -iip echo execHost ip; qstat -f {jobidNumber}\"'
        regex='^\s*execHost (?P<execHost>\S+)\s*$'
        siteConfigDict['execHost'] = cmdRegEx(cmd,regex)
        cmd='\"groups | sed \'s@ @\\n@g\'\"' # '\'groups | sed \'s\/\\\\ \/\\\\\\\\n\/g\'\''
        regex='^\s*(?P<group>\S+)\s*$'
        siteConfigDict['getProjects'] = cmdRegEx(cmd,regex)
        if ("Huygens" in configName):
            siteConfigDict['listAll']=cmdRegEx('\"module load pbs ; qstat -u {username} | tail -n +6\"','^\s*(?P<jobid>(?P<jobidNumber>[0-9]+).\S+)\s+{username}\s+(?P<queue>huygens)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>[^C])\s+(?P<elapTime>\S+)\s*$',requireMatch=False)
        else:
            siteConfigDict['listAll']=cmdRegEx('\"module load pbs ; qstat -u {username} | tail -n +6\"','^\s*(?P<jobid>(?P<jobidNumber>[0-9]+).\S+)\s+{username}\s+(?P<queue>batch)\s+(?P<jobname>desktop_\S+)\s+(?P<sessionID>\S+)\s+(?P<nodes>\S+)\s+(?P<tasks>\S+)\s+(?P<mem>\S+)\s+(?P<reqTime>\S+)\s+(?P<state>[^C])\s+(?P<elapTime>\S+)\s*$',requireMatch=False)
        cmd='\"module load pbs ; module load maui ; qstat | grep {username}\"'
        regex='^\s*(?P<jobid>{jobidNumber}\.\S+)\s+(?P<jobname>desktop_\S+)\s+{username}\s+(?P<elapTime>\S+)\s+(?P<state>R)\s+(?P<queue>\S+)\s*$'
        siteConfigDict['running']=cmdRegEx(cmd,regex)
        if ("Huygens" in configName):
            cmd="\"module load pbs ; module load maui ; echo \'module load pbs ; /usr/local/bin/vncsession --vnc turbovnc --geometry {resolution} ; sleep {wallseconds}\' |  qsub -q huygens -l nodes=1:ppn=1 -N desktop_{username} -o .vnc/ -e .vnc/\""
        else:
            cmd="\"module load pbs ; module load maui ; echo \'module load pbs ; /usr/local/bin/vncsession --vnc turbovnc --geometry {resolution} ; sleep {wallseconds}\' |  qsub -l nodes=1:ppn=1,walltime={wallseconds} -N desktop_{username} -o .vnc/ -e .vnc/\""
        regex="^(?P<jobid>(?P<jobidNumber>[0-9]+)\.\S+)\s*$"
        siteConfigDict['startServer']=cmdRegEx(cmd,regex)
        siteConfigDict['stop']=cmdRegEx('\"module load pbs ; module load maui ; qdel -a {jobidNumber}\"')
        #siteConfigDict['vncDisplay']= cmdRegEx('" /usr/bin/ssh {execHost} \' cat /var/spool/torque/spool/{jobidNumber}.*\'"' ,'^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$')
        siteConfigDict['vncDisplay']= cmdRegEx('\"cat /var/spool/torque/spool/{jobidNumber}.*\"' ,'^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$',host='exec')
        cmd= '\"module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\"'
        regex='^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$'
        siteConfigDict['otp']=cmdRegEx(cmd,regex,host='exec')
        siteConfigDict['agent']=cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -l {username} {execHost} "echo agent_hello; bash "','agent_hello',async=True)
        siteConfigDict['tunnel']=cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -L {localPortNumber}:localhost:{remotePortNumber} -l {username} {execHost} "echo tunnel_hello; bash"','tunnel_hello',async=True)

        cmd='"/usr/bin/ssh {execHost} \'MACHINE_ID=\\$(cat /var/lib/dbus/machine-id); cat ~/.dbus/session-bus/\\$MACHINE_ID-\\$(echo {vncDisplay} | tr -d \\":\\" | tr -d \\".0\\")\'"'
        regex='^DBUS_SESSION_BUS_ADDRESS=(?P<dbusSessionBusAddress>.*)$'
        siteConfigDict['dbusSessionBusAddress']=cmdRegEx(cmd,regex)

        cmd='\"/usr/local/bin/get_ephemeral_port.py\"'
        regex='^(?P<intermediateWebDavPortNumber>[0-9]+)$'
        siteConfigDict['webDavIntermediatePort']=cmdRegEx(cmd,regex,host='exec')

        cmd='\"/usr/local/bin/get_ephemeral_port.py\"'
        regex='^(?P<remoteWebDavPortNumber>[0-9]+)$'
        siteConfigDict['webDavRemotePort']=cmdRegEx(cmd,regex,host='exec')

        # Below, I initially tried to respect the user's Nautilus setting of always_use_location_entry and change it back after launching Nautilus,
        # but doing so changes this setting in already-running Nautilus windows, and I want the user to see Nautilus's location bar when showing 
        # them the WebDav share.  So now, I just brutally change the user's Nautilus location-bar setting to always_use_location_entry.
        # Note that we might end up mounting WebDAV in a completely different way (e.g. using wdfs), but for now I'm trying to make the user
        # experience similar on MASSIVE and the CVL.  On MASSIVE, users are not automatically added to the "fuse" group, but they can still 
        # access a WebDAV share within Konqueror.  The method below for the CVL/Nautilus does require fuse membership, but it ends up looking
        # similar to MASSIVE/Konqueror from the user's point of view.  
        cmd="\"/usr/bin/ssh {execHost} \\\"export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};echo \\\\\\\"import pexpect;child = pexpect.spawn('gvfs-mount dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}');child.expect('Password: ');child.sendline('{vncPasswd}')\\\\\\\" %s python;/usr/bin/gconftool-2 --type=Boolean --set /apps/nautilus/preferences/always_use_location_entry true;DISPLAY={vncDisplay} /usr/bin/nautilus --no-desktop --sm-disable dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName};\\\"\"" % (pipe)
        siteConfigDict['openWebDavShareInRemoteFileBrowser']=cmdRegEx(cmd)

        #cmd = '"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:8080/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" | DISPLAY={vncDisplay} zenity --title \\"MASSIVE/CVL Launcher\\" --text-info --width 490 --height 175\'"'
        cmd = '"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:8080/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt\'"'
        siteConfigDict['displayWebDavInfoDialogOnRemoteDesktop']=cmdRegEx(cmd)

        cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {remoteWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {execHost} "echo tunnel_hello; bash"'
        regex='tunnel_hello'
        siteConfigDict['webDavTunnel']=cmdRegEx(cmd,regex,async=True)

        # 1. Due to a bug in gvfs-mount, I'm using timeout, so it doesn't matter if "gvfs-mount -u" never exits.
        # 2. I'm using gvfs-mount --unmount-scheme dav for now, to unmount all GVFS WebDAV mounts,
        #    because otherwise it's too painful to refer to the specific mount point at "$HOME/.gvfs/WebDAV on localhost",
        #    because the $HOME environment variable could be evaluated in the wrong shell.
        # 3. The wmctrl command to close the Nautilus window doesn't seem to work from the Launcher,
        #    even though it seems to work fine when I run paste the command used by the Launcher's
        #    subprocess into a Terminal window.  Maybe I should use the same method I'm using for
        #    Konqueror instead (which is a server-side script).
        # 4. Occassionally the DBUS_SESSION_BUS_ADDRESS environment variable gets out of sync with
        #    ~/.dbus/session-bus/$MACHINE_ID-$DISPLAY which causes gvfs-mount etc. to fail.
        #cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};DISPLAY={vncDisplay} wmctrl -F -c \"{homeDirectoryWebDavShareName} - File Browser\"; DISPLAY={vncDisplay} timeout 3 gvfs-mount -u \"$HOME/.gvfs/WebDAV on localhost\"\'"'
        cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};DISPLAY={vncDisplay} wmctrl -F -c \"{homeDirectoryWebDavShareName} - File Browser\"; DISPLAY={vncDisplay} timeout 3 gvfs-mount --unmount-scheme dav\'"'
        siteConfigDict['webDavUnmount']=cmdRegEx(cmd)
    else:
        siteConfigDict['loginHost']=configName
        siteConfigDict['listAll']=cmdRegEx('\'module load turbovnc ; vncserver -list\'','^(?P<vncDisplay>:[0-9]+)\s+[0-9]+\s*$',requireMatch=False)
        siteConfigDict['startServer']=cmdRegEx('\"/usr/local/bin/vncsession --vnc turbovnc --geometry {resolution}\"','^.*?started on display \S+(?P<vncDisplay>:[0-9]+)\s*$')
        siteConfigDict['stop']=cmdRegEx('\'module load turbovnc ; vncserver -kill {vncDisplay}\'')
        siteConfigDict['otp']= cmdRegEx('\'module load turbovnc ; vncpasswd -o -display localhost{vncDisplay}\'','^\s*Full control one-time password: (?P<vncPasswd>[0-9]+)\s*$')
        siteConfigDict['agent']=cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -l {username} {loginHost} "echo agent_hello; bash "','agent_hello',async=True)
        siteConfigDict['tunnel']=cmdRegEx('{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -L {localPortNumber}:localhost:{remotePortNumber} -l {username} {loginHost} "echo tunnel_hello; bash"','tunnel_hello',async=True)

        cmd='"/usr/bin/ssh {execHost} \'MACHINE_ID=\\$(cat /var/lib/dbus/machine-id); cat ~/.dbus/session-bus/\\$MACHINE_ID-\\$(echo {vncDisplay} | tr -d \\":\\" | tr -d \\".0\\")\'"'
        regex='^DBUS_SESSION_BUS_ADDRESS=(?P<dbusSessionBusAddress>.*)$'
        siteConfigDict['dbusSessionBusAddress']=cmdRegEx(cmd,regex)

        cmd='{sshBinary} -A -c {cipher} -t -t -oStrictHostKeyChecking=no -oExitOnForwardFailure=yes -R {intermediateWebDavPortNumber}:localhost:{localWebDavPortNumber} -l {username} {loginHost} "ssh -R {remoteWebDavPortNumber}:localhost:{intermediateWebDavPortNumber} {execHost} \'echo tunnel_hello; bash\'"'
        regex='tunnel_hello'
        siteConfigDict['webDavTunnel']=cmdRegEx(cmd,regex,async=True)

        cmd="\"/usr/bin/ssh {execHost} \\\"export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};echo \\\\\\\"import pexpect;child = pexpect.spawn('gvfs-mount dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}');child.expect('Password: ');child.sendline('{vncPasswd}')\\\\\\\" %s python;/usr/bin/gconftool-2 --type=Boolean --set /apps/nautilus/preferences/always_use_location_entry true;DISPLAY={vncDisplay} /usr/bin/nautilus --no-desktop --sm-disable dav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName};\\\"\"" % (pipe)
        siteConfigDict['openWebDavShareInRemoteFileBrowser']=cmdRegEx(cmd)

        #cmd = '"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" | DISPLAY={vncDisplay} zenity --title \\"MASSIVE/CVL Launcher\\" --text-info --width 490 --height 175\'"'
        cmd = '"/usr/bin/ssh {execHost} \'sleep 2;echo -e \\"You can access your local home directory in Nautilus File Browser, using the location:\\n\\ndav://{localUsername}@localhost:{remoteWebDavPortNumber}/{homeDirectoryWebDavShareName}\\n\\nYour one-time password is {vncPasswd}\\" > ~/.vnc/\\$HOSTNAME\\$DISPLAY-webdav.txt\'"'
        siteConfigDict['displayWebDavInfoDialogOnRemoteDesktop']=cmdRegEx(cmd)

        # 1. Due to a bug in gvfs-mount, I'm using timeout, so it doesn't matter if "gvfs-mount -u" never exits.
        # 2. I'm using gvfs-mount --unmount-scheme dav for now, to unmount all GVFS WebDAV mounts,
        #    because otherwise it's too painful to refer to the specific mount point at "$HOME/.gvfs/WebDAV on localhost",
        #    because the $HOME environment variable could be evaluated in the wrong shell.
        # 3. The wmctrl command to close the Nautilus window doesn't seem to work from the Launcher,
        #    even though it seems to work fine when I run paste the command used by the Launcher's
        #    subprocess into a Terminal window.  Maybe I should use the same method I'm using for
        #    Konqueror instead (which is a server-side script).
        # 4. Occassionally the DBUS_SESSION_BUS_ADDRESS environment variable gets out of sync with
        #    ~/.dbus/session-bus/$MACHINE_ID-$DISPLAY which causes gvfs-mount etc. to fail.
        #cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};DISPLAY={vncDisplay} wmctrl -F -c \"{homeDirectoryWebDavShareName} - File Browser\"; DISPLAY={vncDisplay} timeout 3 gvfs-mount -u \"$HOME/.gvfs/WebDAV on localhost\"\'"'
        cmd = '"/usr/bin/ssh {execHost} \'export DBUS_SESSION_BUS_ADDRESS={dbusSessionBusAddress};DISPLAY={vncDisplay} wmctrl -F -c \"{homeDirectoryWebDavShareName} - File Browser\"; DISPLAY={vncDisplay} timeout 3 gvfs-mount --unmount-scheme dav\'"'
        siteConfigDict['webDavUnmount']=cmdRegEx(cmd)








    return siteConfigDict

massivevisible={}
massivevisible['usernamePanel']=True
massivevisible['projectPanel']=True
massivevisible['resourcePanel']=True
massivevisible['resolutionPanel']='Advanced'
massivevisible['cipherPanel']='Advanced'
massivevisible['debugCheckBoxPanel']='Advanced'
massivevisible['advancedCheckBoxPanel']=True
massivevisible['optionsDialog']=False
cvlvisible={}
cvlvisible['usernamePanel']=True
cvlvisible['projectPanel']=False
cvlvisible['resourcePanel']='Advanced'
cvlvisible['resolutionPanel']='Advanced'
cvlvisible['cipherPanel']='Advanced'
cvlvisible['debugCheckBoxPanel']='Advanced'
cvlvisible['advancedCheckBoxPanel']=True
cvlvisible['optionsDialog']=False

m1=siteConfig()
d=buildSiteConfigCmdRegExDict("m1")
m1.__dict__.update(d)
m1.visibility=massivevisible

m2=siteConfig()
d=buildSiteConfigCmdRegExDict("m2")
m2.__dict__.update(d)
m2.visibility=massivevisible

cvl=siteConfig()
d=buildSiteConfigCmdRegExDict("cvl")
cvl.__dict__.update(d)
cvl.visibility=cvlvisible

huygens=siteConfig()
d=buildSiteConfigCmdRegExDict("Huygens")
huygens.__dict__.update(d)
huygens.visibility=cvlvisible

defaultSites={}

defaultSites['Desktop on m1.massive.org.au']  = m1
defaultSites['Desktop on m2.massive.org.au']  = m2 
defaultSites['CVL Desktop']  = cvl
defaultSites['Huygens on the CVL']  = huygens
import utilityFunctions
import json
json=json.dumps(defaultSites,cls=utilityFunctions.GenericJSONEncoder,sort_keys=True,indent=4,separators=(',', ': '))
#json=utilityFunctions.GenericJSONEncoder().encode(defaultSites)
print json


