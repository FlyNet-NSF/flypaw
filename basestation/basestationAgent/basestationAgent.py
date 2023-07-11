#!/usr/bin/env python3
from http import client
import socket
import pickle
import json
from telnetlib import STATUS
import geojson as gj
import sys
import pytz
import requests
import time
#from mobius.controller.controller import Controller
from geographiclib.geodesic import Geodesic

from flypawClasses import iperfInfo, sendVideoInfo, sendFrameInfo, collectVideoInfo, flightInfo, missionInfo, resourceInfo, VehicleCommands, droneSim, MissionObjective, Position

#from cloud_resources import CloudResources

#sys.path.append('/root/Profiles/vehicle_control/aerpawlib/')
#from aerpawlib.util import Coordinate
#from aerpawlib.vehicle import Drone
#from aerpawlib.vehicle import Vehicle
#import dronekit

#import aerpawlib
from datetime import datetime

def configurePrometheusForResources(resources):
    prometheusReloadURL = "http://127.0.0.1:9090/-/reload"
    prometheus_config_array = []
    prometheus_config_obj = {}
    resource_ip_array = []
    for resource in resources:
        thisResourceInfo = resource.__dict__
        resourceAddresses = thisResourceInfo['resourceAddresses']
        externalIP = resourceAddresses[1][1]
        externalIPandPort = externalIP + ":8095"
        if externalIPandPort not in resource_ip_array:
            resource_ip_array.append(externalIPandPort)
        
    prometheus_config_obj['labels'] = {}
    prometheus_config_obj['labels']['job'] = "node"
    prometheus_config_obj['targets'] = resource_ip_array
    prometheus_config_array.append(prometheus_config_obj)
    try:
        with open("/root/prometheus/targets.json", "w") as ofile:
            json.dump(prometheus_config_array,ofile)
            ofile.close()
    except IOError:
        print("could not open prometheus config file")
        return 1
    #tell prometheus to reload config
    time.sleep(1)
    updateresp = requests.post(prometheusReloadURL, data={})
    if updateresp.status_code == 200:
        print("Prometheus configured and reloaded")
    else:
        print("Prometheus reload failed with status_code: " + str(status_code))
        return 1
    return 0

def configureBasestationProcesses(mission, resources):
    thisMission = mission.__dict__
    if 'missionType' in thisMission:
        missiontype = thisMission['missionType']
        if missiontype == "videography":
            #videography mission uses prometheus... configure and run
            prometheusFail = configurePrometheusForResources(resources)
            if (prometheusFail):
                return 1
        elif missiontype == "bandwidth":
            #could theoretically start iperf server, but punt for now
            return 1
        elif missiontype == "fire":
            #maybe start the udp video frame transfer server?
            #could theoretically start iperf server
            return 1
    return 0

                
def getMissionLibraries(mission, resources):
    thisMission = mission.__dict__
    if 'missionType' in thisMission:
        missiontype = thisMission['missionType']
        missionLibraries = []
        if missiontype == "bandwidth":
            for thisResource in resources: #same libraries for each resource in this case
                resourceLibraries = []
                resourceLibraries.append("iperf3")
                missionLibraries.append(resourceLibraries)
        elif missiontype == "videography":
            for thisResource in resources: #same libraries for each resource in this case
                resourceLibraries = []
                resourceLibraries.append("iperf3")
                resourceLibraries.append("epel-release")
                resourceLibraries.append("docker")
                missionLibraries.append(resourceLibraries)
        return missionLibraries
    else:
        return None

def getMissionCompletionCommands(mission, resources):
    #stub... unfinished
    thisMission = mission.__dict__

    if 'missionType' in thisMission:
        missiontype = thisMission['missionType']
        missionCompletionCommands = [] #one list of commands per resource
        if missiontype == "bandwidth":
            for thisResource in resources:
                thisResourceInfo = thisResource.__dict__
                #a list of commands for each resource
                completionCommands = []
                missionCompletionCommands.append(completionCommands)
        elif missiontype == "videography":
            for thisResource in resources:
                thisResourceInfo = thisResource.__dict__
                #a list of commands for each resource
                completionCommands = []
                missionCompletionCommands.append(completionCommands)
        return missionCompletionCommands

def getMissionResourcesCommands(mission, resources):
    thisMission = mission.__dict__
    
    if 'missionType' in thisMission:
        missiontype = thisMission['missionType']
        missionResourcesCommands = [] #one list of commands per resource
        if missiontype == "bandwidth":
            for thisResource in resources:
                thisResourceInfo = thisResource.__dict__
                missionResourceCommands = []
                #open up the ports... maybe there is a more precise way to do this
                missionResourceCommands.append("sudo iptables -P INPUT ACCEPT")
                #run iperf3
                missionResourceCommands.append("iperf3 --server -J -D --logfile /home/cc/iperf3.txt")
                missionResourcesCommands.append(missionResourceCommands)
        elif missiontype == "videography":
            for thisResource in resources:
                thisResourceInfo = thisResource.__dict__
                resourceAddresses = thisResourceInfo['resourceAddresses']
                #generally address 0 is management IP, address 1 external IP...they could be the same
                #resourceAddress is a pair eg. ['external', 'xxx.xxx.xxx.xxx']
                #could cycle through each address and look for external as first part of pair rather than just assume
                externalIP = resourceAddresses[1][1]
                missionResourceCommands = []
                #open up the ports... maybe there is a more precise way to do this
                missionResourceCommands.append("sudo iptables -P INPUT ACCEPT")
                #run iperf3
                missionResourceCommands.append("iperf3 --server -J -D --logfile /home/cc/iperf3.txt")
                #start docker
                missionResourceCommands.append("sudo systemctl start docker")
                #get prometheus node exporter 
                missionResourceCommands.append("wget https://github.com/prometheus/node_exporter/releases/download/v1.0.0-rc.0/node_exporter-1.0.0-rc.0.linux-amd64.tar.gz")
                #untar prometheus node exporter
                missionResourceCommands.append("sudo tar -zxvf node_exporter-1.0.0-rc.0.linux-amd64.tar.gz -C /opt")
                #run prometheus node exporter
                missionResourceCommands.append("nohup /opt/node_exporter-1.0.0-rc.0.linux-amd64/node_exporter --web.listen-address=':8095' > /home/cc/node_exporter.log 2>&1 &")
                #get darknet container
                missionResourceCommands.append("sudo docker pull papajim/detectionmodule")
                #clone coconet github
                missionResourceCommands.append("git clone https://github.com/papajim/pegasus-coconet.git")
                #make directory for incoming images
                missionResourceCommands.append("mkdir /home/cc/dataset");
                #get receive_file_udp to receive image files and run darknet
                missionResourceCommands.append("wget https://emmy8.casa.umass.edu/flypaw/cloud/receive_file_udp/receive_file_udp_send_coconet.py")
                #run receive_file_udp
                missionResourceCommands.append("nohup python3 receive_file_udp_send_coconet.py -o /home/cc/dataset -a '0.0.0.0' -p 8096 -b 4096 > /home/cc/receive_file_udp.log 2>&1 &")

                missionResourcesCommands.append(missionResourceCommands)
                #install ffmpeg for now... centos 7 requires the repo install
                #missionResourceCommands.append("sudo yum -y localinstall --nogpgcheck https://download1.rpmfusion.org/free/el/rpmfusion-free-release-7.noarch.rpm")
                #missionResourceCommands.append("sudo yum -y install ffmpeg");
                #missionResourceCommands.append("mkdir /home/cc/ffmpeg");
                #ffmpeg_cmd = "ffmpeg -nostdin -i udp://" + externalIP + ":23000 -c copy -flags +global_header -f segment -segment_time 10 -segment_format_options movflags=+faststart -reset_timestamps 1 /home/cc/ffmpeg/test%d.mp4 > /home/cc/ffmpeg/ffmpeg.log 2>&1 < /dev/null &"
                #ffmpeg_cmd = "ffmpeg -nostdin -i udp://" + externalIP + ":23000 -f mpegts udp://" + externalIP + ":24000"
                #missionResourceCommands.append(ffmpeg_cmd)
                
        return missionResourcesCommands
    else:
        return None
def getPlanFromPlanfile(filepath):
    f = open(filepath)
    pathdata = json.load(f)
    f.close()
    return pathdata
#This function processes the raw plan. It really should have a defined plan structure to pass to the Drone and back to the Main file...
def processPlan(plan):
    processedPlan = {}
    missionObjectives = []
    default_waypoints = []
    processedPlan['STATUS'] = "UNINITIALIZED" 
    if not plan['fileType'] == "TaskQ_Plan":
        print("Wrong Plan file Format")
        return processedPlan
    if not 'mission' in plan:
        print("No mission in planfile")
        return processedPlan
    if not 'plannedHomePosition' in plan['mission']:
        print("No planned home position")
        return processedPlan
    php = plan['mission']['plannedHomePosition']

    thisWaypoint = [php[1],php[0],0] #I don't want to append the the PLanned Home Position to the start anymore
    lastWaypoint = thisWaypoint
    if not 'items' in plan['mission']: #Empty mission
        print("No items")
        return processedPlan
    theseItems = plan['mission']['items']
    for thisItem in theseItems:
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
                position = Position()
                position.InitParams(thisWaypoint[0],thisWaypoint[1],thisWaypoint[2],0,0,0)
                objective = MissionObjective(position,thisItem['TASK'],False)
                missionObjectives.append(objective)

    print (default_waypoints)
    processedPlan['default_waypoints'] = default_waypoints
    processedPlan["STATUS"] = "PROCESSED"
    processedPlan["objectives"] = missionObjectives
    return processedPlan
"""
Dont really need this function right now, but I am keeping it around incase I want to be able to accept QGroundMission as well-------------------------------

def processPlan_QGROUND_STANDARD(plan):
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
"""

class FlyPawBasestationAgent(object):
    def __init__(self, ipaddr="172.16.0.1", port=20001, chunkSize=1024) :
        self.ipaddr = ipaddr
        self.port = port
        self.chunkSize = chunkSize
        self.iperf3Agent = iperfInfo()
        self.videoTransferAgent = sendVideoInfo()
        self.frameTransferAgent = sendFrameInfo()
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
        self.vehicleCommands.setSendFrameCommand(self.frameTransferAgent)
        self.acs = "https://casa-denton3.noaa.unt.edu:8091/casaAlert/flightPath"
        self.usrname = "admin"
        self.password = "shabiz"
        self.updateURL = "https://casa-denton3.noaa.unt.edu:8091/casaAlert/flightUpdate"
        #for mission data, we should probably be checking elsewhere... for now we'll just define a mission here:
        mission = missionInfo()
        mission.name = "AERPAW"
        mission.missionType = "fire" #"bandwidth", "videography", "fire"
        mission.missionLeader = "basestation" #drone or basestation or cloud
        mission.priority = 1
        mission.planfile = "./plans/simplePlan_TaskQ.plan"
        mission.default_waypoints = []
        plan = getPlanFromPlanfile(mission.planfile)
        processedPlan = processPlan(plan)
        if processedPlan['STATUS'] == "UNINITIALIZED":
            mission.STATUS = "FAILED"
        elif processedPlan['STATUS'] == "PROCESSED":
            mission.STATUS = "PROCESSED"
            mission.default_waypoints = processedPlan['default_waypoints']
            mission.missionObjectives = processedPlan['objectives']

        mission.resources = False
        self.missions.append(mission)
        if mission.resources:
            self.cloud_mgr = Controller(config_file_location="./config.yml")
        else:
            self.cloud_mgr = None
        self.RadioPosition = Position()
        self.RadioPosition.InitParams(-78.69607,35.72744,0,0,0,0)
        self.DistanceOfFailure = 150
        self.LastKnownDronePosition = self.RadioPosition



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

        if self.missions[0].resources:
            #only do this if we have an outside connection
            #self.update_digital_twin(msg)
            acsUpdate = self.update_acs()
            print(acsUpdate)

        #set command based on mission                                                                                                                                          
        if self.missions[0].missionType == "Bandwidth":
            print("received telemetry, asking for iperf")
            self.currentRequests.append(self.vehicleCommands.commands['iperf']) # iperf as default
            
        return

    def register_acs(self):
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
            print(json.dumps(registerResp))
            return True
        else:
            print("could not register flight in ACS")
            registerResp['registration'] = "FAILED"
            print(json.dumps(registerResp))
            return False
        
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
    #BASESTATION DISPATCH OLD -----------------VESTIGAL
    def basestationDispatch(self):
        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPServerSocket.bind((self.ipaddr, self.port))
        print("UDP server up and listening, IP:" + str(self.ipaddr) + " port: " + str(self.port))

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
                    validMissions = []

                    for ms in self.missions:
                        if ms.STATUS == "PROCESSED" :
                            validMissions.append(ms)
                    print("Dispatcher-- mission check" + str(validMissions[0].missionObjectives))
                    msgFromServer['missions'] = validMissions
                    
                    
                elif msgType == "acceptMission":
                    #if you have an outside connection only
                    if self.missions[0].resources:
                        #register in ACS  (once it's working move it down below the get resources
                        
                        """
                        ACS registration
                        """
                        registered = self.register_acs()
                        if not registered:
                            msgFromServer['missionstatus'] = "canceled"
                            return
                    
                        #if we're registered properly...
                        #get cloud resources and configure to mission
                        self.cloud_mgr.create()
                        time.sleep(3)
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
                        print("giving resources 60 seconds to come online")
                        time.sleep(60)

                    # Now that you have the IP addresses, configure anything on the basestation
                    fail = configureBasestationProcesses(self.missions[0],self.resourceList)
                    if (fail):
                        msgFromServer['missionstatus'] = "canceled"

                        if self.missions[0].resources:
                            #delete the cloud resources 
                            for s in slices:
                                for n in s.get_nodes():
                                    n.delete()
                            #self.cloud_mgr.delete()
                            return
                    
                    if self.missions[0].resources:
                        # now configure nodes...
                        """
                        Mission Library Installation on Cloud Nodes
                        """
                        missionLibraries = getMissionLibraries(self.missions[0], self.resourceList)

                        for s in slices:
                            nodeno = 0
                            for node in s.get_nodes():
                                nodeName = node.get_name()
                                print("Install Libraries for nodeName: " + nodeName)
                                #getRepoStr = "wget 'http://mirror.centos.org/centos/8-stream/BaseOS/x86_64/os/Packages/centos-gpg-keys-8-3.el8.noarch.rpm'"
                                #installRepoStr = "sudo rpm -i 'centos-gpg-keys-8-3.el8.noarch.rpm'"
                                #swapRepoStr = "sudo dnf -y --disablerepo '*' --enablerepo=extras swap centos-linux-repos centos-stream-repos"
                                #stdout, stderr = node.execute(getRepoStr)
                                #print(stdout)
                                #print(stderr)
                                #stdout, stderr = node.execute(installRepoStr)
                                #print(stdout)
                                #print(stderr)
                                #stdout, stderr = node.execute(swapRepoStr)
                                #print(stdout)
                                #print(stderr)
                                for library in missionLibraries[nodeno]:
                                    #libraryInstallStr = "sudo dnf -y install " + library #centos8 
                                    libraryInstallStr = "sudo yum -y install " + library #centos7
                                    print(nodeName + ": " + libraryInstallStr)
                                    stdout, stderr = node.execute(libraryInstallStr)
                                    print(stdout)
                                    print(stderr)
                                nodeno = nodeno + 1

                        #now install and run any preflight commands/configuration on the nodes
                        # ideally this would be coordinated be done through KubeCtl or something
                        missionResourcesCommands = getMissionResourcesCommands(self.missions[0],self.resourceList)
                        for s in slices:
                            nodeno = 0
                            for node in s.get_nodes():
                                nodeName = node.get_name()
                                print("Run Commands for nodeName: " + nodeName)
                                for command in missionResourcesCommands[nodeno]:
                                    print("command: " + command)
                                    stdout, stderr = node.execute(command)
                                    print(stdout)
                                    print(stderr)
                                nodeno = nodeno + 1

                    msgFromServer['missionstatus'] = "confirmed"
                    
                elif msgType == "resourceInfo":
                    msgFromServer['resources'] = self.resourceList 
                    
                elif msgType == "telemetry":
                    #update your digital twin, update registry, pass on to downstream applications
                    self.handle_telemetry(clientMessage)
                    
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
                            self.currentRequests.append(self.vehicleCommands.commands['sendFrame'])
                        else:
                            self.currentRequests.append(self.vehicleCommands.commands['flight'])
                    else:
                        self.currentRequests.append(self.vehicleCommands.commands['flight'])
                elif msgType == "sendFrame":
                    self.currentRequests.append(self.vehicleCommands.commands['flight'])
                elif msgType == "sendVideo":
                    self.currentRequests.append(self.vehicleCommands.commands['flight'])
                elif msgType == "abortMission":
                    print ("mission abort... prepare for landing")
                elif msgType == "completed":
                    #download your log files from the cloud
                    #missionCompletionCommands = getMissionCompletionCommands(self.missions[0],self.resourceList)
                    if self.missions[0].resources:
                        for s in slices:
                            #nodeno = 0
                            for node in s.get_nodes():
                                nodeName = node.get_name()
                                print("Run Commands for nodeName: " + nodeName)
                                logTime = datetime.now().astimezone().isoformat()
                                iperfLogfile = "/root/Results/" + nodeName + "_iperf_" + str(logTime) + ".log"
                                node.download_file(iperfLogfile, "/home/cc/iperf3.txt", retry=3, retry_interval=5)
                                darknetLogfile = "/root/Results/" + nodeName + "_darknet_" + str(logTime) + ".log"
                                node.download_file(darknetLogfile, "/home/cc/darknet.log", retry=3, retry_interval=5)
                            
                                #for command in missionResourcesCommands[nodeno]:
                                #    print("command: " + command)
                                #    stdout, stderr = node.execute(command)
		                #    print(stdout)
                                #    print(stderr)
                                #nodeno = nodeno + 1
                                print("Deleting: " + nodeName)
                                nodeDelete = node.delete()

                                # delete the cloud resources
                                #self.cloud_mgr.delete()
                    print("flight complete")
                    sys.exit()
                else:
                    print("msgType: " + msgType)
                    self.currentRequests.append(self.vehicleCommands.commands['flight'])
                try: 
                    serialMsgFromServer = pickle.dumps(msgFromServer)
                    print("Pickle Packet Size: " + str(len(pickle.dumps(msgFromServer,-1))))
                    UDPServerSocket.sendto(serialMsgFromServer, address)
                except pickle.PicklingError as pe:
                    print ("cannot encode reply msg: " + pe)
                
            except pickle.UnpicklingError as upe:
                print("cannot decode message from drone: " + upe)

    def DroneDistance(self, dronePosition):
        geo = Geodesic.WGS84.Inverse(dronePosition.lat, dronePosition.lon, self.RadioPosition.lat, self.RadioPosition.lon)
        distance_to_base = geo.get('s12')
        return distance_to_base



    def basestationDispatch_SIM(self):#Simulates an unreliable connection. Doesn't respond if there is no connection
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
                msgFromServer['drone_position'] = clientMessage['CUR_POS']
                self.LastKnownDronePosition = clientMessage['CUR_POS']
                ##############check message type from drone and decide what to do###################
                if msgType == "mission":
                    validMissions = []

                    for ms in self.missions:
                        if ms.STATUS == "PROCESSED" :
                            validMissions.append(ms)
                    print("Dispatcher-- mission check" + str(validMissions[0].missionObjectives))
                    msgFromServer['missions'] = validMissions
                    
                    
                elif msgType == "acceptMission":
                    #if you have an outside connection only
                    if self.missions[0].resources:
                        #register in ACS  (once it's working move it down below the get resources
                        
                        """
                        ACS registration
                        """
                        registered = self.register_acs()
                        if not registered:
                            msgFromServer['missionstatus'] = "canceled"
                            return
                    
                        #if we're registered properly...
                        #get cloud resources and configure to mission
                        self.cloud_mgr.create()
                        time.sleep(3)
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
                        print("giving resources 60 seconds to come online")
                        time.sleep(60)

                    # Now that you have the IP addresses, configure anything on the basestation
                    fail = configureBasestationProcesses(self.missions[0],self.resourceList)
                    if (fail):
                        msgFromServer['missionstatus'] = "canceled"

                        if self.missions[0].resources:
                            #delete the cloud resources 
                            for s in slices:
                                for n in s.get_nodes():
                                    n.delete()
                            #self.cloud_mgr.delete()
                            return
                    
                    if self.missions[0].resources:
                        # now configure nodes...
                        """
                        Mission Library Installation on Cloud Nodes
                        """
                        missionLibraries = getMissionLibraries(self.missions[0], self.resourceList)

                        for s in slices:
                            nodeno = 0
                            for node in s.get_nodes():
                                nodeName = node.get_name()
                                print("Install Libraries for nodeName: " + nodeName)
                                #getRepoStr = "wget 'http://mirror.centos.org/centos/8-stream/BaseOS/x86_64/os/Packages/centos-gpg-keys-8-3.el8.noarch.rpm'"
                                #installRepoStr = "sudo rpm -i 'centos-gpg-keys-8-3.el8.noarch.rpm'"
                                #swapRepoStr = "sudo dnf -y --disablerepo '*' --enablerepo=extras swap centos-linux-repos centos-stream-repos"
                                #stdout, stderr = node.execute(getRepoStr)
                                #print(stdout)
                                #print(stderr)
                                #stdout, stderr = node.execute(installRepoStr)
                                #print(stdout)
                                #print(stderr)
                                #stdout, stderr = node.execute(swapRepoStr)
                                #print(stdout)
                                #print(stderr)
                                for library in missionLibraries[nodeno]:
                                    #libraryInstallStr = "sudo dnf -y install " + library #centos8 
                                    libraryInstallStr = "sudo yum -y install " + library #centos7
                                    print(nodeName + ": " + libraryInstallStr)
                                    stdout, stderr = node.execute(libraryInstallStr)
                                    print(stdout)
                                    print(stderr)
                                nodeno = nodeno + 1

                        #now install and run any preflight commands/configuration on the nodes
                        # ideally this would be coordinated be done through KubeCtl or something
                        missionResourcesCommands = getMissionResourcesCommands(self.missions[0],self.resourceList)
                        for s in slices:
                            nodeno = 0
                            for node in s.get_nodes():
                                nodeName = node.get_name()
                                print("Run Commands for nodeName: " + nodeName)
                                for command in missionResourcesCommands[nodeno]:
                                    print("command: " + command)
                                    stdout, stderr = node.execute(command)
                                    print(stdout)
                                    print(stderr)
                                nodeno = nodeno + 1

                    msgFromServer['missionstatus'] = "confirmed"
                    
                elif msgType == "resourceInfo":
                    msgFromServer['resources'] = self.resourceList 
                    
                elif msgType == "telemetry":
                    #update your digital twin, update registry, pass on to downstream applications
                    self.handle_telemetry(clientMessage)
                    
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
                            self.currentRequests.append(self.vehicleCommands.commands['sendFrame'])
                        else:
                            self.currentRequests.append(self.vehicleCommands.commands['flight'])
                    else:
                        self.currentRequests.append(self.vehicleCommands.commands['flight'])
                elif msgType == "sendFrame":
                    self.currentRequests.append(self.vehicleCommands.commands['flight'])
                elif msgType == "sendVideo":
                    self.currentRequests.append(self.vehicleCommands.commands['flight'])
                elif msgType == "abortMission":
                    print ("mission abort... prepare for landing")
                elif msgType == "completed":
                    #download your log files from the cloud
                    #missionCompletionCommands = getMissionCompletionCommands(self.missions[0],self.resourceList)
                    if self.missions[0].resources:
                        for s in slices:
                            #nodeno = 0
                            for node in s.get_nodes():
                                nodeName = node.get_name()
                                print("Run Commands for nodeName: " + nodeName)
                                logTime = datetime.now().astimezone().isoformat()
                                iperfLogfile = "/root/Results/" + nodeName + "_iperf_" + str(logTime) + ".log"
                                node.download_file(iperfLogfile, "/home/cc/iperf3.txt", retry=3, retry_interval=5)
                                darknetLogfile = "/root/Results/" + nodeName + "_darknet_" + str(logTime) + ".log"
                                node.download_file(darknetLogfile, "/home/cc/darknet.log", retry=3, retry_interval=5)
                            
                                #for command in missionResourcesCommands[nodeno]:
                                #    print("command: " + command)
                                #    stdout, stderr = node.execute(command)
		                #    print(stdout)
                                #    print(stderr)
                                #nodeno = nodeno + 1
                                print("Deleting: " + nodeName)
                                nodeDelete = node.delete()

                                # delete the cloud resources
                                #self.cloud_mgr.delete()
                    print("flight complete")
                    sys.exit()
                else:
                    print("msgType: " + msgType)
                    self.currentRequests.append(self.vehicleCommands.commands['flight'])
                try: 
                    serialMsgFromServer = pickle.dumps(msgFromServer)
                    print("Pickle Packet Size: " + str(len(pickle.dumps(msgFromServer,-1))))
                    droneDistance = self.DroneDistance(self.LastKnownDronePosition)
                    print("Distance to Drone: "+str(droneDistance)+" m")
                    if(droneDistance<=self.DistanceOfFailure):
                        UDPServerSocket.sendto(serialMsgFromServer, address)
                    else:
                        print("Too far...SimulatingBrokenConnection!")

                except pickle.PicklingError as pe:
                    print ("cannot encode reply msg: " + pe)
                
            except pickle.UnpicklingError as upe:
                print("cannot decode message from drone: " + upe)




if __name__ == '__main__':
    FPBA = FlyPawBasestationAgent()
    FPBA.basestationDispatch_SIM()
