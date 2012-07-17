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

import massive_launcher_version_number

setup(
    name = "MASSIVE Launcher",
    description = "MASSIVE Launcher",
    version = massive_launcher_version_number.version_number,
    windows = [
        {
            "script": "massive.py",
            "icon_resources": [(1, "massive.ico")],
            "dest_base": "MASSIVE Launcher"
        }
    ]
    #,ext_modules = [ssh_tunnel_module]
    )
