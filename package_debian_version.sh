#!/bin/bash

VERSION=`grep '^version_number' launcher_version_number.py | cut -f 2 -d '"'`
ARCHITECTURE=`uname -m | sed s/x86_64/amd64/g | sed s/i686/i386/g`

./package_linux_version.sh $VERSION $ARCHITECTURE

TMP="tmp_debian_build"

sudo rm -fr $TMP
sudo rm -f *.deb

TARGET=$TMP/opt/MassiveLauncher
mkdir -p $TARGET

mkdir -p $TMP/usr/share/applications

cp massive-launcher.desktop $TMP/usr/share/applications/

cp -r dist/MassiveLauncher-${VERSION}_${ARCHITECTURE}/* $TARGET/
mkdir $TMP/DEBIAN
cp release/control  $TMP/DEBIAN
cp release/postinst $TMP/DEBIAN

installedSize=`du -sx --exclude DEBIAN $TMP | awk '{print $1}'`

sed -i "s/VERSION/${VERSION}/g" $TMP/DEBIAN/control
sed -i "s/ARCHITECTURE/${ARCHITECTURE}/g" $TMP/DEBIAN/control
sed -i "s/XXINSTALLEDSIZE/${installedSize}/g" $TMP/DEBIAN/control

sudo chown -R root.root $TMP
sudo find $TMP/ -iname '*.so.*' -exec chmod a-x {} \;
sudo find $TMP/ -iname '*.so.*' -exec strip     {} \;
sudo chmod a-x $TMP/opt/MassiveLauncher/icons/MASSIVElogoTransparent144x144.png
sudo chmod a-x $TMP/opt/MassiveLauncher/"MASSIVE Launcher.desktop"

DEB=massive-launcher_${VERSION}_${ARCHITECTURE}.deb
sudo dpkg -b $TMP $DEB

echo
echo
echo
ls -lh *.deb
echo
echo
