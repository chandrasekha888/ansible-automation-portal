#!/bin/bash

cd /home/mamidianish/ansible-demo

LOG_FILE="errdisable_monitor.log"
ALERT_FILE="errdisable_alert.txt"

ansible-playbook -i hosts.ini errdisable_check.yml > $LOG_FILE 2>&1

if grep -i "err-disabled\|bpdu\|storm\|failed" $LOG_FILE > /dev/null
then
    echo "ALERT: Err-disabled port detected" > $ALERT_FILE
    echo "Time: $(date)" >> $ALERT_FILE
    echo "" >> $ALERT_FILE
    cat $LOG_FILE >> $ALERT_FILE

    echo "Err-disabled alert detected. Check file: $ALERT_FILE"
else
    echo "No err-disabled ports found at $(date)"
fi
