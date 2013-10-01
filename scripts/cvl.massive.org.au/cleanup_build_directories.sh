#!/bin/bash

centos32="root@115.146.86.142"
centos64="root@115.146.93.11"

debian32="root@115.146.93.80"
debian64="root@115.146.93.83"

ubuntu32="root@118.138.240.169"
ubuntu64="root@118.138.240.153"

ssh $centos32 rm -fvr 2013*
ssh $centos64 rm -fvr 2013*

ssh $debian32 rm -fvr 2013*
ssh $debian64 rm -fvr 2013*

ssh $ubuntu32 rm -fvr 2013*
ssh $ubuntu64 rm -fvr 2013*

