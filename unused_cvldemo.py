#  MASSIVE/CVL Launcher - easy secure login for the MASSIVE Desktop and the CVL
#  Copyright (C) 2012  James Wettenhall, Monash University
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  Enquires: James.Wettenhall@monash.edu or help@massive.org.au

import sys
import os
import traceback
import argparse
import ssh # Pure Python-based ssh module, based on Paramiko, published on PyPi
import subprocess
import time

global localPortNumber
localPortNumber = "5901"

global cipher
global ciphers
if sys.platform.startswith("win"):
    cipher = "arcfour"
    ciphers = ["3des-cbc", "blowfish-cbc", "arcfour"]
else:
    cipher = "arcfour128"
    ciphers = ["3des-cbc", "blowfish-cbc", "arcfour128"]

version = "0.0.1"

cvldemo_ip_address = "115.146.93.198"

ssh_private_key_filename = "<ssh_private_key_filename>"
username = "<username>"

parser = argparse.ArgumentParser(description="Create a user account on the CVL Demo virtual machine.")

parser.add_argument("-i", "--identity", action="store", default="<ssh_private_key_filename>",help="SSH private key file")
parser.add_argument("-u", "--username", action="store", default="<username>", help="Username")
parser.add_argument("-c", "--cipher", action="store", default=cipher, help="Cipher for SSH tunnel (man ssh_config).")

options = parser.parse_args()

ssh_private_key_filename = options.identity
username = options.username
cipher = options.cipher

if ssh_private_key_filename == "<ssh_private_key_filename>":
    parser.print_help()
    sys.exit(1)

if username == "<username>":
    parser.print_help()
    sys.exit(1)

print 'SSH private key file :', ssh_private_key_filename
print 'username             :', username

try:
    import getpass
    password = getpass.getpass()
    privateKeyFile = os.path.expanduser(ssh_private_key_filename)
    privateKey = ssh.RSAKey.from_private_key_file(privateKeyFile)

    sshClient = ssh.SSHClient()
    sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())
    sshClient.connect(cvldemo_ip_address, username="root", pkey=privateKey)

    stdin,stdout,stderr = sshClient.exec_command("useradd " + username)
    stderrRead = stderr.read()
    userAlreadyExists = False
    if len(stderrRead) > 0:
        if "already exists" in stderrRead:
            userAlreadyExists = True
             # We will ignore this exception.
        else:
            raise Exception(stderrRead)
    stdin,stdout,stderr = sshClient.exec_command("passwd " + username)
    stdin.write(password + "\n")
    stdin.flush()
    stdin.write(password + "\n")
    stdin.flush()
    stderrRead = stderr.read()
    if len(stderrRead) > 0:
        if "BAD PASSWORD" in stderrRead:
            raise Exception(stderrRead)
        elif not "Retype new password" in stderrRead:
            raise Exception(stderrRead)
    stdin,stdout,stderr = sshClient.exec_command("su " + username + " -c \"vncpasswd\"")
    stdin.write(password + "\n")
    stdin.flush()
    stdin.write(password + "\n")
    stdin.flush()
    if len(stderrRead) > 0:
        if "BAD PASSWORD" in stderrRead:
            raise Exception(stderrRead)
        elif not "Retype new password" in stderrRead:
            raise Exception(stderrRead)

    stdin,stdout,stderr = sshClient.exec_command("su " + username + " -c \"vncserver\"")
    stderrRead = stderr.read()
    stderrLines = stderrRead.split("\n")
    stderrLinesSplit = stderrLines[1].split(":")
    displayNumber = stderrLinesSplit[2]
    print "Display number = " + displayNumber
    sshClient.close()

    print "Generating SSH key-pair for tunnel...\n"

    sshClient = ssh.SSHClient()
    sshClient.set_missing_host_key_policy(ssh.AutoAddPolicy())
    sshClient.connect(cvldemo_ip_address, username=username, password=password)

    stdin,stdout,stderr = sshClient.exec_command("/bin/rm -f ~/CVLdemoKeyPair*")
    if len(stderr.read()) > 0:
        print stderr.read()
    stdin,stdout,stderr = sshClient.exec_command("/usr/bin/ssh-keygen -C \"CVL Demo\" -N \"\" -t rsa -f ~/CVLdemoKeyPair")
    if len(stderr.read()) > 0:
        print stderr.read()
    stdin,stdout,stderr = sshClient.exec_command("/bin/mkdir ~/.ssh")
    if len(stderr.read()) > 0:
        print stderr.read()
    stdin,stdout,stderr = sshClient.exec_command("chmod 700 ~/.ssh")
    if len(stderr.read()) > 0:
        print stderr.read()
    stdin,stdout,stderr = sshClient.exec_command("/bin/touch ~/.ssh/authorized_keys")
    if len(stderr.read()) > 0:
        print stderr.read()
    stdin,stdout,stderr = sshClient.exec_command("chmod 600 ~/.ssh/authorized_keys")
    if len(stderr.read()) > 0:
        print stderr.read()
    stdin,stdout,stderr = sshClient.exec_command("/bin/sed -i -e \"/CVL Demo/d\" ~/.ssh/authorized_keys")
    if len(stderr.read()) > 0:
        print stderr.read()
    stdin,stdout,stderr = sshClient.exec_command("/bin/cat CVLdemoKeyPair.pub >> ~/.ssh/authorized_keys")
    if len(stderr.read()) > 0:
        print stderr.read()
    stdin,stdout,stderr = sshClient.exec_command("/bin/rm -f ~/CVLdemoKeyPair.pub")
    if len(stderr.read()) > 0:
        print stderr.read()
    stdin,stdout,stderr = sshClient.exec_command("/bin/cat CVLdemoKeyPair")
    if len(stderr.read()) > 0:
        print stderr.read()

    privateKeyString = stdout.read()

    stdin,stdout,stderr = sshClient.exec_command("/bin/rm -f ~/CVLdemoKeyPair")
    if len(stderr.read()) > 0:
        print stderr.read()

    import tempfile
    privateKeyFile = tempfile.NamedTemporaryFile(mode='w+t')
    privateKeyFile.write(privateKeyString)
    privateKeyFile.flush()

    sshClient.close()

    def createTunnel():
        print "Starting tunnelled SSH session...\n"

        global localPortNumber

        try:
            if sys.platform.startswith("win"):
                sshBinary = "ssh.exe"
                if hasattr(sys, 'frozen'):
                    cvlDemoBinary = sys.executable
                    cvlDemoPath = os.path.dirname(cvlDemoBinary)
                    sshBinary = "\"" + os.path.join(cvlDemoPath, sshBinary) + "\""
                else:
                    sshBinary = "\"" + os.path.join(os.getcwd(), "sshwindows", sshBinary) + "\""

            else:
                sshBinary = "/usr/bin/ssh"

            print "Requesting ephemeral port..."

            localPortNumber = "5901"
            # Request an ephemeral port from the operating system (by specifying port 0) :
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', 0))
            localPortNumber = sock.getsockname()[1]
            sock.close()
            localPortNumber = str(localPortNumber)
            print "localPortNumber = " + localPortNumber

            remotePortNumber = str(5900 + int(displayNumber))
            tunnel_cmd = sshBinary + " -i " + privateKeyFile.name + " -c " + cipher + " " \
                "-oStrictHostKeyChecking=no " \
                "-L " + localPortNumber + ":localhost:" + remotePortNumber + " -l " + username+" "+cvldemo_ip_address

            sys.stdout.write(tunnel_cmd + "\n")
            proc = subprocess.Popen(tunnel_cmd,
                universal_newlines=True,shell=True,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
        except KeyboardInterrupt:
            sys.stdout.write("C-c: Port forwarding stopped.")
            os._exit(0)
        except:
            sys.stdout.write("CVL Demo v" + version + "\n")
            sys.stdout.write(traceback.format_exc())

    import threading
    tunnelThread = threading.Thread(target=createTunnel)
    tunnelThread.start()

    time.sleep(3)

    if sys.platform.startswith("win"):
        vnc = r"C:\Program Files\TurboVNC\vncviewer.exe"
    else:
        vnc = "/opt/TurboVNC/bin/vncviewer"
    if sys.platform.startswith("win"):
        import _winreg
        key = None
        queryResult = None
        foundTurboVncInRegistry = False
        if not foundTurboVncInRegistry:
            try:
                key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC 64-bit_is1", 0,  _winreg.KEY_WOW64_64KEY | _winreg.KEY_ALL_ACCESS)
                queryResult = _winreg.QueryValueEx(key, "InstallLocation")
                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                foundTurboVncInRegistry = True
            except:
                foundTurboVncInRegistry = False
        if not foundTurboVncInRegistry:
            try:
                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC 64-bit_is1", 0,  _winreg.KEY_WOW64_64KEY | _winreg.KEY_ALL_ACCESS)
                queryResult = _winreg.QueryValueEx(key, "InstallLocation")
                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                foundTurboVncInRegistry = True
            except:
                foundTurboVncInRegistry = False
        if not foundTurboVncInRegistry:
            try:
                key = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_ALL_ACCESS)
                queryResult = _winreg.QueryValueEx(key, "InstallLocation")
                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                foundTurboVncInRegistry = True
            except:
                foundTurboVncInRegistry = False
        if not foundTurboVncInRegistry:
            try:
                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\TurboVNC_is1", 0, _winreg.KEY_ALL_ACCESS)
                queryResult = _winreg.QueryValueEx(key, "InstallLocation")
                vnc = os.path.join(queryResult[0], "vncviewer.exe")
                foundTurboVncInRegistry = True
            except:
                foundTurboVncInRegistry = False

    if os.path.exists(vnc):
        sys.stdout.write("TurboVNC was found in " + vnc + "\n")
    else:
        sys.stdout.write("Error: TurboVNC was not found in " + vnc + "\n")

    sys.stdout.write("\nLaunching TurboVNC...\n")

    try:
        if sys.platform.startswith("win"):
            proc = subprocess.Popen("\""+vnc+"\" /user "+username+" /autopass localhost:" + localPortNumber,
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,
                universal_newlines=True)
            proc.communicate(input=password)
        else:
            subprocess.call("echo \"" + password + "\" | " + vnc + " -user " + username + " -autopass localhost:" + localPortNumber,shell=True)
            print vnc + " -user " + username + " -autopass localhost:" + localPortNumber + "\n"
        try:
            privateKeyFile.close() # Automatically removes the temporary file.
        finally:
            os._exit(0)
    except:
        sys.stdout.write(traceback.format_exc())

except:
    sys.stdout.write(traceback.format_exc())

finally:
    sshClient.close()

