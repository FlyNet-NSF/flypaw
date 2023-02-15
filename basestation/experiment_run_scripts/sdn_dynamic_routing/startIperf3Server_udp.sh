#!/bin/bash
#
# This script will start an iperf server 
#

# add -u to use UDP instead of the default TCP 


screen -S iperfserver -dm \
       bash -c "python3.8 /root/flypaw/basestation/iperfServer_udp/iperfServer_udp.py"

