#!/usr/bin/python

import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('localhost', 0))
print sock.getsockname()[1]
