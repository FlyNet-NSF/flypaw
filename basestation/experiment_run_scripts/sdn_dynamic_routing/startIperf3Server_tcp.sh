#!/bin/bash
#
# This script will start an iperf server 
#

# add -u to use UDP instead of the default TCP 

#iperf3 -s
screen -S iperfserver -dm \
       bash -c "iperf3 -s \
       | ts $TS_FORMAT \
       | tee $RESULTS_DIR/$LOG_PREFIX\_iperfserver_log.txt"
