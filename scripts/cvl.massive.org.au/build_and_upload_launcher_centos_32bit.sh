#!/bin/bash

now=`date +%Y-%m-%d-%H%M`

centos32="root@118.138.241.235"

ssh $centos32 rm -f build_launcher_centos_32bit.sh
ssh $centos32 wget --no-check-certificate https://raw.github.com/CVL-dev/cvl-fabric-launcher/master/system_build_scripts/build_launcher_centos_32bit.sh
ssh $centos32 chmod +x build_launcher_centos_32bit.sh

ssh $centos32 ./build_launcher_centos_32bit.sh ${now}

set -x

scp $centos32:~/${now}/cvl-fabric-launcher/dist/MassiveLauncher_v?.?.?_i386.tar.gz          ~/upload_tmp/
scp $centos32:~/${now}/cvl-fabric-launcher/rpmbuild/RPMS/i386/massive-launcher-*i386.rpm    ~/upload_tmp/


