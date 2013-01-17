#!/bin/bash

if [ $# -lt 1 ]; then
    echo "Usage: build_launcher_centos_32bit.sh <build_directory>"
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
rm -f master.tar.gz
wget https://github.com/CVL-dev/cvl-fabric-launcher/archive/master.tar.gz -O master.tar.gz
tar zxf master.tar.gz
cd cvl-fabric-launcher-master

module load python wxwidgets
./package_centos_version.sh

