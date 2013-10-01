#!/bin/bash

now=`date +%Y-%m-%d-%H%M`

ubuntu32="root@118.138.240.169"

ssh $ubuntu32 rm -f build_launcher_ubuntu_32bit.sh
ssh $ubuntu32 wget --no-check-certificate https://raw.github.com/CVL-dev/cvl-fabric-launcher/master/system_build_scripts/build_launcher_ubuntu_32bit.sh
ssh $ubuntu32 chmod +x build_launcher_ubuntu_32bit.sh

ssh $ubuntu32 ./build_launcher_ubuntu_32bit.sh ${now}

scp $ubuntu32:~/${now}/cvl-fabric-launcher/massive-launcher*deb ~/upload_tmp/


