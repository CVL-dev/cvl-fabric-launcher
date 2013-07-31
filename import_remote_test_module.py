import tempfile
import requests
import traceback
try:
    # Download test.py

    testModuleFile = tempfile.NamedTemporaryFile(mode='w+b', prefix='test', suffix='.py', delete=False)
    testModuleFilePath = testModuleFile.name
    print "testModuleFilePath = " + testModuleFilePath
    r = requests.get("https://raw.github.com/CVL-dev/cvl-fabric-launcher/JamesJuly30/test.py", verify=False)
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
    importCommand = "import %s" % (testModuleName)
    print "importCommand:  %s" % (importCommand)
    exec importCommand
except:
    print "Failed to download remote test.py module."
    print str(traceback.format_exc())

