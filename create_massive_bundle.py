"""
A distutils script to make a standalone .app of MASSIVE for
Mac OS X.  You can get py2app from http://undefined.org/python/py2app.
Use this command to build the .app and collect the other needed files:

   python create_massive_bundle.py py2app

Traditionally, this script would be named setup.py
"""

from setuptools import setup
import sys

import massive_launcher_version_number

if sys.platform == 'darwin':
    buildstyle = 'app'
elif sys.platform == 'win32':
    import py2exe
    # buildstyle = 'console'
    buildstyle = 'windows'

setup(
    options=dict(py2app=dict(
        #plist='MASSIVE_Info.plist'
        plist=dict(
            CFBundleDevelopmentRegion="English",
            CFBundleDisplayName="MASSIVE",
            CFBundleExecutable="MASSIVE",
            CFBundleIconFile="MASSIVE.icns",
            CFBundleIdentifier="au.edu.monash.MASSIVE",
            CFBundleName="MASSIVE",
            CFBundlePackageType="APPL",
            CFBundleVersion="Version " + massive_launcher_version_number.version_number
            )
        )
    ),
    data_files=["MASSIVE.icns"],
    name="MASSIVE",
    setup_requires=["py2app"],
    #**{buildstyle : ['massive.py']}
    app=['massive.py']
)
