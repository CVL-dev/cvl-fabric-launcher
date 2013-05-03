#!/bin/bash

echo "::: start of $0"
echo "::: Checking for version issues..."
echo "Launcher version $1"

echo "::: System MOTD..."
cat /etc/motd

echo "::: Home Filesystem Quota..."
check_quota -v

echo "::: end of $0"

