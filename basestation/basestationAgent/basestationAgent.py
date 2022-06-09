#!/usr/bin/env python3
import socket
import pickle
import json
import geojson as gj
import sys
import pytz
import requests
from mobius.controller.controller import Controller

from flypawClasses import iperfInfo, sendVideoInfo, collectVideoInfo, flightInfo, missionInfo, resourceInfo, VehicleCommands, droneSim

#from cloud_resources import CloudResources

#sys.path.append('/root/Profiles/vehicle_control/aerpawlib/')
#from aerpawlib.util import Coordinate
#from aerpawlib.vehicle import Drone
#from aerpawlib.vehicle import Vehicle
#import dronekit

#import aerpawlib
from datetime import datetime

def getMissionLibraries(mission):
    thisMission = mission.__dict__
    missionLibraries = []
    if 'missionType' in thisMission:
        missiontype = thisMission['missionType']
        if missiontype == "bandwidth":
            #iperf
            missionLibraries.append("iperf3")
            #ffmpeg --> maybe move to a different mission
            missionLibraries.append("epel-release")
            
    return missionLibraries

def getMissionResourceCommands(mission):
    thisMission = mission.__dict__
    missionResourceCommands = []
    if 'missionType' in thisMission:
        missiontype = thisMission['missionType']
        if missiontype == "bandwidth":
            #open up the ports... maybe there is a more precise way to do this
            missionResourceCommands.append("sudo iptables -P INPUT ACCEPT")
            #run iperf3
            missionResourceCommands.append("iperf3 --server -J -D --logfile iperf3.txt")
            #run ffmpeg
            #for centos7 have to complete install before running
            missionResourceCommands.append("sudo yum localinstall --nogpgcheck https://download1.rpmfusion.org/free/el/rpmfusion-free-release-7.noarch.rpm")
            missionResourceCommands.append("sudo yum install ffmpeg");
            missionResourceCommands.append("mkdir /home/cc/ffmpeg");
            missionResourceCommands.append("ffmpeg -i udp://172.16.0.1:23000 -c copy -flags +global_header -f segment -segment_time 10 -segment_format_options movflags=+faststart -reset_timestamps 1 /home/cc/ffmpeg/test%d.mp4 -nostdin &")
            
    return missionResourceCommands

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

class FlyPawBasestationAgent(object):
    def __init__(self, ipaddr="172.16.0.1", port=20001, chunkSize=1024) :
        self.ipaddr = ipaddr
        self.port = port
        self.chunkSize = chunkSize
        self.iperf3Agent = iperfInfo()
        self.videoTransferAgent = sendVideoInfo()
        self.videoCollectionAgent = collectVideoInfo()
        self.flightInfo = flightInfo()
        self.missions = []
        self.currentRequests = []
        self.iperfHistory = []
        self.resourceList = []
        #self.drone = Drone() #our digital twin
        self.droneSim = droneSim()
        self.vehicleCommands = VehicleCommands()
        self.vehicleCommands.setIperfCommand(self.iperf3Agent)
        self.vehicleCommands.setCollectVideoCommand(self.videoCollectionAgent)
        self.vehicleCommands.setSendVideoCommand(self.videoTransferAgent)
        self.acs = "https://casa-denton3.noaa.unt.edu:8091/casaAlert/flightPath"
        self.usrname = "admin"
        self.password = "shabiz"
        self.updateURL = "https://casa-denton3.noaa.unt.edu:8091/casaAlert/flightUpdate"
        #for mission data, we should probably be checking elsewhere... for now we'll just define a mission here:
        mission = missionInfo()
        mission.name = "AERPAW"
        mission.missionType = "bandwidth" #"videography"
        mission.missionLeader = "drone" #or basestation or cloud
        mission.priority = 1
        mission.planfile = "./plans/mission.plan"
        mission.default_waypoints = []
        plan = getPlanFromPlanfile(mission.planfile)
        processedPlan = processPlan(plan)
        mission.default_waypoints = processedPlan['default_waypoints']
        self.missions.append(mission)
        self.cloud_mgr = Controller(config_file_location="./config.yml")

    def update_digital_twin(self):
        """
        function call to update the digital twin with different types of incoming data   
        """
        return
    
    def handle_telemetry(self, msg):
        """
        do things like send to digital twin and ACS
        """
        if msg['type'] == "telemetry":
            print("update self coordinates")
            if msg['telemetry']['position'] is not None:
                self.droneSim.position = msg['telemetry']['position']
            if msg['telemetry']['battery'] is not None:
                self.droneSim.battery = msg['telemetry']['battery']
            #if msg['telemetry']['attitude'] is not None:
            #self.drone.attitude.pitch = msg['telemetry']['attitude']['pitch']
            #self.drone.attitude.yaw = msg['telemetry']['attitude']['yaw']
            #self.drone.attitude.roll = msg['telemetry']['attitude']['roll']
            if msg['telemetry']['heading'] is not None:
                self.droneSim.heading = msg['telemetry']['heading']
            if msg['telemetry']['home'] is not None:
                self.droneSim.home = msg['telemetry']['home']
            if msg['telemetry']['nextWaypoint'] is not None:
                self.droneSim.nextWaypoint = msg['telemetry']['nextWaypoint']
            
        #self.update_digital_twin(msg)
        acsUpdate = self.update_acs()
        print(acsUpdate)
        return

    def update_acs(self):
        postData = {}
        postData['type'] = 'Feature'
        
        geometry = {}
        geometry['type'] = 'Point'

        currentLocation = []
        currentLocation.append(self.droneSim.position.lon)
        currentLocation.append(self.droneSim.position.lat)
        currentLocation.append(self.droneSim.position.alt)

        geometry['coordinates'] = currentLocation
        #geometry['coordinates'] = self.droneSim.position
        postData['geometry'] = geometry
        
        properties = {}
        #just use the first mission name for now
        properties['eventName'] = self.missions[0].name
        properties['locationTimestamp'] = self.droneSim.position.time
        
        nextWP = {}
        nextWPGeo = {}
        nextWPGeo['type'] = 'Point'
        #nextWaypoint = []
        #nextWaypoint.append(self.droneSim.nextWaypoint.lon)
	#nextWaypoint.append(self.droneSim.nextWaypoint.lat)
	#nextWaypoint.append(self.droneSim.nextWaypoint.alt)
        #nextWPGeo['coordinates'] = nextWaypoint
        nextWPGeo['coordinates'] = []
        nextWPGeo['coordinates'].append(self.droneSim.nextWaypoint[0])
        nextWPGeo['coordinates'].append(self.droneSim.nextWaypoint[1])
        nextWPGeo['coordinates'].append(self.droneSim.nextWaypoint[2])
        
        nextWP['geometry'] = nextWPGeo
        nextWP['type'] = 'Feature'
        properties['nextWaypoint'] = nextWP        
        properties['userProperties'] = {}
        properties['userProperties']['heading'] = self.droneSim.heading
        postData['properties'] = properties
        post_json_data = json.dumps(postData)

        postParameters = {}
        postParameters['json'] = post_json_data
        flightupdateresp = requests.post(self.updateURL, auth=(self.usrname, self.password), data=postParameters)
        updateResp = {}
        updateResp['registrationStatusCode'] = flightupdateresp.status_code
        #print(flightsubmitresp.status_code)
        if flightupdateresp.status_code == 200:
            updateResp['registration'] = "OK"
        else:
            updateResp['registration'] = "FAILED"
        return updateResp['registration']
            
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

                ##############check message type from drone and decide what to do###################
                if msgType == "mission":
                    msgFromServer['missions'] = self.missions
                    
                elif msgType == "acceptMission":

                    #register in ACS  (once it's working move it down below the get resources
                    
                    """
                    ACS registration
                    """
                    print("register in ACS")
                    
                    lineString = gj.LineString(self.missions[0].default_waypoints)
                    userProperties = {}
                    featureList = []
                    userProperties['classification'] = "scheduledFlight";
                    eventName = self.missions[0].name
                    #utcnow = datetime.utcnow()
                    #startTime = utcnow.isoformat(sep='T')
                    currentUnixsecs = datetime.now(tz=pytz.UTC).timestamp()
                    laterUnixsecs = currentUnixsecs + 1800 #half an hour from now
                    currentDT = datetime.fromtimestamp(currentUnixsecs, tz=pytz.UTC)
                    laterDT = datetime.fromtimestamp(laterUnixsecs, tz=pytz.UTC)
                    startTime = currentDT.strftime("%Y-%m-%dT%H:%M:%S+00:00")
                    endTime = laterDT.strftime("%Y-%m-%dT%H:%M:%S+00:00")

                    feature = gj.Feature(geometry=lineString, properties={"eventName": eventName, "startTime": startTime, "endTime": endTime, "userProperties": userProperties, "products": [{"hazard": "MRMS_PRECIP", "parameters": [{"thresholdUnits": "inph", "comparison": ">=", "distance": 5, "distanceUnits": "miles", "threshold": 0.1}]}]})
                    featureList.append(feature)
                    fc = gj.FeatureCollection(featureList)
                    dumpFC = gj.dumps(fc, sort_keys=True)
                    FC_data = {'json': dumpFC}
                    flightsubmitresp = requests.post(self.acs, auth=(self.usrname, self.password), data=FC_data)
                    registerResp = {}
                    registerResp['registrationStatusCode'] = flightsubmitresp.status_code
                    print(flightsubmitresp.status_code)
                    if flightsubmitresp.status_code == 200:
                        registerResp['registration'] = "OK"
                    else:
                        registerResp['registration'] = "FAILED"

                    #get cloud resources and configure to mission
                    self.cloud_mgr.create()
                    
                    slices = self.cloud_mgr.get_resources()
                    for s in slices:
                        for n in s.get_nodes():
                            thisResourceInfo = resourceInfo()
                            thisResourceInfo.name = n.get_name()
                            thisResourceInfo.location = "KVM@TACC" #extract algorithmically
                            thisResourceInfo.purpose = "mission" #get from mission somehow
                            
                            m_ip = ("management", n.get_management_ip())
                            e_ip = ("external", n.get_management_ip()) #for fabric these will not be the same 
                            thisResourceInfo.resourceAddresses.append(m_ip)
                            thisResourceInfo.resourceAddresses.append(e_ip)
                            thisResourceInfo.state = n.get_reservation_state()
                            self.resourceList.append(thisResourceInfo)

                    
                    # configure nodes
                    """
                    Mission Library Installation on Cloud Nodes
                    """
                    # need a mapping function of mission libraries to nodes... maybe for multiple missions also
                    # for now just use the first mission and install all libraries on all nodes
                    missionLibraries = getMissionLibraries(self.missions[0])

                    for s in slices:
                        for node in s.get_nodes():
                            nodeName = node.get_name()
                            print("Install Libraries for nodeName: " + nodeName)
                            #getRepoStr = "wget 'http://mirror.centos.org/centos/8-stream/BaseOS/x86_64/os/Packages/centos-gpg-keys-8-3.el8.noarch.rpm'"
                            #installRepoStr = "sudo rpm -i 'centos-gpg-keys-8-3.el8.noarch.rpm'"
                            #swapRepoStr = "sudo dnf -y --disablerepo '*' --enablerepo=extras swap centos-linux-repos centos-stream-repos"
                            stdout, stderr = node.execute(getRepoStr)
                            print(stdout)
                            print(stderr)
                            stdout, stderr = node.execute(installRepoStr)
                            print(stdout)
                            print(stderr)
                            stdout, stderr = node.execute(swapRepoStr)
                            print(stdout)
                            print(stderr)
                            for library in missionLibraries:
                                #libraryInstallStr = "sudo dnf -y install " + library #centos8 
                                libraryInstallStr = "sudo yum -y install " + library #centos7
                                print(nodeName + ": " + libraryInstallStr)
                                stdout, stderr = node.execute(libraryInstallStr)
                                print(stdout)
                                print(stderr)

                    # ideally this would be coordinated be done through KubeCtl or something, but initially we'll 
                    # just start up the iperf3 server in configuration
                    missionResourceCommands = getMissionResourceCommands(self.missions[0])
                    for s in slices:
                        for node in s.get_nodes():
                            nodeName = node.get_name()
                            print("Run Commands for nodeName: " + nodeName)
                            for command in missionResourceCommands:
                                print("command: " + command)
                                stdout, stderr = node.execute(command)
                                print(stdout)
                                print(stderr)

                    msgFromServer['missionstatus'] = "confirmed"
                    
                elif msgType == "resourceInfo":
                    msgFromServer['resources'] = self.resourceList 
                    
                elif msgType == "telemetry":
                    #update your digital twin, update registry, pass on to downstream applications
                    self.handle_telemetry(clientMessage)
                    
                    #set command based on mission
                    print("received telemetry, asking for iperf")
                    self.currentRequests.append(self.vehicleCommands.commands['iperf']) # iperf as default            

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
                elif msgType == "abortMission":
                    # delete the cloud resources
                    self.cloud_mgr.delete()
                else:
                    print("msgType: " + msgType)
                    self.currentRequests.append(self.vehicleCommands.commands['flight'])
                try: 
                    serialMsgFromServer = pickle.dumps(msgFromServer)
                    UDPServerSocket.sendto(serialMsgFromServer, address)
                except pickle.PicklingError as pe:
                    print ("cannot encode reply msg: " + pe)
                
            except pickle.UnpicklingError as upe:
                print("cannot decode message from drone: " + upe)


if __name__ == '__main__':
    FPBA = FlyPawBasestationAgent()
    FPBA.basestationDispatch()
