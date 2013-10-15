#!/bin/bash

# The MASSIVE/CVL Launcher's home-directory sharing functionality  assumes that 
# this script is available (and executable) on the CVL VMs as:
#
#   /usr/local/bin/cat_dbus_session_file.sh

# The inotifywait stuff was inspired by:
# http://stackoverflow.com/questions/2379829/while-loop-to-test-if-a-file-exists-in-bash
# Note the following:
# For anyone wondering why the loop, it's to deal with possible race conditions
# between creation and waiting and because inotifywait has --exclude to filter
# out filenames, but not --include to ignore everything except the filename.

if [ -z ${DISPLAY} ]
then
  echo "cat_dbus_session_file.sh ERROR: DISPLAY environment variable is not set."
  exit 1
fi

MACHINE_ID=$(cat /var/lib/dbus/machine-id)
DBUS_SESSION_FILE=~/.dbus/session-bus/$MACHINE_ID-$(echo $DISPLAY | tr -d ":" | tr -d ".0")
VNC_PID_FILE=~/.vnc/${HOSTNAME}${DISPLAY}.pid

# Wait until directory exists.

while [ ! -d ~/.dbus ]
do
    echo "Waiting until ~/.dbus/ exists..."
    inotifywait -t 1 -e create -e moved_to ~
done

# Wait until directory exists.

while [ ! -d ~/.dbus/session-bus ]
do
    echo "Waiting until ~/.dbus/session-bus/ exists..."
    inotifywait -t 1 -e create -e moved_to ~/.dbus
done

# Wait until file exists.

while [ ! -f "$DBUS_SESSION_FILE" ]
do
    echo "Waiting until $DBUS_SESSION_FILE exists..."
    inotifywait -t 1 -e create -e moved_to ~/.dbus/session-bus
done

# Ensure that we are not using an old DBUS session file.

while [ $DBUS_SESSION_FILE -ot $VNC_PID_FILE ]
do
  echo "Waiting until $DBUS_SESSION_FILE is up-to-date..."
  inotifywait -t 1 -e create -e moved_to -e modify ~/.dbus/session-bus
done

cat $DBUS_SESSION_FILE

