import json
import os
import requests
import ssh
from base64 import b64decode

def run_ssh_command(ssh_client, command):
    """
    Run a command using the supplied ssh client, returning stdout and stderr.
    """

    stdin, stdout, stderr = ssh_client.exec_command(command)
    stdout, stderr = stdout.read(), stderr.read()

    if stdout == None: stdout = ''
    if stderr == None: stderr = ''

    return stdout, stderr


USER_MANAGEMENT_URL = 'https://cvl.massive.org.au/usermanagement/query.php'

def get_key(username, password):
    """
    Query the user management system to get the user's private key file and other info.

    Example:

    get_key('testuser', 'testpassword') returns

    {u'massive_account': u'testuser@massive',
     u'private_key': '-----BEGIN RSA PRIVATE KEY-----\n...',
     u'private_key_name': u'cvl_massive_key',
     u'vm_ip': u'192.168.1.1'}

    """

    query_message = 'request_user_data= request_private_key= ' + 'username=' + username + ' password=' + password

    try:
        if os.path.exists('cacert.pem'):
            r = requests.post(USER_MANAGEMENT_URL, {'queryMessage': query_message, 'query': 'Send to user management'}, verify='cacert.pem')
        else:
            r = requests.post(USER_MANAGEMENT_URL, {'queryMessage': query_message, 'query': 'Send to user management'})
    except:
        raise ValueError, 'Could not query CVL user management system.'

    if r.ok and not 'error' in r.text:
        try:
            payload = json.loads(r.text)
            if 'private_key' in payload:
                payload['private_key'] = b64decode(payload['private_key'])
            return payload
        except:
            raise ValueError, 'Error parsing output from CVL user management system: <%s>' % (r.text,)

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

