import os
import ssh
import sys

server = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

s = ssh.SSHClient()
s.set_missing_host_key_policy(ssh.AutoAddPolicy())
s.connect(server, username=username, password=password)
ssh_stdin, ssh_stdout, ssh_stderr = s.exec_command('rm -fr ~/.ssh')
