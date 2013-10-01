#!/bin/bash

version=`ls massive-launcher_*_amd64.deb | grep -vi ubuntu | cut -f 2 -d '_'`

mv massive-launcher-${version}-1.i386.rpm        MASSIVE_Launcher_v${version}-1.i686.rpm
mv massive-launcher-${version}-1.x86_64.rpm      MASSIVE_Launcher_v${version}-1.amd64.rpm

mv massive-launcher_${version}_i386.deb          MASSIVE_Launcher_v${version}_i686.deb
mv massive-launcher_${version}_amd64.deb         MASSIVE_Launcher_v${version}_amd64.deb

mv massive-launcher_UBUNTU_${version}_i386.deb          MASSIVE_Launcher_v${version}_ubuntu13_i686.deb
mv massive-launcher_UBUNTU_${version}_amd64.deb         MASSIVE_Launcher_v${version}_ubuntu13_amd64.deb

mv MassiveLauncher_v${version}_i386.tar.gz       MASSIVE_Launcher_v${version}_i686.tar.gz
mv MassiveLauncher_v${version}_amd64.tar.gz      MASSIVE_Launcher_v${version}_amd64.tar.gz



