#!/bin/bash

WDIR=${HOME}/${1}

mkdir -p $WDIR
cd $WDIR
#git clone git@github.com:CVL-dev/cvl-fabric-launcher.git
#git clone https://github.com/CVL-dev/cvl-fabric-launcher
git clone git://github.com/CVL-dev/cvl-fabric-launcher
cd cvl-fabric-launcher
. /opt/sw/32bit/debian/modules/3.2.9c/Modules/3.2.9/init/bash
module load python wxpython
./package_debian_version.sh

