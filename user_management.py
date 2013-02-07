import json
import os
import requests

USER_MANAGEMENT_URL = 'https://cvl.massive.org.au/usermanagement/query.php'

def get_key(username, password):
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
            return json.loads(r.text)
        except:
            raise ValueError, 'Error parsing output from CVL user management system: <%s>' % (r.text,)
