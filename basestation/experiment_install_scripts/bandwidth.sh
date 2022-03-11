#!/bin/bash

#git may already be installed by default
apt-get install -y git

#we'll use iperf3 server on the command line rather than the python wrapped version for now
apt-get install -y iperf3

#install python3.8 if it is not installed.
apt-get install -y python3.8

#as root, in /root directory, per the aerpaw standard experiment instruction
#git clone https://github.com/CASAelyons/flypaw.git

#copy run scripts to proper locations
cp /root/flypaw/basestation/experiment_run_scripts/bandwidth/startBandwidthExperiment.sh /root

cp /root/flypaw/basestation/experiment_run_scripts/bandwidth/startBasestationAgent.sh /root/Profiles/ProfileScripts/Vehicle

cp /root/Profiles/ProfileScripts/Radio/Samples/startSRSRAN-SISO-EPCandENB.sh /root/Profiles/ProfileScripts/Radio/startRadio.sh

#for tcp iperf3 server
cp /root/flypaw/basestation/experiment_run_scripts/bandwidth/startIperf3Server_tcp.sh /root/Profiles/ProfileScripts/Traffic/startTraffic.sh

#for udp iperf3 server
#cp /root/flypaw/basestation/experiment_run_scripts/bandwidth/startIperf3Server_udp.sh /root/Profiles/ProfileScripts/Traffic/startTraffic.sh

#copy planfile you want to use to mission.plan... maybe eventually just pass as argument to basestationAgent.py
cp /root/flypaw/basestation/basestationAgent/plans/aerpaw_waypoint.plan /root/flypaw/basestation/basestationAgent/plans/mission.plan

#then, to start:
/bin/bash /root/startBandwidthExperiment.sh



