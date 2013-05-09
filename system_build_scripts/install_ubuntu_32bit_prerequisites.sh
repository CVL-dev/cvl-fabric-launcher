#!/bin/bash

set -x
set -e

curl http://python-distribute.org/distribute_setup.py | python
curl https://raw.github.com/pypa/pip/master/contrib/get-pip.py | python

pip install ssh
pip install pycrypto
pip install appdirs
pip install requests
