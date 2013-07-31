import os
import ssh
import sys

server = sys.argv[1]
username = sys.argv[2]
password = sys.argv[3]

s = ssh.SSHClient()
s.set_missing_host_key_policy(ssh.AutoAddPolicy())
s.connect(server, username=username, password=password)
ssh_stdin, ssh_stdout, ssh_stderr = s.exec_command('qstat -u %s' % (username,))
stdout, stderr = ssh_stdout.read(), ssh_stderr.read()

# FIXME use a regex instead...

for line in stdout.splitlines():
    line = line.split()

    try:
        if line[1] == username and line[2] == 'vis' and line[-2] != 'C':
            sys.stderr.write('visnode job still running: stdout')
    except IndexError:
        pass
