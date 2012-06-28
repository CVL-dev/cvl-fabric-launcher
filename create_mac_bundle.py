"""
A distutils script to make a standalone .app of the MASSIVE Launcher for
Mac OS X.  You can get py2app from http://undefined.org/python/py2app.
Use this command to build the .app and collect the other needed files:

   python create_mac_bundle.py py2app

Traditionally, this script would be named setup.py
"""

from setuptools import setup
import sys

import massive_launcher_version_number

setup(
    options=dict(py2app=dict(
        plist=dict(
            CFBundleDevelopmentRegion="English",
            CFBundleDisplayName="MASSIVE Launcher",
            CFBundleExecutable="MASSIVE Launcher",
            CFBundleIconFile="MASSIVE.icns",
            CFBundleIdentifier="au.edu.monash.MASSIVE",
            CFBundleName="MASSIVE Launcher",
            CFBundlePackageType="APPL",
            CFBundleVersion="Version " + massive_launcher_version_number.version_number
            )
        )
    ),
    data_files=["MASSIVE.icns"],
    name="MASSIVE Launcher",
    setup_requires=["py2app"],
    app=['massive.py']
)
