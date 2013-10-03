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

    emailBody="${emailBody}"

    echo -e "$emailBody" > $tmp
    cat $filename >> $tmp

    recipients="james.wettenhall@monash.edu,paul.mcintosh@monash.edu,jupiter.hu@monash.edu,chris.hines@monash.edu"
    originalRecipients=$recipients
    grep -q "Contact me? Yes" $filename && grep -q "^Config: login.cvl.massive.org.au" $filename && recipients="cvl-help@monash.edu,${recipients}"
    grep -q "Contact me? Yes" $filename && grep -q "^Config: Huygens" $filename && recipients="cvl-help@monash.edu,${recipients}"
    grep -q "Contact me? Yes" $filename && grep -q "^Config: 115.146" $filename && recipients="cvl-help@monash.edu,${recipients}"
    grep -q "Contact me? Yes" $filename && grep -q "^Config: 118.138" $filename && recipients="cvl-help@monash.edu,${recipients}"
    if [ $recipients == $originalRecipients ]
    then
        grep -q "Contact me? Yes" $filename && recipients="help@massive.org.au,${recipients}"
    fi
    mutt -s "Launcher crash report: $filename" $recipients < $tmp

done

rm -f $tmp

