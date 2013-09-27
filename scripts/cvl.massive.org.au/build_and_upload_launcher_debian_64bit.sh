#!/bin/bash

now=`date +%Y-%m-%d-%H%M`

debian64="root@115.146.93.83"

ssh $debian64 rm -f build_launcher_debian_64bit.sh
ssh $debian64 wget --no-check-certificate https://raw.github.com/CVL-dev/cvl-fabric-launcher/master/system_build_scripts/build_launcher_debian_64bit.sh
ssh $debian64 chmod +x build_launcher_debian_64bit.sh

ssh $debian64 ./build_launcher_debian_64bit.sh ${now}

scp $debian64:~/${now}/cvl-fabric-launcher/massive-launcher*deb ~/upload_tmp/

