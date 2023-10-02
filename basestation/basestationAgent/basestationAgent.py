#!/usr/bin/env python3
import socket
import pickle
import json
import geojson as gj
import sys
import pytz
import requests
import time
from datetime import datetime
from mobius.controller.controller import Controller
from flypawClasses import iperfInfo, sendVideoInfo, sendFrameInfo, collectVideoInfo, flightInfo, missionInfo, resourceInfo, VehicleCommands, droneSim
from prometheusInterface import configurePrometheusForResources
from missionDefinition import configureBasestationProcesses, getMissionLibraries, getMissionResourcesCommands, getMissionCompletionCommands, 
from flightPlanning import getPlanFromPlanfile, processPlan
from acsInterface import registerACS, updateACS

#sys.path.append('/root/Profiles/vehicle_control/aerpawlib/')
#from aerpawlib.util import Coordinate
#from aerpawlib.vehicle import Drone
#from aerpawlib.vehicle import Vehicle
#import dronekit

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

        #for now we'll statically define a mission here:
        mission = missionInfo()
        mission.name = "AERPAW"
        mission.missionType = "fire" #"bandwidth", "videography", "fire"
        mission.missionLeader = "basestation" #drone or basestation or cloud
        mission.priority = 1
        mission.planfile = "./plans/mission.plan"
        mission.default_waypoints = []
        plan = getPlanFromPlanfile(mission.planfile)
        processedPlan = processPlan(plan)
        mission.default_waypoints = processedPlan['default_waypoints']
        mission.resources = False
        self.missions.append(mission)

        #if you want external (ie. Fabric or Chameleon) resources, set mission.resources to true and update config.yml
        if mission.resources:
            self.cloud_mgr = Controller(config_file_location="./config.yml")
        else:
            self.cloud_mgr = None
    
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
            acsUpdate = self.updateACS(self.droneSim, mission.name, self.updateURL, self.usrname, self.password)
            print(acsUpdate)

        #set command based on mission
        if self.missions[0].missionType == "Bandwidth":
            print("received telemetry, asking for iperf")
            self.currentRequests.append(self.vehicleCommands.commands['iperf']) # iperf as default

        if self.missions[0].missionType == "fire":
            print("received telemetry, asking for iperf")
            self.currentRequests.append(self.vehicleCommands.commands['iperf']) # iperf as default
            
        return
            
    def basestationDispatch(self):
        '''
        basestationDispatch is a udp based listening socket that the drone uses as a mission managing agent
        for example... drone->requests mission basestationDispatch-> provides mission  etc.   
        '''
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
                    #if you have an outside connection only
                    if self.missions[0].resources:
                        """
                        ACS registration
                        """
                        registered = self.registerACS(mission.default_waypoints, mission.name, self.acs, self.usrname, self.password)
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
                                thisResourceInfo.location = "KVM@TACC" #todo: extract algorithmically
                                thisResourceInfo.purpose = "mission" #todo: get dynamically from mission

                                #get the relevant IP addresses
                                m_ip = ("management", n.get_management_ip())
                                e_ip = ("external", n.get_external_ip()) 
                                thisResourceInfo.resourceAddresses.append(m_ip)
                                thisResourceInfo.resourceAddresses.append(e_ip)
                                thisResourceInfo.state = n.get_reservation_state()
                                self.resourceList.append(thisResourceInfo)
                        print("giving resources 60 seconds to come online")
                        time.sleep(60)

                    # Now that you have the resource IP addresses, configure anything you need to on the basestation
                    fail = configureBasestationProcesses(self.missions[0],self.resourceList)
                    if (fail):
                        #if your basestation configuration fails, cancel the mission and release the resources
                        msgFromServer['missionstatus'] = "canceled"

                        if self.missions[0].resources:
                            #delete the cloud resources 
                            for s in slices:
                                for n in s.get_nodes():
                                    n.delete()
                            #self.cloud_mgr.delete()
                            return
                    
                    if self.missions[0].resources:
                        # now configure resource nodes
                        """
                        Mission Library Installation on Cloud Nodes
                        """
                        missionLibraries = getMissionLibraries(self.missions[0], self.resourceList)

                        for s in slices:
                            nodeno = 0
                            for node in s.get_nodes():
                                nodeName = node.get_name()
                                print("Install Libraries for nodeName: " + nodeName)
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
                    #todo migrate to getMissionCompletionCommands
                    #missionCompletionCommands = getMissionCompletionCommands(self.missions[0],self.resourceList)
                    if self.missions[0].resources:
                        for s in slices:
                            #nodeno = 0
                            for node in s.get_nodes():
                                nodeName = node.get_name()
                                print("Run Commands for nodeName: " + nodeName)
                                #download your log files from the cloud
                                logTime = datetime.now().astimezone().isoformat()
                                iperfLogfile = "/root/Results/" + nodeName + "_iperf_" + str(logTime) + ".log"
                                node.download_file(iperfLogfile, "/home/cc/iperf3.txt", retry=3, retry_interval=5)
                                darknetLogfile = "/root/Results/" + nodeName + "_darknet_" + str(logTime) + ".log"
                                node.download_file(darknetLogfile, "/home/cc/darknet.log", retry=3, retry_interval=5)
                                #delete resource
                                print("Deleting: " + nodeName)
                                nodeDelete = node.delete()

                    print("flight complete")
                    sys.exit()
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
