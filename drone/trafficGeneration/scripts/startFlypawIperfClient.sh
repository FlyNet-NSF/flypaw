#!/bin/bash
#
# This script will start an iperf client to the specified destination
#

DESTINATION_IP=172.16.0.1
# Checking the connection via ping to server until it gets it
while ((1)) ; do 
  echo "Looking for connection..."
  ping  -c 1 -W 1 $DESTINATION_IP >& /dev/null
  rv=$?;
  if (test $rv -eq 0); then
     echo "Got it"
     break;
  fi
  sleep 1;
done

# total transmit time (in seconds)
#IPERF_DURATION="${IPERF_DURATION:-300}" # seconds
#IPERF_DURATION=300

# Destination IP address
#DESTINATION_IP="${DESTINATION_IP:-'172.16.0.1'}"


# add -u to use UDP instead of the default TCP 
# add -R to use reverse direction (from server to client)

#iperf3 -c $DESTINATION_IP -t $IPERF_DURATION

screen -S iperfclient -dm \
       bash -c "python3 /root/flypaw/drone/iperfClientToBasestation.py -b ${DESTINATION_IP} -p 5201 -o /root/Results/flypaw"
