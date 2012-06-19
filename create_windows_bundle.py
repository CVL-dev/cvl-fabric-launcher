# Adapted from C:\Python27\Lib\site-packages\py2exe\samples\simple\setup.py

# Run the build process by running
# 'python create_windows_bundle.py py2exe' in a console prompt.
#
# This script would traditionally be named 'setup.py'.
#
# If everything works well, you should find a subdirectory named 'dist'
# containing some files, including an exe file and some DLLs.

from distutils.core import setup
import py2exe

import massive_launcher_version_number

setup(
    # The first three parameters are not required, if at least a
    # 'version' is given, then a versioninfo resource is built from
    # them and added to the executables.
    version = massive_launcher_version_number.version_number,
    description = "MASSIVE Launcher",
    name = "MASSIVE Launcher",

    # targets to build
    #windows = ["massive.py"],
    windows = [
        {
            "script": "massive.py",
            "icon_resources": [(1, "massive.ico")]
        }
    ],
    )
