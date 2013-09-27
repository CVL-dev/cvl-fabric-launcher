#!/bin/bash

now=`date +%Y-%m-%d-%H%M`

centos64="root@115.146.93.11"

ssh $centos64 rm -f build_launcher_centos_64bit.sh
ssh $centos64 wget --no-check-certificate https://raw.github.com/CVL-dev/cvl-fabric-launcher/master/system_build_scripts/build_launcher_centos_64bit.sh
ssh $centos64 chmod +x build_launcher_centos_64bit.sh

ssh $centos64 ./build_launcher_centos_64bit.sh ${now}

scp $centos64:~/${now}/cvl-fabric-launcher/dist/MassiveLauncher_v*.tar.gz                   ~/upload_tmp/
scp $centos64:~/${now}/cvl-fabric-launcher/rpmbuild/RPMS/x86_64/massive-launcher-*.rpm      ~/upload_tmp/


