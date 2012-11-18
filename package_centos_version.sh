#!/bin/bash

SRC=`pwd`

VERSION=`grep '^version_number' ${SRC}/launcher_version_number.py | cut -f 2 -d '"'`
ARCHITECTURE=`uname -m | sed s/x86_64/amd64/g | sed s/i686/i386/g`

./package_linux_version.sh

cd rpmbuild

rm -fr BUILD BUILDROOT RPMS SOURCES SRPMS tmp
mkdir  BUILD BUILDROOT RPMS SOURCES SRPMS tmp

rm -f ~/.rpmmacros
echo "%_topdir  "`pwd`     >> ~/.rpmmacros
echo "%_tmppath "`pwd`/tmp >> ~/.rpmmacros


sed s/VERSION/${VERSION}/g SPECS/massive-launcher.spec.template > SPECS/massive-launcher.spec

if [ "$ARCHITECTURE" == "amd64" ]
then
    sed -i s/libc.so.6\(GLIBC_PRIVATE\)/libc.so.6\(GLIBC_PRIVATE\)\(64bit\)/g SPECS/massive-launcher.spec
fi

rm -fr massive-launcher-${VERSION}

mkdir -p massive-launcher-${VERSION}/opt/MassiveLauncher
mkdir -p massive-launcher-${VERSION}/usr/share/applications
rm -f massive-launcher-${VERSION}.tar.gz SOURCES/massive-launcher-${VERSION}.tar.gz 

cp ../massive-launcher.desktop massive-launcher-${VERSION}/usr/share/applications/
cp -r ../dist/MassiveLauncher-${VERSION}_${ARCHITECTURE}/* massive-launcher-${VERSION}/opt/MassiveLauncher

tar zcf massive-launcher-${VERSION}.tar.gz massive-launcher-${VERSION}
cp massive-launcher-${VERSION}.tar.gz SOURCES/

rpmbuild -ba SPECS/massive-launcher.spec
cd ..

find rpmbuild/ -iname '*rpm' -exec ls -lh {} \;


