#!/bin/bash
# James Wettenhall james.wettenhall@monash.edu 2012

# Mostly copied from Paul McIntosh's /usr/local/desktop/massive_desktop script.

# The MASSIVE Launcher assumes that this script is available (and executable)
#   on the MASSIVE login nodes as:
#
#   /usr/local/desktop/request_visnode.sh

# check if we are called correctly and show usage if not
if [ $# -lt 2 ] ; then
 echo "Usage: request_visnode.sh <project> <hours> [visnodes] [persistent] [qstat] [qpeek] [resolution]"
 echo "  Where:"
 echo "    <project> the MASSIVE project code (e.g. MonashXXX)"
 echo "    <hours> How many hours you want the session for (e.g. 4 )"
 echo "    [visnodes] How many vis nodes you want the session for (e.g. 2) default 1"
 echo "    [persistent] If True, run in batch mode for session persistence and multiple nodes"
 echo "    [qstat] If True, repeatedly run qstat and wait for job to start."
 echo "    [qpeek] If True, sleep for 15 seconds and then run qpeek to display the job's STDOUT."
 echo "    [resolution] If specified (e.g. 1024x768), call /usr/local/desktop/set_display_resolution.sh [resolution]"
 exit 0
fi

# if [[ "$USER" == "paulmc" ]]; then
#    echo /usr/local/desktop/test_request_visnode.sh $@
#    /usr/local/desktop/test_request_visnode.sh $@
#    exit 0
# fi

#echo "WARN: If you hit cancel after this message your job will still run!"
#echo "WARN Hi!!!"
#echo "ERROR Bye!!"

PROJECT=$1
HOURS=$2
VISNODES=1

cluster=`hostname | grep -o m[1-2]`

# Set persistent defaults for each cluster
if [[ "$cluster" == "m1" ]]; then
 PERSISTENT=True
else
 PERSISTENT=False
fi

export MASSIVE_PROJECT=$PROJECT
# echo "INFO: MASSIVE is experiencing an unscheduled outage, it may not be possible to get a desktop"

if [ $# -ge 3 ] ; then
 VISNODES=$3
 if [ $VISNODES -ge 2 ] ; then
   echo "INFO: You have requested more than one vis node. This should only be used for parallel vis jobs e.g. ParaViewi. Also note that \"module load massive\" is required in your .bashrc, please contact help@massive.org.au is you need help doing this"
 fi
fi
if [ $# -ge 4 ] ; then
 PERSISTENT=$4
fi
QSTAT=True
if [ $# -ge 5 ] ; then
  QSTAT=$5
fi
QPEEK=True
if [ $# -ge 6 ] ; then
  QPEEK=$6
fi
if [ $# -ge 7 ] ; then
  RESOLUTION=$7
  /usr/local/desktop/set_display_resolution.sh $RESOLUTION
fi

USERSHORT=$( echo $USER | cut -c 1-8 )
if [[ "$PERSISTENT" == "True" ]]
then
  # If job already exists connect to that otherwise start a new session
  # jobid_full=`qstat | grep top_ | grep $USERSHORT | egrep "R NORMAL|R compute|R vis" | awk '{print $1}'`
  jobid_full=`qstat -r -u $USER | grep desktop_ | awk '{print $1}'`
  echo jobid_full $jobid_full
  if [[ "$jobid_full" == "" ]];
  then
     # this is a new job
#     if [[ "$cluster" == "m1" ]];
#     then
#     jobid_full=`qsub -A $PROJECT -N desktop\_$USER  -l walltime=$HOURS:00:00,nodes=$VISNODES:ppn=12:gpus=2,gres=xsrv,mem=48000MB /usr/local/desktop/pbs_hold_script`
#     else  # m2
     jobid_full=`qsub -A $PROJECT -N desktop\_$USER -q vis -l walltime=$HOURS:00:00,nodes=$VISNODES:ppn=12:gpus=2 /usr/local/desktop/pbs_hold_script`
     # jobid_full=`qsub -A $PROJECT -N desktop\_$USER -q vis -l walltime=$HOURS:00:00,nodes=$VISNODES:ppn=12:gpus=2,mem=192000MB /usr/local/desktop/pbs_hold_script`
#     fi
  fi
  echo $jobid_full
  if [[ "$QSTAT" == "True" ]]; then
          # need jobid without server name for qpeek
          jobid=`echo $jobid_full | cut -d '.' -f 1`
          checktime=1
          echo sleep $checktime
          sleep $checktime
          isrunning=`qstat -f $jobid_full | grep "job_state = R"`
          echo $isrunning
          while [[ "$isrunning" == "" ]]
          do
            checktime=$[$checktime+1]
            echo sleep $checktime
            sleep $checktime
            isrunning=`qstat -f $jobid_full | grep "job_state = R"`
            qstat $jobid_full
          done
          echo "Looking good..."
  fi
  if [[ "$QPEEK" == "True" ]]; then
    echo "Waiting 15 seconds to make sure that there are no errors..."
    sleep 15
    qpeek $jobid
  fi
else
#  if [[ "$cluster" == "m1" ]];
#  then
#    qsub -A $PROJECT -N desktop\_$USER -I -l walltime=$HOURS:00:00,nodes=$VISNODES:ppn=12:gpus=2,gres=xsrv,mem=48000MB
#    sleep 10
#  else # on m2
    qsub -A $PROJECT -N desktop\_$USER -I -q vis -l walltime=$HOURS:0:0,nodes=$VISNODES:ppn=12:gpus=2
    # qsub -A $PROJECT -N Desktop -I -q vis -l walltime=$HOURS:0:0,nodes=$VISNODES:ppn=12:gpus=2,mem=192000MB
#  fi
fi
