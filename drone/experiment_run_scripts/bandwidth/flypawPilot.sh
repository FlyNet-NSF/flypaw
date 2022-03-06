#!/bin/bash
#
# This script will start the flypawPilot application
#

cd /root/flypaw/drone/flypawPilot
$AERPAW_PYTHON -u -m aerpawlib \
	  --script flypawPilot \
	  --vehicle $VEHICLE_TYPE \
	  --conn :14550



