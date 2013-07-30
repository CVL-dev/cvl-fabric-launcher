import os
import ssh
import sys

server = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

s = ssh.SSHClient()
s.set_missing_host_key_policy(ssh.AutoAddPolicy())
s.connect(server, username=username, password=password)
ssh_stdin, ssh_stdout, ssh_stderr = s.exec_command('cat ~/.ssh/id_rsa.pub')
stdout, stderr = ssh_stdout.read(), ssh_stderr.read()

# FIXME use a regex instead...

for line in stdout.splitlines():
    if '-login' not in line: continue
   
    line = line.split()[-1]
    line = line.split('@')

    if line[0] == username and '-login' in line[1]:
        sys.exit(0)

sys.stderr.write('failed to find Massive key\n')
