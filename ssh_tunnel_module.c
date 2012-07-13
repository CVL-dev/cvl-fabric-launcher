#include <Python.h>

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
    // Python function must return None.
    // Py_INCREF(Py_None);
    // return Py_None;
} 

static PyMethodDef SshTunnelMethods[] = {
    //...
    {"system",  ssh_tunnel_system, METH_VARARGS,
     "Execute a shell command."},
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
