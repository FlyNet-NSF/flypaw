#!/bin/bash

#git may already be installed by default
apt-get install -y git

#as root, in /root directory, per the aerpaw standard experiment instruction
#git clone https://github.com/CASAelyons/flypaw.git

#requires python3.7+ which should be installed... otherwise install it...
python3.7 -m pip install --upgrade pip

#if something higher than 3.7 is installed, modify pip accordingly

PIP=pip3.7
${PIP} install iperf3
${PIP} install geographiclib
${PIP} install uuid
#${PIP} install dronekit￼

#copy run scripts to proper locations
cp /root/flypaw/drone/experiment_run_scripts/bandwidth/startBandwidthExperiment.sh /root

cp /root/flypaw/drone/experiment_run_scripts/bandwidth/startFlypawPilot.sh /root/Profiles/ProfileScripts/Vehicle

cp /root/flypaw/drone/experiment_run_scripts/bandwidth/flypawPilot.sh /root/Profiles/ProfileScripts/Vehicle/Helpers

cp /root/Profiles/ProfileScripts/Radio/Samples/startSRSRAN-SISO-UE.sh /root/Profiles/ProfileScripts/Radio/startRadio.sh

#then, to start:
/bin/bash /root/startBandwidthExperiment.sh



