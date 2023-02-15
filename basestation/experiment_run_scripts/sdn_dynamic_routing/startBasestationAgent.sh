#!/bin/bash
#
# This script will start the basestation agent
#

pushd /root/flypaw/basestation/basestationAgent

screen -S basestationAgent -dm \
       bash -c "python3.10 /root/flypaw/basestation/basestationAgent/basestationAgent.py"

