#!/bin/bash

WDIR=${HOME}/${1}

mkdir $WDIR
cd $WDIR
git clone git@github.com:CVL-dev/cvl-fabric-launcher.git
cd cvl-fabric-launcher
module load python wxpython
./package_centos_version.sh

