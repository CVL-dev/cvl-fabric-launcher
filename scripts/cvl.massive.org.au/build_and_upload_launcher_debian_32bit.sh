#!/bin/bash

now=`date +%Y-%m-%d-%H%M`

debian32="root@115.146.93.80"

ssh $debian32 rm -f build_launcher_debian_32bit.sh
ssh $debian32 wget --no-check-certificate https://raw.github.com/CVL-dev/cvl-fabric-launcher/master/system_build_scripts/build_launcher_debian_32bit.sh
ssh $debian32 chmod +x build_launcher_debian_32bit.sh

ssh $debian32 ./build_launcher_debian_32bit.sh ${now}

scp $debian32:~/${now}/cvl-fabric-launcher/massive-launcher*deb ~/upload_tmp/


