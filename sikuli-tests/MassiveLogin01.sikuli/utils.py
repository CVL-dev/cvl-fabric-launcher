import os

def kill_pageant_and_charade():
    username = os.path.split(os.path.expanduser('~'))[-1]

    lines = os.popen('tasklist /FI "USERNAME eq %s"' % username).read().splitlines()

    for line in lines:
        if len(line.split()) == 0: continue

        pid = None

        if line.split()[0] == 'PAGEANT.EXE':
            pid = line.split()[1]
        elif line.split()[0] == 'charade.exe':
            pid = line.split()[1]

        if pid is not None:
            print pid
            os.popen('TASKKILL /PID ' + str(pid) +' /F')

def kill_launcher():
    username = os.path.split(os.path.expanduser('~'))[-1]

    lines = os.popen('tasklist /FI "USERNAME eq %s"' % username).read().splitlines()

    for line in lines:
        if len(line.split()) == 0: continue

        pid = None

        if line.split()[0] == 'launcher.exe':
            pid = line.split()[1]

        if pid is not None:
            print pid
            os.popen('TASKKILL /PID ' + str(pid) +' /F')

