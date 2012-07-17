// MASSIVE Launcher ssh_tunnel module
// Requires the libssh2 library.
// Based on libssh2's direct_tcpip.c 

// THIS ssh_tunnel MODULE IS NOT CURRENTLY USED. 
// ITS IMPLEMENTATION IS INCOMPLETE AND IT DOESN'T WORK IN ITS CURRENT FORM.
// IT HAS BEEN REPLACED BY CALLS TO EXTERNAL SSH PROCESSES
// (ssh on Mac, Linux and plink.exe on Windows).
// THIS FILE WILL PROBABLY BE REMOVED FROM THE REPOSITORY SOON.

/*
From: https://groups.google.com/forum/?fromgroups#!topic/comp.security.ssh/qEss3K48wQY

...
So if I say 'ssh -L 1234:thingy:5678 host', the client opens port
1234 and listens on it, and every time a connection comes in, it
sends a "direct-tcpip" request asking the server to connect to
thingy:5678. Typically a client user will run that command, and then
in another window on the client machine run some other command that
connects to that por

*/

#include <Python.h>

#include "libssh2_config.h"
#include <libssh2.h>

#ifdef WIN32
#include <windows.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <netdb.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/time.h>
#endif

#include <fcntl.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>

#ifdef HAVE_SYS_SELECT_H
#include <sys/select.h>
#endif

#ifndef INADDR_NONE
#define INADDR_NONE (in_addr_t)-1
#endif

#define DEBUG 1

enum {
    AUTH_NONE = 0,
    AUTH_PASSWORD,
    AUTH_PUBLICKEY
};

static PyObject *SshTunnelError;

static PyObject *
ssh_tunnel_system(PyObject *self, PyObject *args)
{
    const char *command;
    int sts;

    if (!PyArg_ParseTuple(args, "s", &command))
        return NULL;
    sts = system(command);
    if (sts < 0) {
        PyErr_SetString(SshTunnelError, "System command failed");
        return NULL;
    }
    // return Py_BuildValue("i", sts);
    return PyLong_FromLong(sts);

    // If you have a C function that returns no useful argument 
    // (a function returning void), the corresponding 
    // Python function must return None:
    //
    // Py_INCREF(Py_None);
    // return Py_None;
} 

static PyObject *
ssh_tunnel_create_tunnel(PyObject *self, PyObject *args)
{
	const char *keyfile1 = "/home/username/.ssh/id_rsa.pub";
	const char *keyfile2 = "/home/username/.ssh/id_rsa";

	const char *username = "username";
	const char *password = "";

	const char *local_listenip = "127.0.0.1";
	unsigned int local_listenport = 5901;	
	unsigned int local_wantport = 5901;	

	const char *remote_desthost = "localhost"; /* resolved by the server */
	unsigned int remote_destport = 5901;
	unsigned int remote_listenport;

	const char *server_hostname = "";
	char server_ip[1024];

    if (!PyArg_ParseTuple(args, "ssisis",
        &username, &password, 
        &local_listenport,
    	&remote_desthost, &remote_destport,
        &server_hostname))
    {
        return NULL;
    }

    struct hostent *server_host = gethostbyname(server_hostname);
    if (server_host==NULL)
    {
        herror("gethostbyname failed");
        //return -1;
        Py_INCREF(Py_None);
        return Py_None;
    }

    struct in_addr *address = (struct in_addr *) server_host->h_addr;
    strcpy(server_ip, inet_ntoa(*address));

    //fprintf(stderr, "server_ip = %s\n",server_ip);

    /*** Main functionality ***/
    	
    int rc, sock = -1, listensock = -1, forwardsock = -1, i, auth = AUTH_NONE;
    struct sockaddr_in sin;
    socklen_t sinlen = sizeof(sin);
    const char *fingerprint;
    char *userauthlist;
    LIBSSH2_SESSION *session;
    LIBSSH2_LISTENER *listener = NULL;
    LIBSSH2_CHANNEL *channel = NULL;
    const char *shost;
    unsigned int sport;
    fd_set fds;
    struct timeval tv;
    ssize_t len, wr;
    char buf[16384];

#ifdef WIN32
    char sockopt;
    WSADATA wsadata;

    WSAStartup(MAKEWORD(2,0), &wsadata);
#else
    int sockopt;
#endif

    rc = libssh2_init (0);
    if (rc != 0) {
        fprintf (stderr, "libssh2 initialization failed (%d)\n", rc);
        //return 1;
        Py_INCREF(Py_None);
        return Py_None;
    }

    /* Connect to SSH server */
    sock = socket(PF_INET, SOCK_STREAM, IPPROTO_TCP);
    sin.sin_family = AF_INET;
    if (INADDR_NONE == (sin.sin_addr.s_addr = inet_addr(server_ip))) {
        perror("inet_addr");
        fprintf(stderr, "Failed to connect to %s\n", server_ip);
        //return -1;
        Py_INCREF(Py_None);
        return Py_None;
    }
    sin.sin_port = htons(22);
    if (connect(sock, (struct sockaddr*)(&sin),
                sizeof(struct sockaddr_in)) != 0) {
        fprintf(stderr, "failed to connect!\n");
        //return -1;
        Py_INCREF(Py_None);
        return Py_None;
    }

    /* Create a session instance */
    session = libssh2_session_init();
    if(!session) {
        fprintf(stderr, "Could not initialize SSH session!\n");
        //return -1;
        Py_INCREF(Py_None);
        return Py_None;
    }

    /* ... start it up. This will trade welcome banners, exchange keys,
     * and setup crypto, compression, and MAC layers
     */
    rc = libssh2_session_handshake(session, sock);
    if(rc) {
        fprintf(stderr, "Error when starting up SSH session: %d\n", rc);
        //return -1;
        Py_INCREF(Py_None);
        return Py_None;
    }

    /* At this point we havn't yet authenticated.  The first thing to do
     * is check the hostkey's fingerprint against our known hosts Your app
     * may have it hard coded, may go to a file, may present it to the
     * user, that's your call
     */
    fingerprint = libssh2_hostkey_hash(session, LIBSSH2_HOSTKEY_HASH_SHA1);
    fprintf(stderr, "Fingerprint: ");
    for(i = 0; i < 20; i++)
        fprintf(stderr, "%02X ", (unsigned char)fingerprint[i]);
    fprintf(stderr, "\n");

    /* check what authentication methods are available */
    userauthlist = libssh2_userauth_list(session, username, strlen(username));
    printf("Authentication methods: %s\n", userauthlist);
    if (strstr(userauthlist, "password"))
        auth |= AUTH_PASSWORD;
    if (strstr(userauthlist, "publickey"))
        auth |= AUTH_PUBLICKEY;

    if (auth & AUTH_PASSWORD) {
#ifdef DEBUG
        fprintf(stderr, "Attempting to authenticate using supplied password.\n");
#endif
        if (libssh2_userauth_password(session, username, password)) {
            fprintf(stderr, "Authentication by password failed.\n");
            goto shutdown;
        }
#ifdef DEBUG
        fprintf(stderr, "Authentication successful!\n");
#endif
    } else if (auth & AUTH_PUBLICKEY) {
        if (libssh2_userauth_publickey_fromfile(session, username, keyfile1,
                                                keyfile2, password)) {
            printf("\tAuthentication by public key failed!\n");
            goto shutdown;
        }
        printf("\tAuthentication by public key succeeded.\n");
    } else {
        printf("No supported authentication methods found!\n");
        goto shutdown;
    }

#ifdef DEBUG
        fprintf(stderr, "local_listenip: %s\n", local_listenip);
        fprintf(stderr, "local_listenport: %d\n", local_listenport);
#endif

    printf("Asking localhost to listen on remote %s:%d\n", local_listenip,
        local_listenport);

    /* tell libssh2 we want it all done non-blocking */
    //libssh2_session_set_blocking(session, 0);

    listener = libssh2_channel_forward_listen_ex(session, local_listenip,
        local_wantport, &local_listenport, 1);
    if (!listener) {
        fprintf(stderr, "Could not start the tcpip-forward listener!\n"
                "(Note that this can be a problem at the server!"
                " Please review the server logs.)\n");
        goto shutdown;
    }

    printf("Localhost is listening on %s:%d\n", local_listenip,
        local_listenport);

    /* Must use non-blocking IO hereafter due to the current libssh2 API */
    libssh2_session_set_blocking(session, 0);

    printf("Here 1\n");
    shost = inet_ntoa(sin.sin_addr);
    printf("Here 2\n");
    sport = ntohs(sin.sin_port);
    printf("Here 3\n");

    // Not sure if this is necessary:
    //libssh2_channel_forward_listen(session, remote_destport);

    printf("remote_desthost = %s, remote_destport = %d\n", remote_desthost, remote_destport);
    //channel = libssh2_channel_direct_tcpip_ex(session, remote_desthost,
        //remote_destport, shost, sport);
    channel = libssh2_channel_direct_tcpip(session, remote_desthost, remote_destport);
    printf("Here 4\n");
    if (!channel) {
        fprintf(stderr, "Could not open the direct-tcpip channel!\n"
                "(Note that this can be a problem at the server!"
                " Please review the server logs.)\n");
        goto shutdown;
    }

    /*
    printf("Waiting for remote connection\n");
    channel = libssh2_channel_forward_accept(listener);
    if (!channel) {
        fprintf(stderr, "Could not accept connection!\n"
                "(Note that this can be a problem at the server!"
                " Please review the server logs.)\n");
        goto shutdown;
    }
    */

    /*
    listensock = socket(PF_INET, SOCK_STREAM, IPPROTO_TCP);
    sin.sin_family = AF_INET;
    //sin.sin_port = htons(local_listenport);
    sin.sin_port = htons(remote_destport);
    //if (INADDR_NONE == (sin.sin_addr.s_addr = inet_addr(local_listenip))) {
    if (INADDR_NONE == (sin.sin_addr.s_addr = inet_addr(remote_desthost))) {
        perror("inet_addr");
        goto shutdown;
    }
    sockopt = 1;
    setsockopt(listensock, SOL_SOCKET, SO_REUSEADDR, &sockopt, sizeof(sockopt));
    sinlen=sizeof(sin);
    memset(&sin, 0, sinlen); // Added by James W 
    if (-1 == bind(listensock, (struct sockaddr *)&sin, sinlen)) {
        perror("bind");
        goto shutdown;
    }
    if (-1 == listen(listensock, 2)) {
        perror("listen");
        goto shutdown;
    }

    printf("Waiting for TCP connection on %s:%d...\n",
        inet_ntoa(sin.sin_addr), ntohs(sin.sin_port));

    forwardsock = accept(listensock, (struct sockaddr *)&sin, &sinlen);
    if (-1 == forwardsock) {
        perror("accept");
        goto shutdown;
    }

    shost = inet_ntoa(sin.sin_addr);
    sport = ntohs(sin.sin_port);

    //printf("Forwarding connection from %s:%d here to remote %s:%d\n", shost,
        //sport, remote_desthost, remote_destport);
        //
    printf("Forwarding connection from remote %s:%d to local %s:%d\n", shost,
        sport, local_listenip, local_listenport);

    channel = libssh2_channel_direct_tcpip_ex(session, remote_desthost,
        remote_destport, shost, sport);
    if (!channel) {
        fprintf(stderr, "Could not open the direct-tcpip channel!\n"
                "(Note that this can be a problem at the server!"
                " Please review the server logs.)\n");
        goto shutdown;
    }

    */

    /* Must use non-blocking IO hereafter due to the current libssh2 API */
    libssh2_session_set_blocking(session, 0);

    while (1) {
        FD_ZERO(&fds);
        FD_SET(forwardsock, &fds);
        tv.tv_sec = 0;
        tv.tv_usec = 100000;
        rc = select(forwardsock + 1, &fds, NULL, NULL, &tv);
        if (-1 == rc) {
            perror("select");
            goto shutdown;
        }
        if (rc && FD_ISSET(forwardsock, &fds)) {
            len = recv(forwardsock, buf, sizeof(buf), 0);
            if (len < 0) {
                perror("read");
                goto shutdown;
            } else if (0 == len) {
                printf("The client at %s:%d disconnected!\n", shost, sport);
                goto shutdown;
            }
            wr = 0;
            do {
                i = libssh2_channel_write(channel, buf, len);
                if (i < 0) {
                    fprintf(stderr, "libssh2_channel_write: %d\n", i);
                    goto shutdown;
                }
                wr += i;
            } while(i > 0 && wr < len);
        }
        while (1) {
            len = libssh2_channel_read(channel, buf, sizeof(buf));
            if (LIBSSH2_ERROR_EAGAIN == len)
                break;
            else if (len < 0) {
                fprintf(stderr, "libssh2_channel_read: %d", (int)len);
                goto shutdown;
            }
            wr = 0;
            while (wr < len) {
                i = send(forwardsock, buf + wr, len - wr, 0);
                if (i <= 0) {
                    perror("write");
                    goto shutdown;
                }
                wr += i;
            }
            if (libssh2_channel_eof(channel)) {
                printf("The server at %s:%d disconnected!\n",
                    remote_desthost, remote_destport);
                goto shutdown;
            }
        }
    }

shutdown:
#ifdef WIN32
    closesocket(forwardsock);
    closesocket(listensock);
#else
    close(forwardsock);
    close(listensock);
#endif
    if (channel)
        libssh2_channel_free(channel);
    libssh2_session_disconnect(session, "Client disconnecting normally");
    libssh2_session_free(session);

#ifdef WIN32
    closesocket(sock);
#else
    close(sock);
#endif
    libssh2_exit();    
    
    /*** End main functionality ***/
    
    //if (result < 0) {
      //  PyErr_SetString(SshTunnelError, "System command failed");
        //return NULL;
    //}

    // return Py_BuildValue("i", result);
    // return PyLong_FromLong(result);

    // If you have a C function that returns no useful argument 
    // (a function returning void), the corresponding 
    // Python function must return None:
    //
    Py_INCREF(Py_None);
    return Py_None;
} 

static PyMethodDef SshTunnelMethods[] = {
    //...
    {"system",  ssh_tunnel_system, METH_VARARGS,
     "Execute a shell command."},
    {"create_tunnel",  ssh_tunnel_create_tunnel, METH_VARARGS,
     "Create an SSH tunnel."},
    //...
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

// The init<modulename> function, should be the only non-static
// item defined in the module file.
PyMODINIT_FUNC
initssh_tunnel(void)
{
    PyObject *m;

    m = Py_InitModule("ssh_tunnel", SshTunnelMethods);
    if (m == NULL)
        return;

    SshTunnelError = PyErr_NewException("ssh_tunnel.error", NULL, NULL);
    Py_INCREF(SshTunnelError);
    PyModule_AddObject(m, "error", SshTunnelError);
}

int main(int argc, char *argv[])
{
    /* Pass argv[0] to the Python interpreter */
    Py_SetProgramName(argv[0]);

    /* Initialize the Python interpreter.  Required. */
    Py_Initialize();

    /* Add a static module */
    initssh_tunnel();
}
