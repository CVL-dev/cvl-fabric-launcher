import json
import sys
import collections
import requests
from logger.Logger import logger

def getSites(prefs):
    logger.debug("getting a list of sites")
    siteList=[]
    if prefs.has_section('configured_sites'):
        l=prefs.options('configured_sites')
        for s in l:
            if 'sitename' in s:
                site=prefs.get('configured_sites',s)
                number=int(s[8:])
                enabled=prefs.get('configured_sites','siteenabled%i'%number)
                if enabled=='True':
                    siteList.append(site)

    r=collections.OrderedDict()
    for site in siteList:
        logger.debug("retrieving the config for %s"%site)
        try:
            req=requests.get(site,verify=False)
            if req.status_code == 200:
                newSites=GenericJSONDecoder().decode(req.text)
                if (isinstance(newSites,list)):
                    keyorder=newSites[0]
                    for key in keyorder:
                        r[key]=newSites[1][key]
        except Exception as e:
            logger.debug("error retrieving the config for %s"%site)
            logger.debug("%s"%e)
    return r
        
        

#    DEFAULT_SITES_JSON='defaultSites.json'
#    defaultSites={}
#    with open(DEFAULT_SITES_JSON,'r') as f:
#        defaultSites=GenericJSONDecoder().decode(f.read())
#    if (isinstance(defaultSites,list)):
#        keyorder=defaultSites[0]
#        r=collections.OrderedDict()
#        for key in keyorder:
#            r[key]=defaultSites[1][key]
#        defaultSites=r
#    return defaultSites

class sshKeyDistDisplayStrings(object):
    def __init__(self,**kwargs):
        self.passwdPrompt="enter passwd"
        self.passwdPromptIncorrect="passwd incorrect. reenter"
        self.passphrasePrompt="enter key passphrase"
        self.passphrasePromptIncorrectl="Incorrect. enter key passphrase"
        self.newPassphraseEmptyForbidden="new passphrase. empty passphrase forbidden"
        self.newPassphraseTooShort="passphrase to short. enter a new passphrase"
        self.newPassphraseMismatch="passphrases don't match. enter new passphrases"
        self.newPassphrase="new passphrase for new key"
        self.newPassphraseTitle="Please enter a new passphrase"
        self.temporaryKey="""
Would you like to use the launchers old behaviour (entering a password every time you start a new desktop) or try the new behaviour (creating an ssh key pair and entering a passphrase the first time you use the launcher after reboot.)

Passwords are recomended if this is a shared user account.

SSH Keys are recommended if you are the only person who uses this account.

This option can be changed from the Identity menu.
"""
        self.temporaryKeyYes="Use my password every time"
        self.temporaryKeyNo="Use my SSH Key"
        self.qdelQueuedJob="""It looks like you've been waiting for a job to start.
Do you want me to delete the job or leave it in the queue so you can reconnect later?
"""
        self.qdelQueuedJobQdel="Delete the job"
        self.qdelQueuedJobNOOP="Leave it in the queue (I'll reconnect later)"
        self.persistentMessage="Would you like to leave your current session running so that you can reconnect later?\nIt has {timestring} remaining."
        self.persistentMessageStop="Stop the desktop"
        self.persistentMessagePersist="Leave it running"
        self.reconnectMessage="An Existing Desktop was found. It has {timestring} remaining. Would you like to reconnect or kill it and start a new desktop?"
        self.reconnectMessageYes="Reconnect"
        self.reconnectMessageNo="New desktop"
        self.createNewKeyDialogNewPassphraseMismatch="Passphrases don't match"
        self.helpEmailAddress="help@massive.org.au"
        for key,value in kwargs.iteritems():
            self.__dict__[key]=value

# JSON Encoder and Decoder based on
# http://broadcast.oreilly.com/2009/05/pymotw-json.html
# json - JavaScript Object Notation Serializer
# By Doug Hellmann
# May 24, 2009
# Compiled regular expressions don't seem to conform to the "normal" pattern of having an obj.__class__.__name__ and obj.__module__
# Thus I have added specical case handling for regular expressions -- Chris Hines

class GenericJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        import re
        if isinstance(obj,type(re.compile(''))):
            d={'__class__':'__regex__','pattern':obj.pattern}
        else:
            d = { '__class__':obj.__class__.__name__, '__module__':obj.__module__, }
            d.update(obj.__dict__)
        return d

class GenericJSONDecoder(json.JSONDecoder):
    
    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=self.dict_to_object)

    def dict_to_object(self, d):
        if '__class__' in d:
            class_name = d.pop('__class__')
            if class_name == '__regex__':
                import re
                pattern=d.pop('pattern')
                return re.compile(pattern)
            module_name = d.pop('__module__')
            module = __import__(module_name)
            class_ = getattr(module, class_name)
            args = dict( (key.encode('ascii'), value) for key, value in d.items())
            try:
                inst = class_(**args)
            except Exception as e:
                print(class_name)
                print(args)
                raise e
        else:
            inst = d
        return inst

class cmdRegEx():
    def __init__(self,cmd=None,regex=None,requireMatch=True,loop=False,async=False,host='login',failFatal=True):

        self.cmd=cmd
        if (not isinstance(regex,list)):
            self.regex=[regex]
        else:
            self.regex=regex
        self.loop=loop
        self.async=async
        self.requireMatch=requireMatch
        if regex==None:
            self.requireMatch=False
        self.host=host
        if (self.async):
            self.host='local'
        self.failFatal=failFatal

    def windowsEscape(cmd):
        return cmd.replace('&','^&').replace('|','^|')

    def getCmd(self,jobParam={}):
        if ('exec' in self.host):
            sshCmd = '{sshBinary} -A -T -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o StrictHostKeyChecking=no -l {username} {execHost} '
        elif ('local' in self.host):
            sshCmd = ''
        else:
            sshCmd = '{sshBinary} -A -T -o PasswordAuthentication=no -o PubkeyAuthentication=yes -o StrictHostKeyChecking=yes -l {username} {loginHost} '
        cmd=self.cmd
        if sys.platform.startswith("win"):
            escapedChars={'ampersand':'^&','pipe':'^|'}
        else:
            escapedChars={'ampersand':'&','pipe':'|'}
        formatdict = jobParam.copy()
        formatdict.update(escapedChars)
        string=sshCmd.format(**formatdict).encode('ascii')+cmd.format(**formatdict).encode('ascii')
        return string


class siteConfig():
        
    def __init__(self,**kwargs):
        self.loginHost=None
        self.listAll=cmdRegEx(failFatal=False)
        self.running=cmdRegEx()
        self.stop=cmdRegEx(failFatal=False)
        self.stopForRestart=cmdRegEx(failFatal=False)
        self.execHost=cmdRegEx()
        self.startServer=cmdRegEx()
        self.runSanityCheck=cmdRegEx(failFatal=False)
        self.setDisplayResolution=cmdRegEx(failFatal=False)
        self.getProjects=cmdRegEx(failFatal=False)
        self.showStart=cmdRegEx(failFatal=False)
        self.vncDisplay=cmdRegEx()
        self.otp=cmdRegEx()
        self.directConnect=cmdRegEx()
        self.messageRegexs=[]
        self.webDavIntermediatePort=cmdRegEx(failFatal=False)
        self.webDavRemotePort=cmdRegEx(failFatal=False)
        self.openWebDavShareInRemoteFileBrowser=cmdRegEx(failFatal=False)
        self.displayWebDavInfoDialogOnRemoteDesktop=cmdRegEx(failFatal=False)
        self.webDavTunnel=cmdRegEx(failFatal=False)
        self.onConnectScript=cmdRegEx(failFatal=False)
        self.agent=cmdRegEx()
        self.tunnel=cmdRegEx()
        self.visibility={}
        self.displayStrings=sshKeyDistDisplayStrings()
        for key,value in kwargs.iteritems():
            self.__dict__[key]=value
