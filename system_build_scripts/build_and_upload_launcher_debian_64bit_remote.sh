#!/bin/bash

WDIR=${HOME}/${1}

mkdir $WDIR
cd $WDIR
git clone git@github.com:CVL-dev/cvl-fabric-launcher.git
cd cvl-fabric-launcher
. /opt/sw/64bit/debian/modules/3.2.9c/Modules/3.2.9/init/bash
module load python wxpython
./package_debian_version.sh

