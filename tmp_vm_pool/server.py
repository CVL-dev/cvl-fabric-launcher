import socket, ssl

bindsocket = socket.socket()
bindsocket.bind(('', 10023))
bindsocket.listen(5)

def do_something(connstream, data):
    for line in data.splitlines():
        x = line.split('\t')
        assert len(x) == 2
        print '%s = %s' % (x[0], x[1],)
    return False

def deal_with_client(connstream):
    data = connstream.read()
    while data:
        if not do_something(connstream, data):
            break
        data = connstream.read()

while True:
    newsocket, fromaddr = bindsocket.accept()
    connstream = ssl.wrap_socket(newsocket,
                                 server_side=True,
                                 certfile="server.crt",
                                 keyfile="server.key",
                                 ssl_version=ssl.PROTOCOL_TLSv1)
    try:
        deal_with_client(connstream)
    finally:
        connstream.shutdown(socket.SHUT_RDWR)
        connstream.close()


