
import sys
import os
import argparse
import ssh # Pure Python-based ssh module, based on Paramiko, published on PyPi

version = "0.0.1"

cvldemo_ip_address = "115.146.93.198"

ssh_private_key_filename = "<ssh_private_key_filename>"
username = "<username>"

parser = argparse.ArgumentParser(description="Create a user account on the CVL Demo virtual machine.")

parser.add_argument("-i", "--identity", action="store", default="<ssh_private_key_filename>",help="SSH private key file")
parser.add_argument("-u", "--username", action="store", default="<username>", help="Username")

options = parser.parse_args()

ssh_private_key_filename = options.identity

username = options.username

print 'SSH private key file :', ssh_private_key_filename
print 'username             :', username

import getpass
password = getpass.getpass()

privateKeyFile = os.path.expanduser(ssh_private_key_filename)
privateKey = ssh.RSAKey.from_private_key_file(privateKeyFile)
sshClient = ssh.SSHClient()
sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())
sshClient.connect(cvldemo_ip_address, username="root", pkey=privateKey)

stdin,stdout,stderr = sshClient.exec_command("useradd " + username)
stderrRead = stderr.read()
if len(stderrRead) > 0:
    sys.stdout.write(stderrRead)
stdin,stdout,stderr = sshClient.exec_command("passwd " + username)
stdin.write(password + "\n")
stdin.flush()
stdin.write(password + "\n")
stdin.flush()
stderrRead = stderr.read()
if len(stderrRead) > 0:
    sys.stdout.write(stderrRead)

sshClient.close()

