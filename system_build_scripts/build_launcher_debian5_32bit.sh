#!/bin/bash

if [ $# -lt 1 ]; then
    echo "Usage: build_launcher_debian5_32bit.sh <build_directory>"
    exit 1
fi

#WDIR=${HOME}/${1}
WDIR=${1}

if [ -d $WDIR ]; then
    echo "Error: Please remove the existing \"$WDIR\" directory. It will be created automatically."
    exit 1
fi

mkdir $WDIR
cd $WDIR
#git clone git@github.com:CVL-dev/cvl-fabric-launcher.git
# The following git clone command doesn't require SSH keys to be set up,
# however it only provides a read-only clone of the repository.
git clone git://github.com/CVL-dev/cvl-fabric-launcher
cd cvl-fabric-launcher
. /opt/sw/32bit/debian/modules/3.2.9c/Modules/3.2.9/init/bash
module load python wxpython
./package_debian_version.sh

