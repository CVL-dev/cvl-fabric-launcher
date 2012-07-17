"""
A distutils script to make a standalone .app of the MASSIVE Launcher for
Mac OS X.  You can get py2app from http://undefined.org/python/py2app.
Use this command to build the .app and collect the other needed files:

   python create_mac_bundle.py py2app

Traditionally, this script would be named setup.py
"""

from setuptools import setup, Extension

import massive_launcher_version_number

# THE ssh_tunnel MODULE IS NOT CURRENTLY USED. 
# ITS IMPLEMENTATION IS INCOMPLETE AND IT DOESN'T WORK IN ITS CURRENT FORM.
# IT HAS BEEN REPLACED BY CALLS TO EXTERNAL SSH PROCESSES
# (ssh on Mac, Linux and plink.exe on Windows).

#ssh_tunnel_module = Extension("ssh_tunnel", 
    #sources = ["ssh_tunnel_module.c"],
    #extra_compile_args = ['-O3'],
    #libraries = ['ssh2'])

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
    #,ext_modules = [ssh_tunnel_module]
)
