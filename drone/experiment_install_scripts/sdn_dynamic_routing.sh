#!/bin/bash

#git may already be installed by default
apt-get install -y git

#as root, in /root directory, per the aerpaw standard experiment instruction
pushd /root
git clone https://github.com/FlyNet-NSF/flypaw.git
popd

#requires python3.7+ which should be installed... otherwise install it...
#python3.7 -m pip install --upgrade pip

#if something higher than 3.7 is installed, modify pip accordingly
#PIP=pip3.7
PYTHON=python3.7
${PYTHON} -m pip install iperf3
${PYTHON} -m pip install ffmpeg
${PYTHON} -m pip install geographiclib
${PYTHON} -m pip install uuid
${PYTHON} -m pip install dataclasses
${PYTHON} -m pip install pykml
${PYTHON} -m pip install dronekit

pushd /root/Profiles/vehicle_control/aerpawlib/
python3.7 setup.py install
popd

ln -s /root/flypaw/basestation/basestationAgent/flypawClasses.py /root/flypaw/drone/flypawPilot/

#copy run scripts to proper locations
cp /root/flypaw/drone/experiment_run_scripts/sdn_dynamic_routing/start_flypaw_experiment.sh /root

cp /root/flypaw/drone/experiment_run_scripts/sdn_dynamic_routing/startFlypawPilot.sh /root/Profiles/ProfileScripts/Vehicle

cp /root/flypaw/drone/experiment_run_scripts/sdn_dynamic_routing/flypawPilot.sh /root/Profiles/ProfileScripts/Vehicle/Helpers

cp /root/Profiles/ProfileScripts/Radio/Samples/startSRSRAN-SISO-UE.sh /root/Profiles/ProfileScripts/Radio/startRadio.sh

#then, to start:
/bin/bash /root/start_flypaw_experiment.sh



