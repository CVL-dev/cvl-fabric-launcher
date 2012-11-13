#!/bin/bash

# Utility for packaging the Linux version of the installer.
#
# You may have to change PYINSTALLERDIR to point to the directory where
# pyinstaller 1.5.1 was unpacked.

PYINSTALLERDIR=`pwd`/pyinstaller-1.5.1

set -o nounset
set -e

VERSION=`grep '^version_number' launcher_version_number.py | cut -f 2 -d '"'`
ARCHITECTURE=`uname -m | sed s/x86_64/amd64/g | sed s/i686/i386/g`

rm -fr dist
python $PYINSTALLERDIR/Configure.py
rm -f launcher.spec
python ${PYINSTALLERDIR}/Makespec.py launcher.py
python ${PYINSTALLERDIR}/Build.py launcher.spec

cp "MASSIVE Launcher.desktop" 	dist/launcher/
cp massiveLauncher.sh 		dist/launcher/

mkdir dist/launcher/icons
cp IconPngs/* dist/launcher/icons/
cp README_LINUX dist/launcher/

cd dist
mv launcher MassiveLauncher-${VERSION}_${ARCHITECTURE}
tar zcf MassiveLauncher_v${VERSION}_${ARCHITECTURE}.tar.gz MassiveLauncher-${VERSION}_${ARCHITECTURE}
cd ..

ls -lh dist/MassiveLauncher_v${VERSION}_${ARCHITECTURE}.tar.gz

