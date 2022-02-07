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

pushd /root/flypaw/drone/trafficGeneration/iperfClientToBasestation

screen -S iperfclient -dm \
       bash -c "python3 /root/flypaw/drone/trafficGeneration/iperfClientToBasestation/iperfClientToBasestation.py -b ${DESTINATION_IP} -p 5201 -o ${RESULTS_DIR}"
