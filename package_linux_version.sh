#!/bin/bash

# Utility for packaging the Linux version of the installer. Example use:
#
# 	./package_linux_version.sh 0.3.1 i686
# 	./package_linux_version.sh 0.3.1 amd64
#
# You may have to change PYINSTALLERDIR to point to the directory where
# pyinstaller 1.5.1 was unpacked.

PYINSTALLERDIR=/opt/src/pyinstaller-1.5.1

set -o nounset
set -e

VERSION=$1
ARCHITECTURE=$2

rm -fr dist
python $PYINSTALLERDIR/Configure.py
rm -f launcher.spec
python /opt/src/pyinstaller-1.5.1/Makespec.py launcher.py
python /opt/src/pyinstaller-1.5.1/Build.py launcher.spec

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

./rpmbuild.sh
