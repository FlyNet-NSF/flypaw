import requests
import json
import geojson
import time
import sys
import os
import iperf3
#import pika                                                                                                                                                               
import threading
import random
#import dronekit
#from pymavlink import mavutil
#from geopy.distance import lonlat, distance, Distance                                                                                                                     
#from geopy import Point
from geographiclib.geodesic import Geodesic
#from distutils.util import strtobool
from datetime import datetime
from aerpawlib.runner import BasicRunner, entrypoint, StateMachine, state, in_background, timed_state
from aerpawlib.util import VectorNED
from aerpawlib.vehicle import Drone

#class FlyPawPilot(BasicRunner):
class FlyPawPilot(StateMachine):
    currentPosition = None
    currentBattery = None
    currentHeading = None
    currentIperfObj = None
    #@entrypoint
    @state(name="preflight", first=True)
    async def preflight(self, drone: Drone):
        self.currentPosition = getCurrentPosition(drone)
        self.currentBattery = getCurrentBattery(drone)
        self.currentHeading = drone.heading
        print(self.currentPosition['time'])
        print(self.currentBattery['level'])
        print(self.currentHeading)
        #take off to 30m
        #await drone.takeoff(10)
        return "flight"
        #take off to 30m
        #await drone.takeoff(10)

        # fly north 10m
        #await drone.goto_coordinates(drone.position + VectorNED(10, 0))

        # land
        #await drone.land()
    

    @state(name="flight")
    async def flight(self, drone: Drone):
        self.currentPosition = getCurrentPosition(drone)
        self.currentBattery = getCurrentBattery(drone)
        self.currentHeading = drone.heading
        print(self.currentPosition['time'])
        print(self.currentBattery['level'])
        print(self.currentHeading)
        return "iperf"

    @timed_state(name="iperf",duration = 2)
    async def iperf(self, drone: Drone):
        output_json = {}
        client = iperf3.Client()
        client.server_hostname = "192.168.116.2"
        client.port = 5201
        client.duration = 1
        client.json_output = True
        result = client.run()
        err = result.error
        if err is not None:
            output_json['connection'] = err
            output_json['mbps'] = None
            output_json['retransmits'] = None
            output_json['meanrtt'] = None
            thistime = datetime.now()
            unixsecs = datetime.timestamp(thistime)
            output_json['unixsecs'] = int(unixsecs)
        else:
            datarate = result.sent_Mbps
            retransmits = result.retransmits
            unixsecs = result.timesecs
            result_json = result.json
            meanrtt = result_json['end']['streams'][0]['sender']['mean_rtt']
            output_json['connection'] = 'ok'
            output_json['mbps'] = datarate
            output_json['retransmits'] = retransmits
            output_json['unixsecs'] = unixsecs
            output_json['meanrtt'] = meanrtt

        self.currentIperfObj = output_json
        #print(output_json['mbps'])
        if (output_json['mbps'] == None):
            print("no connection, continue")
            return "flight"
        else:
            return "videoanalysis"

    @state(name="videoanalysis")
    async def videoanalysis(self, _ ):
        print("videoanalysis")
        print(self.currentIperfObj['mbps'])
        return "flight"
    
            

def getCurrentPosition(drone: Drone):
    if drone.connected:
        pos = drone.position
        gps = drone.gps
        currentPosition = {}
        currentPosition['lat'] = pos.lat
        currentPosition['lon'] = pos.lon
        currentPosition['alt'] = pos.alt
        currentPosition['time'] = datetime.now().astimezone().isoformat()
        currentPosition['fix'] = gps.fix_type
        currentPosition['fix_type'] = gps.satellites_visible
        return currentPosition
    else:
        return None
    
def getCurrentBattery(drone: Drone):
    if drone.connected:
        battery = drone.battery
        currentBattery = {}
        currentBattery['voltage'] = battery.voltage
        currentBattery['current'] = battery.current
        currentBattery['level'] = battery.level
        return currentBattery
    else:
        return None
    
