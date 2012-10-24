#!/bin/bash

sudo apt-get --assume-yes install 	python-wxgtk2.8 python-wxgtk2.8-dbg \
					python-pycryptopp python-pycryptopp-dbg python-libssh2 \
					python-setuptools python-dev \
					alien

sudo easy_install pip 
sudo pip install ssh
sudo pip install appdirs
sudo pip install psutil

VERSION=`grep '^version_number' launcher_version_number.py | cut -f 2 -d '"'`
ARCHITECTURE=`uname -m | sed s/x86_64/amd64/g | sed s/i686/i386/g`

./package_linux_version.sh $VERSION $ARCHITECTURE

TMP="tmp_debian_build"

rm -fr $TMP
rm -f *.deb *.rpm

TARGET=$TMP/opt/MassiveLauncher-${VERSION}_${ARCHITECTURE}
mkdir -p $TARGET

cp -r dist/MassiveLauncher-${VERSION}_${ARCHITECTURE}/* $TARGET/
mkdir $TMP/DEBIAN
cp release/control $TMP/DEBIAN

sed -i "s/VERSION/${VERSION}/g" $TMP/DEBIAN/control
sed -i "s/ARCHITECTURE/${ARCHITECTURE}/g" $TMP/DEBIAN/control

sed -i "s@/opt/MassiveLauncher@/opt/MassiveLauncher-${VERSION}_${ARCHITECTURE}@g" \
    ${TARGET}/MASSIVE\ Launcher.desktop \
    ${TARGET}/massiveLauncher.sh

DEB=massive-launcher_${VERSION}_${ARCHITECTURE}.deb
dpkg -b $TMP $DEB
sudo alien --to-rpm $DEB

echo
echo
echo
ls -lh *.deb *.rpm
echo
echo
