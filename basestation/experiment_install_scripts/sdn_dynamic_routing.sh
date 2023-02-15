#!/bin/bash

#git may already be installed by default
apt-get install -y git

#we'll use iperf3 server on the command line rather than the python wrapped version for now
apt-get install -y iperf3

pushd /root
git clone https://github.com/FlyNet-NSF/flypaw.git
popd

mkdir /usr/local/python
pushd /usr/local/python
wget https://www.python.org/downloads/release/python-31010/
tar -xzf Python-3.10.10.tgz 
popd
pushd /usr/local/python/Python-3.10.10
./configure --prefix=/usr/local/python
make
make install
popd
export PATH=/usr/local/python/bin:$PATH
echo "export PATH=/usr/local/python/bin:$PATH" >> /root/.bashrc
python3.10 -m pip install pip
pip3.10 install --upgrade pip
pip3.10 install geojson
pip3.10 install pytz
pip3.10 install requests
pip3.10 install mobius-py

#copy run scripts to proper locations
cp /root/flypaw/basestation/experiment_run_scripts/sdn_dynamic_routing/start_flypaw_experiment.sh /root

cp /root/flypaw/basestation/experiment_run_scripts/sdn_dynamic_routing/startBasestationAgent.sh /root/Profiles/ProfileScripts/Vehicle

cp /root/Profiles/ProfileScripts/Radio/Samples/startSRSRAN-SISO-EPCandENB.sh /root/Profiles/ProfileScripts/Radio/startRadio.sh

#for tcp iperf3 server
cp /root/flypaw/basestation/experiment_run_scripts/sdn_dynamic_routing/startIperf3Server_tcp.sh /root/Profiles/ProfileScripts/Traffic/startTraffic.sh

#for udp iperf3 server
#cp /root/flypaw/basestation/experiment_run_scripts/bandwidth/startIperf3Server_udp.sh /root/Profiles/ProfileScripts/Traffic/startTraffic.sh

#copy planfile you want to use to mission.plan... maybe eventually just pass as argument to basestationAgent.py
cp /root/flypaw/basestation/basestationAgent/plans/aerpaw_waypoint.plan /root/flypaw/basestation/basestationAgent/plans/mission.plan

#then, to start:
/bin/bash /root/start_flypaw_experiment.sh



