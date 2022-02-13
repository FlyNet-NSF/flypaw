import requests
import json
import geojson
import time
import sys
import os
import iperf3
import socket
import pickle
import uuid
import select
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
#from aerpawlib.vehicle import Vehicle
from aerpawlib.vehicle import Drone

#class FlyPawPilot(BasicRunner):
class FlyPawPilot(StateMachine):
    currentPosition = None
    currentBattery = None
    #currentAttitude = None
    currentHeading = None
    currentHome = None
    currentIperfObj = None

    videoLocation = getVideoLocation()
    
    #@entrypoint
    @state(name="preflight", first=True)
    async def preflight(self, drone: Drone):
                
        self.currentPosition = getCurrentPosition(drone)
        self.currentBattery = getCurrentBattery(drone)
        #self.currentAttitude = getCurrentAttitude(drone)
        self.currentHeading = drone.heading
        self.currentHome = drone.home_coords
        
        #take off to 30m
        #await drone.takeoff(10)
        return "flight"
    
        #await drone.takeoff(10)

        # fly north 10m
        #await drone.goto_coordinates(drone.position + VectorNED(10, 0))

        # land
        #await drone.land()
    

    @state(name="flight")
    async def flight(self, drone: Drone):
        self.currentPosition = getCurrentPosition(drone)
        self.currentBattery = getCurrentBattery(drone)
        #self.currentAttitude = getCurrentAttitude(drone) #may or may not be available
        self.currentHeading = drone.heading
        return "reportPositionUDP" 
        #return "iperf"

    @state(name="reportPositionUDP")
    async def reportPositionUDP(self, drone: Drone):
        defaultSequence = "flight"
        nextSequence = defaultSequence
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "telemetry"
        msg['telemetry'] = {}
        msg['telemetry']['position'] = []
        msg['telemetry']['position'].append(self.currentPosition['lat'])
        msg['telemetry']['position'].append(self.currentPosition['lon'])
        msg['telemetry']['position'].append(self.currentPosition['alt'])
        msg['telemetry']['position'].append(self.currentPosition['time'])
        msg['telemetry']['gps'] = {}
        msg['telemetry']['gps']['fix'] = self.currentPosition['fix']
        msg['telemetry']['gps']['fix_type'] = self.currentPosition['fix_type']
        msg['telemetry']['battery'] = {}
        msg['telemetry']['battery']['voltage'] = self.currentBattery['voltage']
        msg['telemetry']['battery']['current'] = self.currentBattery['current']
        msg['telemetry']['battery']['level'] = self.currentBattery['level']
        #msg['telemetry']['attitude'] = {}
        #msg['telemetry']['attitude']['pitch'] = self.currentAttitude['pitch']
        #msg['telemetry']['attitude']['yaw'] = self.currentAttitude['yaw']
        #msg['telemetry']['attitude']['roll'] = self.currentAttitude['roll']
        msg['telemetry']['heading'] = self.currentHeading
        #msg['telemetry']['
        msg['telemetry']['home'] = []
        msg['telemetry']['home'].append(self.currentHome.lat)
        msg['telemetry']['home'].append(self.currentHome.lon)
        msg['telemetry']['home'].append(self.currentHome.alt)

        serverReply = udpClientMsg(msg, "192.168.116.2", 20001)
        if serverReply is not None:
            #print(serverReply)
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
                nextSequence = "instructionRequest"
            else:
                print("we have a mismatch in uuids... investigate")
                
        return nextSequence

    @state(name="instructionRequest")
    async def instructionRequest(self, drone: Drone):
        defaultSequence = "flight"
        nextSequence = defaultSequence
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "instructionRequest"
        serverReply = udpClientMsg(msg, "192.168.116.2", 20001)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
                if 'requests' in serverReply:
                    theseRequests = serverReply['requests']
                    #just handle the first request for now
                    if serverReply['requests'] is not None:
                        thisPrimaryRequest = theseRequests[0]
                        if 'command' in thisPrimaryRequest:
                            requestIsValid = validateRequest(thisPrimaryRequest['command'])
                            if requestIsValid:
                                print("performing request: " + thisPrimaryRequest['command'])
                                nextSequence = thisPrimaryRequest['command']
                                return nextSequence
        #if for any reason you asked for a request and didn't get one or got a bad one, we're on our own for now
        #implement safety checks
        #check how far we are from the home location
        #implement me
        #estimate how much battery it will take to get there
        #implement me
        #reqBatteryToGetHome = 30
        #if currentBattery['level'] < reqBatteryToGetHome:
        #look for new home within range... if none available, head toward home and prepare for crash landing
        #elif currentBattery['level'] >= reqBatteryToGetHome and currentBattery['level'] < reqBatteryToGetHome + 10:
        #look for new home or go home
        #else:
        #proceed
        #return "flight"
        
        
    @timed_state(name="iperf",duration = 2)
    async def iperf(self, drone: Drone):
        defaultSequence = "flight"
        nextSequence = defaultSequence
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "iperfResults"
        msg['iperfResults'] = {}
        client = iperf3.Client()
        client.server_hostname = "192.168.116.2"
        client.port = 5201
        client.duration = 1
        client.json_output = True
        result = client.run()
        err = result.error
        if err is not None:
            msg['iperfResults']['connection'] = err
            msg['iperfResults']['mbps'] = None
            msg['iperfResults']['retransmits'] = None
            msg['iperfResults']['meanrtt'] = None
            thistime = datetime.now()
            unixsecs = datetime.timestamp(thistime)
            msg['iperfResults']['unixsecs'] = int(unixsecs)
        else:
            datarate = result.sent_Mbps
            retransmits = result.retransmits
            unixsecs = result.timesecs
            result_json = result.json
            meanrtt = result_json['end']['streams'][0]['sender']['mean_rtt']
            msg['iperfResults']['connection'] = 'ok'
            msg['iperfResults']['mbps'] = datarate
            msg['iperfResults']['retransmits'] = retransmits
            msg['iperfResults']['unixsecs'] = unixsecs
            msg['iperfResults']['meanrtt'] = meanrtt

        self.currentIperfObj = msg['iperfResults']
        serverReply = udpClientMsg(msg, "192.168.116.2", 20001)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
                nextSequence = "instructionRequest"
        #print(msg['iperfResults']['mbps'])
        if (msg['iperfResults']['mbps'] == None):
            print("no connection, continue")
        
        return nextSequence

    @state(name="sendVideo")
    async def sendVideo(self, _ ):
        defaultSequence = "flight"
        nextSequence = defaultSequence
        
        x = uuid.uuid4()
        msg = {}
        
    
    @state(name="collectVideo")
    async def collectVideo(self, _ ):
        defaultSequence = "flight"
        nextSequence = defaultSequence
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "collectVideo"
        msg['collectVideo'] = {}
        serverReply = udpClientMsg(msg, "192.168.116.2", 20001)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
                nextSequence = "instructionRequest"

        print("collectVideo")
        return nextSequence
    
            

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

#def getCurrentAttitude(vehicle: Vehicle):
    #function does not work
    #Vehicle in aerpawlib needs to be updated
    #    if drone.connected:
#        attitude = drone.Attitude
#        currentAttitude = {}
#        currentAttitude['pitch'] = attitude[0]
#        currentAttitude['yaw'] = attitude[1]
#        currentAttitude['roll'] = attitude[2]
#        return currentAttitude
#    else:
#        return None

def getVideoLocation():
    #check on the specific camera software configuration
    #maybe add a camera argument
    #or just hardcode for now:
    videoLocation = "/opt/video/"
    return videoLocation
    
    
def validateRequest(request):
    validReq = []
    validReq.append("iperf")
    validReq.append("flight")
    validReq.append("sendVideo")
    validReq.append("collectVideo")
    validReq.append("instructionRequest")

    if request in validReq:
        return 1    
    else:
        return 0
    
def udpClientMsg(msg, address, port):
    try:
        serialMsg = pickle.dumps(msg)
        serverLoc = (address, port)
        chunkSize = 1024
        timeout_in_seconds = 1
        UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPClientSocket.sendto(serialMsg, serverLoc)
        UDPClientSocket.setblocking(0)
        readiness = select.select([UDPClientSocket], [], [], timeout_in_seconds)
        if readiness[0]:
            serialMsgFromServer = UDPClientSocket.recvfrom(chunkSize)
            try:
                server_msg = pickle.loads(serialMsgFromServer[0])
                "Reply from Server {}".format(server_msg)
                print(server_msg)
                return server_msg
            except pickle.UnpicklingError as upe:
                print("bad response from server: " + upe)
                return None
        else:
            print("timeout")
            return None
    except pickle.PicklingError as pe:
        print("could not encode data")
        return None
        
