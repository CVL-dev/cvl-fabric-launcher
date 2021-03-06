#!/bin/bash

# Utility for packaging the Linux version of the installer.
#
# You may have to change PYINSTALLERDIR to point to the directory where
# pyinstaller was unpacked.

PYINSTALLERDIR=`pwd`/pyinstaller-2.1

set -o nounset
set -e

VERSION=`grep '^version_number' launcher_version_number.py | cut -f 2 -d '"'`
ARCHITECTURE=`uname -m | sed s/x86_64/amd64/g | sed s/i686/i386/g`

rm -fr dist

python create_commit_def.py

# PyInstaller 2.1
python ${PYINSTALLERDIR}/pyinstaller.py launcher.py

cp "MASSIVE Launcher.desktop" 	dist/launcher/
cp massiveLauncher.sh 		dist/launcher/

mkdir dist/launcher/icons
cp IconPngs/* dist/launcher/icons/
cp README_LINUX dist/launcher/
cp -r cvlsshutils dist/launcher/

cp `python -c 'import requests; print requests.certs.where()'` dist/launcher/

mkdir -p dist/launcher/help/helpfiles/
cp help/helpfiles/* dist/launcher/help/helpfiles/
cp help/README.txt dist/launcher/help/

cd dist
mv launcher MassiveLauncher-${VERSION}_${ARCHITECTURE}
tar zcf MassiveLauncher_v${VERSION}_${ARCHITECTURE}.tar.gz MassiveLauncher-${VERSION}_${ARCHITECTURE}
cd ..

ls -lh dist/MassiveLauncher_v${VERSION}_${ARCHITECTURE}.tar.gz

