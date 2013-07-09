#HelpController.py

import wx.html
import tempfile
import requests
import traceback
import pkgutil
from utilityFunctions import logger_debug, unzip

#helpController.DisplayContents()
#helpController.Display("MASSIVE/CVL Launcher")
#helpController.Display("SSH Keys")

launcherHtmlHelpProjectFilename = "launcher.hhp"

class HelpController(wx.html.HtmlHelpController):

    def __init__(self):

        self.helpZipFile = None
        self.helpZipFilePath = None
        self.helpZipFileDirectory = None
        self.helpFilesDirectory = None

        #self.launcherHelpUrl = "https://cvl.massive.org.au/launcher_files/help/helpfiles.zip"
        self.launcherHelpUrl = "https://raw.github.com/CVL-dev/cvl-fabric-launcher/master/help/helpfiles.zip"
        self.initializationSucceeded = False
        try:
            # Download helpfiles.zip:

            self.helpZipFile = tempfile.NamedTemporaryFile(mode='w+b', prefix='helpfiles-', suffix='.zip', delete=False)
            self.helpZipFilePath = self.helpZipFile.name
            logger_debug("self.helpZipFilePath = " + self.helpZipFilePath)
            r = requests.get(launcherHelpUrl)
            if r.status_code == 200:
                for chunk in r.iter_content():
                    self.helpZipFile.write(chunk)
            self.helpZipFile.close()

            # We should be able to add the zip archive directly to the 
            # help controller, but that didn't seem to work.

            # Unzip helpfiles.zip:

            (self.helpZipFileDirectory, self.helpZipFileFilename) = os.path.split(self.helpZipFilePath)
            unzip(self.helpZipFilePath, self.helpZipFileDirectory)
            self.helpFilesDirectory = os.path.join(self.helpZipFileDirectory, "helpfiles")
            logger_debug("self.helpFilesDirectory = " + self.helpFilesDirectory)

            self.launcherHtmlHelpProjectFile = os.path.join(self.helpFilesDirectory, launcherHtmlHelpProjectFilename)
            self.initializationSucceeded = helpController.AddBook(self.launcherHtmlHelpProjectFile)

        except:
            logger_debug(traceback.format_exc())

            try:
                # If we don't succeed in downloading help, 
                # we will try using local help files instead.

                if hasattr(sys, 'frozen'):
                    self.helpFilesDirectory = os.path.join(os.path.dirname(sys.executable), "help", "helpfiles")
                else:
                    launcherModulePath = os.path.dirname(pkgutil.get_loader("launcher").filename)
                    self.helpFilesDirectory = os.path.join(launcherModulePath, "help", "helpfiles")

                self.launcherHtmlHelpProjectFile = os.path.join(self.helpFilesDirectory, launcherHtmlHelpProjectFilename)
                self.initializationSucceeded = helpController.AddBook(self.launcherHtmlHelpProjectFile)

            except:
                logger_debug(traceback.format_exc())


    def cleanUp(self):
        if self.helpZipFilePath is not None:
            os.remove(self.helpZipFilePath)
        if self.helpFilesDirectory is not None
            for helpFile in os.listdir(self.helpFilesDirectory):
                os.remove(os.path.join(self.helpFilesDirectory,helpFile))
            os.remove(self.helpFilesDirectory)

helpController = HelpController()

