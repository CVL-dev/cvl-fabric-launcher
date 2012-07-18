#!/bin/bash 
# James Wettenhall james.wettenhall@monash.edu 2012

# Mostly copied from Paul McIntosh's /usr/local/desktop/massive_desktop script.

# The MASSIVE Launcher assumes that this script is available (and executable)
#   on the MASSIVE login nodes as:
#
#   /usr/local/desktop/request_visnode.sh

# check if we are called correctly and show usage if not
if [ $# -lt 2 ] ; then
 echo "Usage: massive_desktop <project> <hours>"
 echo "  Where:"
 echo "    <project> the MASSIVE project code (e.g. MonashXXX)"
 echo "    <hours> How many hours you want the session for (e.g. 8 )"
 exit 0
fi

PROJECT=$1
HOURS=$2
echo $@
qsub -A $PROJECT -N Desktop -I -q vis -l walltime=$HOURS:0:0,nodes=1:ppn=12:gpus=2,pmem=16000MB
