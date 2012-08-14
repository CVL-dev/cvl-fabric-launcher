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

# Adapted from C:\Python27\Lib\site-packages\py2exe\samples\simple\setup.py

# Run the build process by running
#
# 'python create_windows_bundle.py py2exe' in a console prompt.
#
# This script would traditionally be named 'setup.py'.
#
# If everything works well, you should find a subdirectory named 'dist'
# containing some files, including an exe file and some DLLs.

from distutils.core import setup, Extension
import py2exe

# THE ssh_tunnel MODULE IS NOT CURRENTLY USED. 
# ITS IMPLEMENTATION IS INCOMPLETE AND IT DOESN'T WORK IN ITS CURRENT FORM.
# IT HAS BEEN REPLACED BY CALLS TO EXTERNAL SSH PROCESSES
# (ssh on Mac, Linux and plink.exe on Windows).

#ssh_tunnel_module = Extension("ssh_tunnel", 
    #sources = ["ssh_tunnel_module.c"],
    #extra_compile_args = ['-O3'],
    #libraries = ['ssh2'])

import launcher_version_number

setup(
    name = "MASSIVE Launcher",
    description = "MASSIVE Launcher",
    version = launcher_version_number.version_number,
    windows = [
        {
            "script": "launcher.py",
            "icon_resources": [(1, "massive.ico")],
            "dest_base": "MASSIVE Launcher"
        }
    ]
    #,ext_modules = [ssh_tunnel_module]
    )
