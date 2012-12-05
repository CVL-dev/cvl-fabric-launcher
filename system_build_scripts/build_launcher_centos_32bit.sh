#!/bin/bash

WDIR=${HOME}/${1}

mkdir $WDIR
cd $WDIR
rm -f master.tar.gz
wget https://github.com/CVL-dev/cvl-fabric-launcher/archive/master.tar.gz
tar zxf master.tar.gz
cd cvl-fabric-launcher-master

module load python wxpython
./package_centos_version.sh

