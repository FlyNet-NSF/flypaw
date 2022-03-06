#!/bin/bash

#git may already be installed by default
apt-get install -y git

#as root, in /root directory, per the aerpaw standard experiment instruction
git clone https://github.com/CASAelyons/flypaw.git

#install python3.8 if it is not installed... Not going to script this for now
#

#copy run scripts to proper locations
cp /root/flypaw/basestation/experiment_run_scripts/bandwidth/startBandwidthExperiment.sh /root

cp /root/flypaw/basestation/experiment_run_scripts/bandwidth/startBasestationAgent.sh /root/Profiles/ProfileScripts/Vehicle

#copy planfile you want to use to mission.plan... maybe eventually just pass as argument to basestationAgent.py
cp /root/flypaw/basestation/basestationAgent/plans/aerpaw_waypoint.plan /root/flypaw/basestation/basestationAgent/plans/mission.plan

#then, to start:
/bin/bash /root/startBandwidthExperiment.sh



