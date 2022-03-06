#!/bin/bash

export VEHICLE_TYPE="${VEHICLE_TYPE:-drone}"

cd $PROFILE_DIR"/ProfileScripts/Vehicle/Helpers"
screen -S flypawPilot -dm \
       bash -c "./flypawPilot.sh"
