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
import glob

import launcher_version_number

data_files = [("Microsoft.VC90.CRT", glob.glob(r'C:\WINDOWS\WinSxS\Manifests\x86_Microsoft.VC90.CRT_1fc8b3b9a1e18e3b_9.0.21022.8_x-ww_d08d0375.manifest') + glob.glob(r'C:\WINDOWS\WinSxS\x86_Microsoft.VC90.CRT_1fc8b3b9a1e18e3b_9.0.21022.8_x-ww_d08d0375\*.dll'))]

setup(
    name = "MASSIVE Launcher",
    data_files=data_files,
    description = "MASSIVE Launcher",
    version = launcher_version_number.version_number,
    windows = [
        {
            "script": "launcher.py",
            "icon_resources": [(1, "massive.ico")],
            "dest_base": "MASSIVE Launcher"
        }
    ]
    )
