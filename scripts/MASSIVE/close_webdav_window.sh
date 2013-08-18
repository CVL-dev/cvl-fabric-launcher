#!/bin/bash

# check if we are called correctly and show usage if not
if [ $# -lt 1 ] ; then
 echo "Usage: close_webdav_window.sh <url>"
 echo "  Where:"
 echo "    <url> the WebDAV URL, e.g. webdav://wettenhj@localhost:56865/wettenhj"
 exit 0
fi

WEBDAV_URL=$1

for konquerorInstance in `dcop konqueror-*`
  do 
    KONQPID=`echo $konquerorInstance | tr '-' '\n' | tail -1`
    if [ "`dcop $konquerorInstance konqueror-mainwindow#1 currentURL`" == "$WEBDAV_URL" ]; then 
      kill $KONQPID
    fi
  done
