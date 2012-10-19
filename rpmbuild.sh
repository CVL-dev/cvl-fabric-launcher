#!/bin/bash

cd rpmbuild

mkdir BUILD
mkdir BUILDROOT
mkdir RPMS
mkdir SOURCES
mkdir SRPMS
mkdir tmp

rm -f ~/.rpmmacros
echo "%_topdir  "`pwd`     >> ~/.rpmmacros
echo "%_tmppath "`pwd`/tmp >> ~/.rpmmacros

VERSION=`grep Version SPECS/massive-launcher.spec  | cut -f 2 -d ' '`

rm -fr massive-launcher-${VERSION}
mkdir -p massive-launcher-${VERSION}/opt/MassiveLauncher

rm -f massive-launcher-${VERSION}.tar.gz SOURCES/massive-launcher-${VERSION}.tar.gz 
cp -r ../dist/MassiveLauncher-0.3.1_i686/* massive-launcher-${VERSION}/opt/MassiveLauncher
tar zcf massive-launcher-${VERSION}.tar.gz massive-launcher-${VERSION}
cp massive-launcher-${VERSION}.tar.gz SOURCES/

rpmbuild -ba SPECS/massive-launcher.spec
cd ..

find rpmbuild/ -iname '*rpm' -exec ls -lh {} \;


