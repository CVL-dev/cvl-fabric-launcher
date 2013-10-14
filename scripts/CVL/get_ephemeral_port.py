#!/usr/bin/python

# The MASSIVE/CVL Launcher's home-directory sharing functionality  assumes that 
# this script is available (and executable) on the CVL VMs as:
#
#   /usr/local/bin/get_ephemeral_port.py

import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('localhost', 0))
print sock.getsockname()[1]
