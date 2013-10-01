#!/bin/bash

now=`date +%Y-%m-%d-%H%M`

ubuntu64="root@118.138.240.153"

ssh $ubuntu64 rm -f build_launcher_ubuntu_64bit.sh
ssh $ubuntu64 wget --no-check-certificate https://raw.github.com/CVL-dev/cvl-fabric-launcher/master/system_build_scripts/build_launcher_ubuntu_64bit.sh
ssh $ubuntu64 chmod +x build_launcher_ubuntu_64bit.sh

ssh $ubuntu64 ./build_launcher_ubuntu_64bit.sh ${now}

scp $ubuntu64:~/${now}/cvl-fabric-launcher/massive-launcher*deb ~/upload_tmp/

