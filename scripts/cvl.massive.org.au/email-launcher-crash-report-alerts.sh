#!/bin/bash

# This file, used by the Launcher, lives in
# /root/cron/email-launcher-crash-report-alerts.sh
# on cvl.massive.org.au
# Running crontab -l as root gives:
# */5 * * * * /root/cron/email-launcher-crash-report-alerts.sh

tmp=`mktemp`

find /opt/launcher_crash_reports/ -type f -mmin -5 | while read filename
do
    emailBody=""

    crashReportContent=`cat $filename`
    emailBody="${emailBody}${crashReportContent}"

    echo -e "$emailBody" > $tmp

    recipients="james.wettenhall@monash.edu,paul.mcintosh@monash.edu,jupiter.hu@monash.edu,chris.hines@monash.edu"
    originalRecipients=$recipients
    grep -q "Contact me? Yes" $filename && grep -q "^Config: login.cvl.massive.org.au" $filename && recipients="cvl-help@monash.edu,${recipients}"
    grep -q "Contact me? Yes" $filename && grep -q "^Config: Huygens" $filename && recipients="cvl-help@monash.edu,${recipients}"
    if [ $recipients == $originalRecipients ]
    then
        recipients="help@massive.org.au,${recipients}"
    fi
    mutt -s "Launcher crash report: $filename" $recipients < $tmp

done

rm -f $tmp

