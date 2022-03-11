#!/bin/bash

export AERPAW_REPO=${AERPAW_REPO:-/root/AERPAW-Dev}
export AERPAW_PYTHON=${AERPAW_PYTHON:-python3.7}
#export LAUNCH_MODE=${LAUNCH_MODE:-'EMULATION'}
export LAUNCH_MODE=${LAUNCH_MODE:-'TESTBED'}
export EXP_NUMBER=${EXP_NUMBER:-1}

export RESULTS_DIR="${RESULTS_DIR:-/root/Results}"
export TS_FORMAT="${TS_FORMAT:-'[%Y-%m-%d %H:%M:%.S]'}"
export LOG_PREFIX="$(date +%Y-%m-%d_%H:%M:%S)"

export PROFILE_DIR=$AERPAW_REPO"/AHN/E-VM/Profile_software"
cd $PROFILE_DIR"/ProfileScripts"

./Radio/startRadio.sh
./Traffic/startTraffic.sh
#./Vehicle/startVehicle.sh

#this is our basestationAgent script
./Vehicle/startBasestationAgent.sh
