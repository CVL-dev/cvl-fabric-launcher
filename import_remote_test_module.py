#!/usr/bin/python

"""
This is a proof of concept for downloading a Python module from GitHub, saving it as a temporary
file and importing it.  Putting some of the Launcher's Python code on a server (like GitHub)
would allow Launcher admins to make changes without having to build and release a new version
of the Launcher.
"""

import tempfile
import requests
import traceback

# Hack from http://stackoverflow.com/questions/12522844/change-character-set-for-tempfile-namedtemporaryfile
# to ensure that the temporary Python module filename only contains characters which are legal for
# Python module names.
class MyRandomSequence(tempfile._RandomNameSequence):
    import string
    characters = string.letters
tempfile._name_sequence = MyRandomSequence()

try:
    # Download test.py

    testModuleFile = tempfile.NamedTemporaryFile(mode='w+b', prefix='test_module_for_remote_importing_', suffix='.py', delete=False)
    testModuleFilePath = testModuleFile.name
    print "testModuleFilePath = " + testModuleFilePath
    r = requests.get("https://raw.github.com/CVL-dev/cvl-fabric-launcher/master/test_module_for_remote_importing.py", verify=False)
    if r.status_code == 200:
        for chunk in r.iter_content():
            testModuleFile.write(chunk)
    testModuleFile.close()

    import sys
    import os
    (testModuleDirectory, testModuleFileName) = os.path.split(testModuleFile.name)
    sys.path.append(testModuleDirectory)
    print "testModuleFileName = " + testModuleFileName
    testModuleName = testModuleFileName.split(".")[0]
    print "testModuleName = " + testModuleName
    importCommand = "import " + testModuleName
    print "importCommand: " + importCommand
    exec importCommand
except:
    print "Failed to download remote test.py module."
    print str(traceback.format_exc())

