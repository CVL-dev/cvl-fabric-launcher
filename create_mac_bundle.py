#  MASSIVE/CVL Launcher - easy secure login for the MASSIVE Desktop and the CVL
#  Copyright (C) 2012  James Wettenhall, Monash University
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  Enquires: James.Wettenhall@monash.edu or help@massive.org.au

"""
A distutils script to make a standalone .app of the MASSIVE Launcher for
Mac OS X.  You can get py2app from http://undefined.org/python/py2app.
Use this command to build the .app and collect the other needed files:

   python create_mac_bundle.py py2app

Traditionally, this script would be named setup.py
"""

from setuptools import setup, Extension

import launcher_version_number

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
            CFBundleVersion="Version " + launcher_version_number.version_number
            )
        )
    ),
    data_files=["MASSIVE.icns"],
    name="MASSIVE Launcher",
    setup_requires=["py2app"],
    app=['launcher.py']
    #,ext_modules = [ssh_tunnel_module]
)
