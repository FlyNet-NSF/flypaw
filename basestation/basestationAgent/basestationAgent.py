import socket
import pickle
import json
import sys
#from aerpawlib.vehicle import Drone
#from aerpawlib.vehicle import Vehicle
#import dronekit

#import aerpawlib
from datetime import datetime

def getPlanFromPlanfile(filepath):
    f = open(filepath)
    pathdata = json.load(f)
    f.close()
    return pathdata

def processPlan(plan):
    processedPlan = {}
    default_waypoints = []
    if not 'mission' in plan:
        print("No mission in planfile")
        return None
    if not 'plannedHomePosition' in plan['mission']:
        print("No planned home position")
        return None
    php = plan['mission']['plannedHomePosition']

    thisWaypoint = [php[1],php[0],0]
    default_waypoints.append(thisWaypoint)
    lastWaypoint = thisWaypoint
    if not 'items' in plan['mission']:
        print("No items")
        return None
    theseItems = plan['mission']['items']
    for thisItem in theseItems:
        if 'autocontinue' in thisItem:
            if thisItem['autocontinue'] == True:
                print ("ignore autocontinue")
                thisWaypoint = [php[1],php[0],lastWaypoint[2]]
                processedPlan['default_waypoints'] = default_waypoints
                thisWaypoint = [php[1],php[0],0]
                default_waypoints.append(thisWaypoint)
        if 'params' in thisItem:
            if not len(thisItem['params']) == 7:
                print("incorrect number of params")
            else:
                thisWaypoint = [thisItem['params'][5], thisItem['params'][4], thisItem['params'][6]]
                if thisWaypoint[0] == 0:
                    thisWaypoint[0] = lastWaypoint[0]
                if thisWaypoint[1] == 0:
                    thisWaypoint[1] = lastWaypoint[1]
                default_waypoints.append(thisWaypoint)
                lastWaypoint = thisWaypoint

    print (default_waypoints)
    processedPlan['default_waypoints'] = default_waypoints
    return processedPlan

class IperfInfo(object):
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
        

class FlyPawBasestationAgent(object):
    def __init__(self, ipaddr="172.16.0.1", port=20001, chunkSize=1024) :
        self.ipaddr = ipaddr
        self.port = port
        self.chunkSize = chunkSize
        self.iperf3Agent = IperfInfo()
        self.videoTransferAgent = sendVideoInfo()
        self.videoCollectionAgent = collectVideoInfo()
        self.flightInfo = flightInfo()
        self.missions = []
        self.currentRequests = []
        self.iperfHistory = []
        #self.drone = Drone() #our digital twin
        self.vehicleCommands = VehicleCommands()
        self.vehicleCommands.setIperfCommand(self.iperf3Agent)
        self.vehicleCommands.setCollectVideoCommand(self.videoCollectionAgent)
        self.vehicleCommands.setSendVideoCommand(self.videoTransferAgent)
        #for mission data, we should probably be checking elsewhere... for now we'll just define a mission here:
        mission = missionInfo()
        mission.missionType = "videography"
        mission.missionLeader = "basestation"
        mission.priority = 1
        mission.planfile = "./plans/mission.plan"
        mission.default_waypoints = []
        plan = getPlanFromPlanfile(mission.planfile)
        processedPlan = processPlan(plan)
        mission.default_waypoints = processedPlan['default_waypoints']
        self.missions.append({'missionType': mission.missionType, 'missionLeader': mission.missionLeader, 'default_waypoints': mission.default_waypoints, 'priority': mission.priority})
        
    def basestationDispatch(self):
        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPServerSocket.bind((self.ipaddr, self.port))
        print("UDP server up and listening")

        while(True):
            msgFromServer = {}
            bytesAddressPair = UDPServerSocket.recvfrom(self.chunkSize)
            serialClientMessage = bytesAddressPair[0]
            address = bytesAddressPair[1]
            try:
                clientMessage = pickle.loads(serialClientMessage)    
                print(clientMessage['type'])
        
                recvdMsg = "Message from Drone:{}".format(clientMessage)
                clientIP  = "Drone IP Address:{}".format(address)
                print(recvdMsg)
                print(clientIP)
                recvTime = datetime.now().astimezone().isoformat()
                msgFromServer['time_received'] = recvTime
                recvUUID = clientMessage['uuid']
                msgFromServer['uuid_received'] = recvUUID
                msgType = clientMessage['type']
                msgFromServer['type_received'] = msgType
                if msgType == "telemetry":
                    #update your digital twin, update registry, pass on to downstream applications
                    #handle_telemetry(clientMessage)

                    #set command based on mission
                    self.currentRequests.append(self.vehicleCommands.commands['iperf']) # iperf as default            

                elif msgType == "acceptMission":
                    #get final approval of DCB
                    #do any preflight resource reservation with Mobius, etc
                    #register flight in ACS or wherever
                    #if all good
                    msgFromServer['missionstatus'] = "confirmed"
                    
                elif msgType == "instructionRequest":
                    msgFromServer['requests'] = self.currentRequests
                    self.currentRequests = []
                elif msgType == "iperfResults":
                    self.iperf3Agent.ipaddr = clientMessage[msgType]['ipaddr']
                    self.iperf3Agent.port = clientMessage[msgType]['port']
                    self.iperf3Agent.protocol = clientMessage[msgType]['protocol']
                    self.iperf3Agent.mbps = clientMessage[msgType]['mbps']
                    self.iperf3Agent.meanrtt = clientMessage[msgType]['meanrtt']
                    self.iperf3Agent.location4d = clientMessage[msgType]['location4d']
                    self.iperfHistory.append(self.iperf3Agent)
                    if self.iperf3Agent.mbps is not None:
                        if self.iperf3Agent.mbps > 1:
                            self.currentRequests.append(self.vehicleCommands.commands['sendVideo'])
                        else:
                            self.currentRequests.append(self.vehicleCommands.commands['flight'])
                    else:
                        self.currentRequests.append(self.vehicleCommands.commands['flight'])
                elif msgType == "sendVideo":
                    self.currentRequests.append(self.vehicleCommands.commands['flight'])
                elif msgType == "mission":
                    msgFromServer['missions'] = self.missions
                try: 
                    serialMsgFromServer = pickle.dumps(msgFromServer)
                    UDPServerSocket.sendto(serialMsgFromServer, address)
                except pickle.PicklingError as pe:
                    print ("cannot encode reply msg: " + pe)
                
            except pickle.UnpicklingError as upe:
                print ("cannot decode message from drone: " + upe)

    def handle_telemetry(self, tm):
        """
        function to apply to received telemetry message (tm in function call) from drone 
        update digital twin
        update registration system
        pass on to downstream functions
        """
        update_digital_twin(tm)
        #update_acs
        #maybe send digital twin somewhere in the cloud for sim
        
        
    def update_digital_twin(self, msg):
        """
        function call to update the digital twin with different types of incoming data
        """
        if msg['type'] == "telemetry":
            print("update twin with telemetry")
            if msg['telemetry']['position'] is not None:
                self.drone.position.lat = msg['telemetry']['position'][0]
                self.drone.position.lon = msg['telemetry']['position'][1]
                self.drone.position.alt = msg['telemetry']['position'][2]
                self.drone.position.time = msg['telemetry']['position'][3]
            if msg['telemetry']['gps'] is not None:
                self.drone.gps.fix_type = msg['telemetry']['gps']['fix_type']
                self.drone.gps.satellites_visible = msg['telemetry']['gps']['satellites_visible']
            if msg['telemetry']['battery'] is not None:
                self.drone.battery.voltage = msg['telemetry']['battery']['voltage'] 
                self.drone.battery.current = msg['telemetry']['battery']['current']
                self.drone.battery.level = msg['telemetry']['battery']['level']
            #if msg['telemetry']['attitude'] is not None:
                #self.drone.attitude.pitch = msg['telemetry']['attitude']['pitch']
                #self.drone.attitude.yaw = msg['telemetry']['attitude']['yaw']
                #self.drone.attitude.roll = msg['telemetry']['attitude']['roll']
            if msg['telemetry']['heading'] is not None:
                self.drone.heading = msg['telemetry']['heading']
            if msg['telemetry']['home'] is not None:
                self.drone.home_coords.lat = msg['telemetry']['home'][0]
                self.drone.home_coords.lon = msg['telemetry']['home'][1]
                self.drone.home_coords.alt = msg['telemetry']['home'][2]
            
if __name__ == '__main__':
    FPBA = FlyPawBasestationAgent()
    FPBA.basestationDispatch()
