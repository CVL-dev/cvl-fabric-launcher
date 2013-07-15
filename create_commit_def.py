import subprocess
import sys

if sys.platform.startswith("win"):
    proc = subprocess.Popen('"C:\\Program Files\\Git\\bin\\git.exe" log -1 --name-status', 
                            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                            universal_newlines=True)
    stdout, stderr = proc.communicate()
else:
    proc = subprocess.Popen('git log -1 --name-status', 
                            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                            universal_newlines=True)
    stdout, stderr = proc.communicate()

stdout = stdout.split('\n')[0].split()

assert stdout[0] == 'commit'
commit = stdout[1]

f = open('commit_def.py', 'w')
f.write('LATEST_COMMIT = "' + commit + '"\n')
f.close()

import os
os.chdir('cvlsshutils')

if sys.platform.startswith("win"):
    proc = subprocess.Popen('"C:\\Program Files\\Git\\bin\\git.exe" log -1 --name-status',
                            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                            universal_newlines=True)
    stdout, stderr = proc.communicate()
else:
    proc = subprocess.Popen('git log -1 --name-status',
                            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                            universal_newlines=True)
    stdout, stderr = proc.communicate()

stdout = stdout.split('\n')[0].split()

assert stdout[0] == 'commit'
commit = stdout[1]

os.chdir('..')

f = open('commit_def.py', 'a')
f.write('LATEST_COMMIT_CVLSSHUTILS = "' + commit + '"\n')
f.close()
