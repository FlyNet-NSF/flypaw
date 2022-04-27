#!/usr/bin/env python3
import json


class iperfInfo(object):
    def __init__(self, ipaddr="172.16.0.1", port=5201, protocol="tcp", priority=0, mbps=0, meanrtt=0):
        self.ipaddr = ipaddr #string server ip address
        self.port = port #string server port address 
        self.protocol = protocol #tcp, udp
        self.priority = 1 #normalized float 0-1         
        self.mbps = mbps #float, units mbps, representing throughput
        self.meanrtt = meanrtt #float, units ms, representing latency
        self.location4d = [float, float, float, str]
        
class collectVideoInfo(object):
    def __init__(self, dataformat="jpgframes", duration=5, quality=100, priority = 1):
        self.dataformat = dataformat #jpgframes, ffmpeg, etc
        self.duration = duration #units seconds
        self.quality = quality #arbitrary unit
        self.priority = priority #normalized float 0-1

class sendVideoInfo(object):
    def __init__(self, dataformat="jpgframes", ipaddr="172.16.0.1", port="23000", priority=1):
        self.dataformat = dataformat #jpgframes, ffmpeg, etc
        self.ipaddr = ipaddr #string ip address
        self.port = port #int port number 
        self.priority = priority #normalized float 0-1

class flightInfo(object):
    def __init__(self):
        """
        coords : [float,float]--> [lon, lat]
        altitude: float --> M AGL(?)
        airspeed: float --> 
        """
        self.coords = [] #[lon, lat]
        self.altitude = float #meters 
        self.airspeed = float #airspeed 
        self.groundspeed = float #groundspeed
        self.priority = float #normalized float 0-1

class missionInfo(object):
    #we'll have to think this through for different mission types
    def __init__(self):
        self.defaultWaypoints = [] #planfile
        self.missionType = str #videography, delivery, air taxi, etc.
        self.missionLeader = str #basestation, drone, cloud, edge device(s)
        self.priority = float #normalized float from 0-1
        self.planfile = str #path to planfile optional 

class resourceInfo(object):
    def __init__(self):
        self.name = str #identifier for resource
        self.location = str #edge, cloud x, cloud y
        self.purpose = str #mission related I guess
        self.interface = str #thinking something like direct vs kubectl
        self.resourceAddresses = [] #one or more ways to communicate with resource... possibly a pairing? eg ("management", "xxx.xxx.xxx.xxx")
        self.state = str #resource reservation state
        self.load = float #placeholder for now... maybe if we have info from prometheus or something
    
class VehicleCommands(object):
    def __init__(self):
        self.commands = {}
        self.commands['iperf'] = {} 
        self.commands['sendVideo'] = {} 
        self.commands['collectVideo'] = {}
        self.commands['flight'] = {}
        
    def setIperfCommand(self, iperfObj):
        self.commands['iperf'] = { "command" : "iperf", "protocol": iperfObj.protocol, "ipaddr": iperfObj.ipaddr, "port": iperfObj.port, "priority": iperfObj.priority } 
    def setCollectVideoCommand(self, collectVideoObj):
        self.commands['collectVideo'] = { "command" : "collectVideo", "dataformat" : collectVideoObj.dataformat, "duration": collectVideoObj.duration, "quality": collectVideoObj.quality, "priority": collectVideoObj.priority }
    def setSendVideoCommand(self, sendVideoObj):
        self.commands['sendVideo'] = { "command" : "sendVideo", "dataformat" : sendVideoObj.dataformat, "ipaddr": sendVideoObj.ipaddr, "port": sendVideoObj.port, "priority": sendVideoObj.priority  }
    def setFlightCommand(self, flightObj):
        self.commands['flight'] = { "command" : "flight", "destination" : flightObj.destination, "speed": flightObj.speed, "priority": flightObj.priority }
    def setMissionCommand(self, missionObj):
        self.commands['mission'] = { "command": "mission", "defaultWaypoints": missionObj.defaultWaypoints, "missionType": missionObj.missionType, "missionControl": missionObj.missionControl, "priority": missionObj.priority }

