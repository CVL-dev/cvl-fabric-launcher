import json
import os
import requests
import ssh
from base64 import b64decode

DEFAULT_USER_MANAGEMENT_URL = 'http://115.146.94.161/UserManagement/query.php'

def run_ssh_command(ssh_client, command):
    """
    Run a command using the supplied ssh client, returning stdout and stderr.
    """

    stdin, stdout, stderr = ssh_client.exec_command(command)
    stdout, stderr = stdout.read(), stderr.read()

    if stdout == None: stdout = ''
    if stderr == None: stderr = ''

    return stdout, stderr

def get_key(cvlLauncherConfig, username, password, use_default_url=False):
    if use_default_url:
        url = DEFAULT_USER_MANAGEMENT_URL
    else:
        url = cvlLauncherConfig.get("CVL Launcher Preferences", 'CVL_UM_server_URL')

    query_message = {'request_user_data': 'True', 'request_private_key': 'True', 'username': username, 'password': password} # FIXME sanity check username, password

    try:
        if os.path.exists('cacert.pem'):
            r = requests.post(url, data={'queryMessage': json.dumps(query_message), 'query': 'Send to user management'}, verify='cacert.pem') # Does not make sense to json.dumps() here!
        else:
            r = requests.post(url, data={'queryMessage': json.dumps(query_message), 'query': 'Send to user management'})                      # Does not make sense to json.dumps() here!
    except:
        raise ValueError, 'Could not query CVL user management system.'

    if r.ok:
        r = json.loads(r.text)

        if 'error' in r:
            raise ValueError, 'User Management error: <%s>' % (r['error'],)
        else:
            try:
                if 'private_key' in r:
                    r['private_key'] = b64decode(r['private_key'])
                return r
            except:
                raise ValueError, 'Could not find private key in User Management response; keys were: <%s>' % (r.keys(),)

def set_vnc_password(hostname, username, key_file):
    """
    Using a previously set up ssh keypair, connect to the host
    and set the vnc password to a random hex string.

    Returns the new password.
    """

    vnc_password = os.urandom(16).encode('hex')

    try:
        ssh_client = ssh.SSHClient()
        ssh_client.set_missing_host_key_policy(ssh.AutoAddPolicy())

        ssh_client.connect(hostname, username=username, look_for_keys=False, key_filename=key_file)

        run_ssh_command(ssh_client, 'mkdir ~/.vnc')
        stdout, stderr = run_ssh_command(ssh_client, 'module load tigervnc; echo %s | vncpasswd -f %s --stdin > ~/.vnc/passwd' % (vnc_password, username,))
    except:
        raise IOError, 'Could not set VNC password on host %s for user %s' % (hostname, username,)

    return vnc_password

