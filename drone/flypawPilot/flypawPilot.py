from argparse import Action
from ast import Str
import asyncio
from calendar import c
from dis import dis
from turtle import back, position
from typing import Iterator
import requests
import json
import jsonpickle


#import geojson
import time
import sys
import os
import iperf3
import socket
import pickle
import uuid
import select
import ffmpeg
#import pika                                                                                                                                                               
import threading
import random
import dronekit
#from pymavlink import mavutil
#from geopy.distance import lonlat, distance, Distance                                                                                                                     
#from geopy import Point
from geographiclib.geodesic import Geodesic
#from distutils.util import strtobool
from datetime import datetime
from aerpawlib.runner import BasicRunner, entrypoint, StateMachine, state, in_background, timed_state
from aerpawlib.util import VectorNED, Coordinate 
from aerpawlib.vehicle import Vehicle
from aerpawlib.vehicle import Drone

thisFileDir = os.path.realpath(os.path.dirname(__file__))
flypawRootDir = os.path.realpath(os.path.join(thisFileDir , '..', '..'))
flypawClassDir = os.path.realpath(os.path.join(flypawRootDir, 'basestation','basestationAgent'))
sys.path.append(flypawClassDir)
from flypawClasses import *
#import flypawClasses


class FlyPawPilot(StateMachine):
    def __init__(self):
        self.currentPosition = Position()
        self.currentBattery = Battery()
        self.currentHeading = None
        self.currentHome = None
        self.nextWaypoint = []
        self.previousSelfs = [] 
        self.missions = [] #This really needs to be an object!
        self.missionstate = None
        self.missionObjectives = []
        self.currentIperfObjArr = []
        self.communications = {}
        self.radio = {}
        self.resources = []
        self.currentWaypointIndex = 0 #deprecated!!!
        self.nextStates = []
        self.logfiles = {}
        self.videoLocation = "/root/video/video_diff_resolution/example1/video_1280_720.mpg"
        self.frameLocation = "/root/video/video_diff_resolution/example_frames"
        self.basestationIP = "172.16.0.1" #other side of the radio link
        self.videoURL = "udp://" + self.basestationIP + ":23000"
        self.prometheusQueryURL = "http://" + self.basestationIP + ":9090/api/v1/query?query=" 
        #frame can be used for sendVideo or sendFrame depending on mission type
        self.frame = 1

        self.taskQ = TaskQueue()
        self.TaskIDGen = TaskIDGenerator() 
        self.CurrentTask =  Task(0,0,0,0,self.TaskIDGen.Get())
        self.PreviousTask = None
        self.ActionStatus = ""
        self.Drone = None
        self.RADIO_RADIUS_SIM = 270 # meters
        self.WaypointHistory = WaypointHistory()
        self.CriticalTaskTimers = list()
        self.WatchDog =WatchDog()
        self.SpeculationList = list()
        self.Hold = TaskHold() #Task Hold !duh!

        



        #eNB location
        self.radio['lat'] = 35.72744
        self.radio['lon'] = -78.69607
        self.RadioPosition = Position()
        self.RadioPosition.InitParams(self.radio['lon'], self.radio['lat'],0,0,0,0)
        self.radioMap = RadioMap(self.RadioPosition)
        
        now = datetime.now()
        current_timestring = now.strftime("%Y%m%d-%H%M%S")
        #output_directory = args.output_directory
        output_directory = "/root/Results/"

        #states
        state_file_name = output_directory + "flypawState_%s.json" % (current_timestring)
        self.logfiles['state'] = state_file_name

        #telemetry
        telemetry_file_name = output_directory + "telemetry_%s.json" % (current_timestring)
        self.logfiles['telemetry'] = telemetry_file_name
        
        #iperf
        iperf_file_name = output_directory + "iperf3_%s.json" % (current_timestring)
        self.logfiles['iperf'] = iperf_file_name

        #errors
        error_file_name = output_directory + "error_%s.txt" % (current_timestring)
        self.logfiles['error'] = error_file_name
                
    #@entrypoint
    @state(name="preflight", first=True)
    async def preflight(self, drone=Drone):
        """
        preflight mission assignment and various status and safety checks and registrations
        """

        print(f"gps: {drone.gps} \t fix type: {drone.gps.fix_type}")
        print(f"gps: {drone._vehicle.gps_0}")
        logState(self.logfiles['state'], "preflight")
        
        #certain failures cause preflight to restart so let's sleep for seconds upon entry
        #time.sleep(1)
        
        self.missionstate = "preflight"
        self.Drone = drone

        ####Firstly some mission neutral hardware checks
        """
        Position Check
        """
        self.currentPosition = getCurrentPosition(drone)
        if not checkPosition(self.currentPosition):
            print("Position reporting not available.  Please resolve.")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("Position reporting not available.  Please resolve.")
                ofile.close()
            return "preflight"
    
        """
        Battery Check
        """
        self.currentBattery = getCurrentBattery(drone)
        if not checkBattery(self.currentBattery, None, None, None):
            print("Battery needs charging or reporting incorrectly.  Please resolve.")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("Battery needs charging or reporting incorrectly.  Please resolve.")
                ofile.close()
            return "preflight"

        """
        Heading Check
        TBD--> Make sure it makes sense and is a number I suppose
        """
        self.currentHeading = drone.heading


        """ 
        Network Check
        TBD--> Placeholder for now... Maybe check your throughput from that pad, or make it a networking system test (UE) rather than iperf
        """
        self.currentIperfObj = None



        """
        Mission Check
        TBD--> develop high level mission overview checks
        """
        print("Checking position")
        checkPosition(self.currentPosition)
        self.missions = getMissions(self.currentPosition,self.basestationIP) #should probably include the position and battery and home info when asking for missions... may preclude some missions   
        #print("missionObjective Transfer Check: "+ str(self.missions.missionObjectives))  
        if len(self.missions)<1:
            print("No assignment... will check again in 2 seconds")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("No assignment... will check again in 1 second")
                ofile.close()
            #time.sleep(2)
            return "preflight"
        else:
            print("number of missions: " + str(len(self.missions)))
            self.processMissions()
            #self.WatchDog.Normal = TaskPenaltyNormalizer(self.taskQ)
            self.WatchDog.StartingPosition = getCurrentPosition(drone)
            self.taskQ.PrintQ()
            

                    
        """
        Airspace Check
        TBD--> A placeholder for future important concepts like weather checks and UVRs.  Traffic also checked with DCB later
        For now just use the first mission
        """
        if not checkAirspace(0):#just a filler arg
            print("Airspace not fit for flying, check back later")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("Airspace not fit for flying, check back later")
                ofile.close()
            return "preflight"

        """
        Equipment Check
        TBD--> Mission specific gear check.  Eg. Video mission should check camera status
        """
        if not checkEquipment(self.missions[0]):
            print("Equipment not reporting correctly.  Please check")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("Equipment not reporting correctly.  Please check")
                ofile.close()
            return "preflight"
        
        ####Could check for availability of resources before accepting mission, but may make more sense to rely on basestation for this...
        """
        Cloud Resources Check
        TBD--> Mission specific cloud resources are queried for availability... not yet reserved
        
        if not checkCloudResources(self.missions[0]):
            print("Required cloud resources do not appear to be available")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("Required cloud resources do not appear to be available")
                ofile.close()
            return "preflight"
        """
        """
        Edge Resources Check
        TBD--> Mission specific edge resources are queried for availability... not yet reserved
        
        if not checkEdgeResources(self.missions[0]):
            print("Required edge resources do not appear to be available")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("Required edge resources do not appear to be available")
                ofile.close()
            return "preflight"
        """
        
        #likely a lot more to check... 

        #ok, try to accept mission
        print("accepting mission")
        missionAccepted = acceptMission(self.currentPosition,self.basestationIP, self.missions[0])

        self.InitWatchDog()
        self.ActivateWatchDog()

        if missionAccepted:
            print ("Here it is"+  str(self.missions[0].Type) + " mission accepted")
            
            #check start time of mission
            #check current time
            #sleep diff

            #get your initial waypoint in the default waypoints before we take off
            #initial_waypoint_location = dronekit.LocationGlobalRelative(self.missions[0]['default_waypoints'][0][1], self.missions[0]['default_waypoints'][0][0], self.missions[0]['default_waypoints'][0][2])
        
        else:
            print("Mission canceled")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("Mission canceled")
                ofile.close()
            return "preflight"

        #get resource info
        """
        Cloud Resource Info
        """
        print ("check resources")
        self.resources = getResourceInfo(self.currentPosition,self.basestationIP)
        for resource in self.resources:
            externalIP = None
            for address in resource.resourceAddresses:
                print("address type: " + address[0])
                if (address[0] == "external"):
                    externalIP = address[1]
            if externalIP is not None:
                print("external IP: " + str(externalIP))
            else:
                print("no external IP address found for node: " + resource.name)

                        
        """
        keep track of previous states, starting now
        """
        self.previousSelfs = []
        self.previousSelfs.append(self)
        #we can only keep track for so long else risk filling up memory... unclear how long this array can be
        if len(self.previousSelfs) > 10000:
            self.previousSelfs.pop(0)

        
        #check start time of mission, check current time, sleep diff
        #something here is not behaving as expected
        if not drone.armed:
            print("drone not armed. Arming")
            #time.sleep(5)
            await drone.set_armed(True)
            print("arming complete")
        else:
            print("drone is already armed")
        """
        Home Check
        """
        #seems like home is not set until after arming so check here
        #self.currentHome = drone.home_coords()
        self.currentHome = drone.position
        if self.currentHome is None:
            print("Please ensure home position is set properly")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("Please ensure home position is set properly")
                ofile.close()
            drone.set_armed(False)
            return "preflight"

        #ok... let's go!
        return "takeoff"

    @state(name="takeoff")
    async def takeoff(self, drone: Drone):
        print("takeoff")
        
        #takeoff to height of the first waypoint or 25 meters, whichever is higher, this will not work as missions become more complex and may not have an asscociated height--takeoff needs a new standard...                                                                                          
        if len(self.missions) > 1:
            target_alt = self.missions[0].Waypoint.alt
        else:
            print("recheck your mission")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("recheck your mission")
                ofile.close()
            return "preflight"

        if target_alt < 30:
            target_alt = 30

        print("takeoff to " + str(target_alt) + "m")
        #await drone.takeoff(target_alt)
        try:
            await asyncio.wait_for(drone.takeoff(target_alt), timeout=20.0) 
        except asyncio.TimeoutError as ex:
            print(ex)
        print("reached " + str(target_alt) + "m")
        self.WaypointHistory.AddPoint(getCurrentPosition(drone),1)#pushes first point to WayPointHistory
        
        #you should be at default_waypoints[1] now
        #with [1] being directly above [0], which is the home position on the ground                                                                                              
        self.currentWaypointIndex = 0
        return "waypoint_entry"










    @state(name="waypoint_entry")
    async def waypoint_entry(self, drone: Drone):
        """
        waypoint_entry
        update position, battery, heading, attitude, etc 
        identify and execute any mission related functions to be performed upon arrival at waypoint
        """
        logState(self.logfiles['state'], "waypoint_entry")
        #update position and battery and gps and heading
        statusAttempts = 5
        statusAttempt = 0
        while True: # Verifies gps is operating 
            #print("Get position.  Attempt: " + str(statusAttempt))
            #print("Verify GPS...")
            self.currentPosition = getCurrentPosition(drone)
            if not checkPosition(self.currentPosition):#need to understand what this function does
                if statusAttempt > statusAttempts:
                    #GPS does not seem to be working... try to go home
                    print("Can't query position.  Abort")
                    with open(self.logfiles['error'], "a") as ofile:
                        ofile.write("Can't query position.  Abort")
                        ofile.close()
                    return "abortMission"
                else:
                    statusAttempt = statusAttempt + 1
                    time.sleep(1)
            else:
                #position seems fine
                print("...GPS Verified")
                statusAttempt = 0
                break
               
        while True: # Attempts to assess the battery
            #print("Check battery.  Attempt: " + str(statusAttempt))
            #print("Check battery...")
            self.currentBattery = getCurrentBattery(drone)
            if self.currentBattery is None:
                if statusAttempt > statusAttempts:
                    #Battery check does not seem to be working... try to go home  
                    print("Can't query battery.  Abort")
                    with open(self.logfiles['error'], "a") as ofile:
                        ofile.write("Can't query battery.  Abort")
                        ofile.close()
                    return "abortMission"
                else:
                    statusAttempt = statusAttempt + 1
                    time.sleep(1)
            else:
                #battery seems fine
                print("...Battery is communicating")
                statusAttempt = 0
                break

        print ("Reporting telemetry and battery status...")
        recv = await self.reportPositionUDP()
        if (recv):
            print("...Report position to basestation confirmed")
            self.communications['reportPositionUDP'] = 1
        else:
            self.communications['reportPositionUDP'] = 0
            print("no reply from server while transmitting position")
        
        #self.currentAttitude = getCurrentAttitude(drone)
        self.currentHeading = drone.heading

        #self.RadioEval()
        self.PreviousTask = self.CurrentTask
        JSON_DUMP_TASK = jsonpickle.encode(self.WaypointHistory)
        with open('json_dump_t.txt','w') as f:
            f.write(JSON_DUMP_TASK)
        JSON_DUMP_ID_GEN = jsonpickle.encode(self.TaskIDGen)
        with open('json_dump_id.txt','w') as f:
            f.write(JSON_DUMP_ID_GEN)
        JSON_DUMP_WD = jsonpickle.encode(self.WatchDog)
        with open('dump_watchdog.json','w') as f:
            f.write(JSON_DUMP_WD)



        self.EvaluateTaskQ()

        #abort mission if Q is empty
        #print("TaskQ Size: " + str(self.taskQ.Count))
        if self.taskQ.Empty():
            print("No more tasks...Returning Home")  
            return "abortMission"

        
        self.CurrentTask = self.taskQ.PopTask()
        #print("Task: " + str(self.CurrentTask.task))
       
        if self.CurrentTask.task == "ABORT":
            return "abortMission"
        return "action"

    @state(name="action") #This really seems like a stub...probably could move it 
    async def action(self, _ ):
        logState(self.logfiles['state'], "action")
        state = self.ActionStateMap(self.CurrentTask.task)
        return state


        






    
    @state(name="flight")
    async def flight(self, drone: Drone):
        logState(self.logfiles['state'], "flight")



        defaultNextCoord = Coordinate(self.CurrentTask.position.lat,self.CurrentTask.position.lon,self.CurrentTask.position.alt)


        ##set heading... unnecessary unless we want to have a heading other than the direction of motion 
        #drone.set_heading(bearing_from_here)
        print("Trying to fly...")
        await drone.goto_coordinates(defaultNextCoord)
        print("Ya...")
        self.WatchDog.ActionComplete(self.CurrentTask)
        return "waypoint_entry" 

    @timed_state(name="instructionRequest", duration=1)
    async def instructionRequest(self):
        logState(self.logfiles['state'], "instructionRequest")
        #defaultSequence = "flight"
        #nextSequence = defaultSequence
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "instructionRequest"
        msg['CUR_POS'] = self.currentPosition
        serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
                if 'requests' in serverReply:
                    theseRequests = serverReply['requests']
                    print(theseRequests)
                    #just handle the first request for now
                    if serverReply['requests'] is not None:
                        return theseRequests
                        #thisPrimaryRequest = theseRequests[0]
                        #if 'command' in thisPrimaryRequest:
                        #    requestIsValid = validateRequest(thisPrimaryRequest['command'])
                        #    if requestIsValid:
                        #        print("performing request: " + thisPrimaryRequest['command'])
                        #        nextSequence = thisPrimaryRequest['command']
                        #    else:
                        #        print("request not valid.  Going to default action: " + nextSequence)

                        #else:
                        #    print("command not present in this request.  Going to default action: " + nextSequence)
                    else:
                        print("no requests at the moment. Drone to decide")
                else:
                    print("requests not present in server reply. Drone to decide")
            else:
                print ("uuid mismatched.  Drone to decide")
        else:
            print("No reply from server.  Drone to decide")
            
        return None
    """
     @timed_state(name="iperf_old",duration = 20)
    async def iperf_old(self, drone: Drone):
        print("starting iperf state")
        logState(self.logfiles['state'], "iperf")
        iperfObjArr = []
        for resource in self.resources:
            externalIP = None
            for address in resource.resourceAddresses:
                print("address type: " + address[0])
                if (address[0] == "external"):
                    externalIP = address[1]
            if externalIP is not None:
                iperfResult = await self.runIperf(externalIP, drone)
                iperfObjArr.append(iperfResult['iperfResults'])
        
        #run it once in your current orientation
        print("Iperfcall--started")
        iperfResult = await self.runIperf(self.basestationIP, drone)
        print("Iperfcall--finished")
        print(iperfResult['iperfResults'])
        iperfObjArr.append(iperfResult['iperfResults'])

        #now yaw toward the radio and do it again
        geodesic_azi = Geodesic.WGS84.Inverse(self.currentPosition.lat, self.currentPosition.lon, self.radio['lat'], self.radio['lon'], 512)
        bearing_to_radio = geodesic_azi.get('azi1')
        #print("set bearing to " + str(bearing_to_radio))
        #await drone.set_heading(bearing_to_radio)
        #print("bearing set, now run iperf again")
        #now toward the radio                                                                                                                
        #iperfResult = await self.runIperf(self.basestationIP, drone)
        #print("second iperf result finished")
        #print(iperfResult['iperfResults'])
        iperfObjArr.append(iperfResult['iperfResults'])
        #drone.radioMap['dataRate'] = iperfResult['iperfResults']['mbps']
        currentPosition = getCurrentPosition(drone)
        self.radioMap.add(currentPosition.lat, currentPosition.lon,self.currentHeading,iperfResult['iperfResults']['mbps'])
        #drone.radioMap.lats = currentPosition['lat']
        print("RadioMapLength:")
        print(self.radioMap.length)
        
        #at the end append all the individual iperf results to the self array
        self.currentIperfObjArr.append(iperfObjArr)
        self.ActionStatus = "SUCCESS"
        return "waypoint_entry"


    """            
   

    #IPERF CAN BE THIS QUICK, takes less than 3.5 sec
    @timed_state(name="iperf",duration = 4)
    async def iperf(self, drone: Drone):
        print("starting iperf state")
        logState(self.logfiles['state'], "iperf")
        iperfObjArr = []

        
        #run it once in your current orientation
        print("Iperfcall--started")
        iperfResult = await self.runIperf(self.basestationIP, drone)
        print("Iperfcall--finished")
        print(iperfResult['iperfResults'])
        #drone.radioMap['dataRate'] = iperfResult['iperfResults']['mbps']
        currentPosition = getCurrentPosition(drone)
        #self.radioMap.Add(currentPosition.lat, currentPosition.lon,self.currentHeading,iperfResult['iperfResults']['mbps'])
        #drone.radioMap.lats = currentPosition['lat']

        
        #at the end append all the individual iperf results to the self array
        self.currentIperfObjArr.append(iperfObjArr)
        self.ActionStatus = "SUCCESS"
        print("Returning to Dispatcher")
        return "waypoint_entry"



    #This is where we will actuate Frame Capture, but for now it is a stub
    @state(name="captureFrame_Single")
    async def captureFrame_Single(self, _ ):
        logState(self.logfiles['state'], "collectVideo")
        x=0
        time.sleep(4)
        self.WatchDog.ActionComplete(self.CurrentTask)
        return "waypoint_entry"

        
    #This is a placeholder for the SEND_DATA function-------------------
    @state(name="sendFrame")
    async def sendFrame(self, _ ):

        logState(self.logfiles['state'], "sendFrame")
        time.sleep(2.5)
        if (self.frame > 1401): #only because the test data has like 1450 frames
            self.frame = 1
        framestr = str(self.frame).zfill(7) + ".jpg"
        framefn = self.frameLocation + "/" + framestr
        
        #figure out where to send
        #i) check prometheus
        up_array = []
        load_array = []
        for resource in self.resources:
            externalIP = None
            for address in resource.resourceAddresses:
                print("address type: " + address[0])
                if (address[0] == "external"):
                    externalIP = address[1]
                    statusQueryURL = self.prometheusQueryURL + 'up{instance="' + externalIP + ':8095"}'
                    print("status query: " + statusQueryURL)
                    nodeOnline = prometheusStatusQuery(statusQueryURL)
                    nodeOnlineObj = {}
                    nodeOnlineObj['externalIP'] = externalIP
                    nodeOnlineObj['online'] = nodeOnline
                    if nodeOnlineObj not in up_array:
                        up_array.append(nodeOnlineObj)
                    if nodeOnline:
                        loadQueryURL = self.prometheusQueryURL + 'node_load1{instance="' + externalIP + ':8095"}'
                        print("load query: " + loadQueryURL)
                        loadResult = prometheusLoadQuery(loadQueryURL)
                        loadObj = {}
                        if loadResult is not None:
                            loadObj['externalIP'] = externalIP
                            loadObj['load'] = loadResult
                            load_array.append(loadObj)

        minload = 100.1
        bestnode = None
        for onlineNode in load_array:
            load = float(onlineNode['load'])
            print("node: " + onlineNode['externalIP'])
            print("load: " + str(load))
            if load < minload:
                bestnode = onlineNode['externalIP']
                minload = load
        if bestnode is not None:
            print("send to: " + bestnode)
                    
            fileSendFail = udpFileSend(framefn, bestnode, 8096, 1024) #try 1024 for buffer size for now
            if fileSendFail:
                print("couldn't send video")
            else:
                self.frame = self.frame + 50
            
            x = uuid.uuid4()
            msg = {}
            msg['uuid'] = str(x)
            msg['type'] = "sendFrame"
            msg['sendFrame'] = {}
            msg['CUR_POS'] = self.currentPosition
            serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
            if serverReply is not None:
                print(serverReply['uuid_received'])
                if serverReply['uuid_received'] == str(x):
                    print(serverReply['type_received'] + " receipt confirmed by UUID")

        self.WatchDog.ActionComplete(self.CurrentTask)
        return "waypoint_entry"
    
    @state(name="sendVideo")
    async def sendVideo(self, _ ):
        print("sendVideo")
        logState(self.logfiles['state'], "sendVideo")
        stream = ffmpeg.input(self.videoLocation)
        endframe = self.frame + 100
        if endframe > 1400:
            self.frame = 0
            endframe = 100
        ffmpeg_out = (
            ffmpeg
            .concat(stream.trim(start_frame=self.frame, end_frame=endframe))
            .output(self.videoURL, vcodec='mpeg4', f='mpegts')
            .global_args('-report')
            .run_async(pipe_stdout=True)
        )
        ffmpeg_out.wait()
        self.frame = endframe
        
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "sendVideo"
        msg['sendVideo'] = {}
        msg['CUR_POS'] = self.currentPosition
        serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
        return "nextAction"

        
    @state(name="collectVideo")
    async def collectVideo(self, _ ):
        logState(self.logfiles['state'], "collectVideo")
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "collectVideo"
        msg['collectVideo'] = {}
        msg['CUR_POS'] = self.currentPosition
        serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
        return "nextAction"

    @state(name="abortMission")
    async def abortMission(self, drone: Drone):
        logState(self.logfiles['state'], "abortMission")
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "abortMission"
        msg['CUR_POS'] = self.currentPosition
        serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
        #consider checking rally points 
        
        #problem with below is that it does not descend vertically.
        #if self.currentHome is not None:
        #    await drone.goto_coordinates(self.currentHome)

        #another option... go to waypoint 1 for now which should be over the home position
        #overHomePositionCoord = Coordinate(self.missions[0].default_waypoints[1][1], self.missions[0].default_waypoints[1][0], self.missions[0].default_waypoints[1][2])
        overHomePositionCoord = Coordinate(self.currentHome.lat, self.currentHome.lon, 30)
        #drone.set_heading(bearing_from_here)
        await drone.goto_coordinates(overHomePositionCoord)
        
        print("land")
        await drone.land()
        print("flight complete")
        return "completed"
    
    @state(name="completed")
    async def completed(self, _ ):
        """
        post flight cleanup
        """
        self.WaypointHistory.PrintWorkingHistory()
        JSON_DUMP_WD = jsonpickle.encode(self.WatchDog)
        self.WatchDog.Print()
        with open('dump_watchdog.json','w') as f:
            f.write(JSON_DUMP_WD)
        self.WatchDog.DumpReport()
        experiment = ExperimentResults()
        print("SpeculativeProduct List Length: " + str(self.SpeculationList.__len__()))
        experiment.SpeculativeSolutionSets = self.SpeculationList
        executionRecord = self.WatchDog.GetActionList()
        experiment.ExecutionRecord = executionRecord
        print("EXECUTE List Length: " + str(executionRecord.__len__()))
        JSON_DUMP_EEE = jsonpickle.encode(experiment,unpicklable=False,indent=True)
        with open('EXPERIMENT_DUMP.json','w') as f:
            f.write(JSON_DUMP_EEE)

        print("cleaning up")
        logState(self.logfiles['state'], "completed")
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "completed"
        msg['CUR_POS'] = self.currentPosition
        serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
        print("exiting")
        sys.exit()
        

    def RadioEval_SIM (self):
        x=0
        self.currentPosition =  getCurrentPosition(self.Drone)
        geo = Geodesic.WGS84.Inverse(self.currentPosition.lat, self.currentPosition.lon, self.radio['lat'], self.radio['lon'])
        distance_to_radio = geo.get('s12')
        print("The distance to radio is {:.3f} m.".format(geo['s12']))
        if distance_to_radio <1000:
            iperfResult = self.runIperfSync(self.basestationIP, self.Drone)
            self.radioMap.Add(self.currentPosition.lat, self.currentPosition.lon,self.currentHeading,iperfResult['iperfResults']['mbps'],self.currentPosition.alt)
            self.communications['iperf'] = 1 #I thought this would happen in iperf call....but it doesn't...
            print("RadioMapLength:"+ str(self.radioMap.length))
            print("CONNECTION-GOOD!")
        else:
            self.radioMap.Add(self.currentPosition.lat, self.currentPosition.lon,self.currentHeading,0,self.currentPosition.alt)
            self.communications['iperf'] = 0
            print("CONNECTION-BAD!")
            #BENCHMARK

    def RadioEval (self):
        self.currentPosition =  getCurrentPosition(self.Drone) #Sometimes this returns none...needs to be addressed...broke the program
        geo = Geodesic.WGS84.Inverse(self.currentPosition.lat, self.currentPosition.lon, self.radio['lat'], self.radio['lon'])
        distance_to_radio = geo.get('s12')
        print("The distance to radio is {:.3f} m.".format(geo['s12']))
        iperfResult = self.runIperfSync(self.basestationIP, self.Drone)
        if self.communications['iperf'] == 1:

            self.radioMap.Add(self.currentPosition.lat, self.currentPosition.lon,self.currentHeading,100.0,self.currentPosition.alt)
            self.communications['iperf'] = 1 #I thought this would happen in iperf call....but it doesn't...
            print("RadioMapLength:"+ str(self.radioMap.length))
            print("CONNECTION-GOOD!")
        else:
            self.radioMap.Add(self.currentPosition.lat, self.currentPosition.lon,self.currentHeading,0,self.currentPosition.alt)
            self.communications['iperf'] = 0
            print("CONNECTION-BAD!")
            #BENCHMARK
        
    def InitWatchDog(self):

        critTasks = self.taskQ.GetCriticalTasks()
        self.WatchDog.InitStopwatches(critTasks)


    def ActivateWatchDog(self):

        self.WatchDog.StartStopwatches()



    def _RadioBreakSim(self):
        x = 0


    def runIperfSync(self, ipaddr, drone: Drone):
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "iperfResults"
        msg['iperfResults'] = {}
        client = iperf3.Client()

        client.server_hostname = ipaddr
        client.port = 5201
        client.duration = 3
        client.json_output = True
        result = client.run()
        err = result.error
        iperfPosition = getCurrentPosition(drone)

        msg['iperfResults']['ipaddr'] = client.server_hostname
        msg['iperfResults']['port'] = client.port
        msg['iperfResults']['protocol'] = "tcp"
        msg['iperfResults']['location4d'] = [ iperfPosition.lat, iperfPosition.lon, iperfPosition.alt, iperfPosition.time ]
        msg['iperfResults']['heading'] = [ self.currentHeading ]
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
            
        result_str = json.dumps(msg)
        with open(self.logfiles['iperf'], "a") as ofile:
            ofile.write(result_str + "\n")
            ofile.close()
            msg['CUR_POS'] = self.currentPosition
            serverReply = udpClientMsg(msg, self.basestationIP, 20001, 2)
            if serverReply is not None:
                print(serverReply['uuid_received'])
                if serverReply['uuid_received'] == str(x):
                    print(serverReply['type_received'] + " receipt confirmed by UUID")
                    self.communications['iperf'] = 1
                else:
                    print(serverReply['type_received'] + " does not match our message UUID")
                    self.communications['iperf'] = 0
            else:
                print("no reply from server while transmitting iperfResults")
                self.communications['iperf'] = 0
        #delete the iperf3 client to avoid errors
        print("IPERF_CALL_RESULTS:")
        print("MBPS: "+ str(msg['iperfResults']['mbps']))
        print("CONNECTION: "+ str(msg['iperfResults']['connection']))
        print("---------------")
        
        del client
        return msg

        
    
    async def runIperf(self, ipaddr, drone: Drone):
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "iperfResults"
        msg['iperfResults'] = {}
        client = iperf3.Client()

        client.server_hostname = ipaddr
        client.port = 5201
        client.duration = 3
        client.json_output = True
        result = client.run()
        err = result.error
        iperfPosition = getCurrentPosition(self.drone)

        msg['iperfResults']['ipaddr'] = client.server_hostname
        msg['iperfResults']['port'] = client.port
        msg['iperfResults']['protocol'] = "tcp"
        msg['iperfResults']['location4d'] = [ iperfPosition.lat, iperfPosition.lon, iperfPosition.alt, iperfPosition.time ]
        msg['iperfResults']['heading'] = [ self.currentHeading ]
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
            
        result_str = json.dumps(msg)
        with open(self.logfiles['iperf'], "a") as ofile:
            ofile.write(result_str + "\n")
            ofile.close()
            msg['CUR_POS'] = self.currentPosition
            serverReply = udpClientMsg(msg, self.basestationIP, 20001, 2)
            if serverReply is not None:
                print(serverReply['uuid_received'])
                if serverReply['uuid_received'] == str(x):
                    print(serverReply['type_received'] + " receipt confirmed by UUID")
                    self.communications['iperf'] = 1
                else:
                    print(serverReply['type_received'] + " does not match our message UUID")
                    self.communications['iperf'] = 0
            else:
                print("no reply from server while transmitting iperfResults")
                self.communications['iperf'] = 0
        #delete the iperf3 client to avoid errors
        del client
        return msg






    #I shouldn't be getting empty missions form the BaseStation
    def processMissionsOLD(self):
        if self.missions :
            x = 0
            for mission in self.missions:
                    for waypoint in mission.default_waypoints:
                        position = Position()
                        position.InitParams(waypoint[0],waypoint[1],waypoint[2],0,0,0)
                        t = Task(position,"FLIGHT",0,0,self.TaskIDGen.Get())
                        self.taskQ.PushTask(t)
            return 1
        else:
            return 0

    def processMissions(self):
        if self.missions :
            x = 0
            for missionObj in self.missions:
                    
                    taskList = self.InterpretObjective(missionObj)
                    for task in taskList:
                        self.taskQ.PushTask(task)
                    

            return 1
        else:
            return 0

    #This function interprets mission objectives converting them into tasks. This should eveentually be called by EvaluateTaskQ as well.
    def InterpretObjective(self, objective:MissionObjective):
        x=0
        taskList = []
        objectiveType = objective.Type
        if objectiveType == "FLIGHT":
            tasktemp = Task(objective.Waypoint,"FLIGHT",0,0,self.TaskIDGen.Get())
            taskList.append(tasktemp)
        if objectiveType == "IPERF":
            taskList.append(Task(objective.Waypoint,"FLIGHT",0,0,self.TaskIDGen.Get()))
            #taskList.append(Task(objective.Waypoint,"IPERF",0,0,self.TaskIDGen.Get()))
        if objectiveType == "IMAGE_LOCATION_QUICK":
            taskList.append(Task(objective.Waypoint,"FLIGHT",0,0,self.TaskIDGen.Get()))
            taskList.append(Task(objective.Waypoint,"IMAGE_SINGLE",0,0,self.TaskIDGen.Get()))
            t = Task(objective.Waypoint,"SEND_DATA",0,0,self.TaskIDGen.Get())
            t.comms_required = True
            taskList.append(t)

        return taskList

            


    #This is a stub. It should be used to evaulate the taskQ. 
    #Evaluate should look at the task view, and analyze taskQ for efficiency and practicality
    # Should takes current drone status into account and rearrange/add tasks if needed.
    #plans aborts
    # Evaluates Failed Tasks/ Incomplete tasks as well.
    #In future we will decide here which tasks can be run asynchronously
    def EvaluateTaskQ(self):

        #Check if connection is needed
        RadioConnectionWayPoint = Position()
        nextTask = self.taskQ.NextTask()
        print(str(nextTask))
        self.taskQ.PrintQ() 
        self.RadioEval()
        if(self.CurrentTask.task=="FLIGHT"):
            self.WaypointHistory.AddPoint(self.currentPosition,self.communications['iperf'])


        #this may need a state of its own... reestablish connection
        if(self.communications['iperf']==0 and nextTask.comms_required):

            JSON_DUMP = jsonpickle.encode(self.taskQ)
            JSON_DUMP_WPH = jsonpickle.encode(self.WaypointHistory)
            emptyList = list()
            t = self.taskQ.NextTask()

            with open('json_dump_q.txt','w') as f:
                f.write(JSON_DUMP)
            with open('json_dump_wph.txt','w') as f:
                f.write(JSON_DUMP_WPH)
            
            speculation =  SpeculativeProduct()
            pt = TaskPenaltyTracker(self.taskQ,self.WatchDog,self.WaypointHistory)
            root:Node =  Node(0,self.taskQ,t,0,0,self.WaypointHistory,self.TaskIDGen,emptyList,pt,1.0,"ROOT")
            tree:PredictiveTree = PredictiveTree(root)
            tree.HaltPoint(False)
            #tree.PrintNodes()
            tree.CurrentWatchdog = self.WatchDog
            currentSpecSolution = tree.BuildSolutionObject()
            JSON_DUMP_SPEC = jsonpickle.encode(currentSpecSolution)
            with open('json_dump_spec.txt','w') as f:
                f.write(JSON_DUMP_SPEC)
            self.SpeculationList.append(currentSpecSolution) 
            
            

            




            recommendedSolution:Solution = currentSpecSolution.GetRecommendation()
            rec = recommendedSolution.DecisionStack[0]## Should this be 0?
            print("Recommended Solution: " + rec)

            if(rec == "LOF"):
                rec = "BACKSTEP"
            elif(rec =="BLOCK"):
                rec = "BACKSTEP"
            elif(rec =="HOLD"):
                rec = "HOLD"

            print("Defaulting to BACKSTEP")

            if(rec=="BACKSTEP"):
                x=0
                BackPath = self.BackStepPath()
                self.taskQ.PopTask()#This is probably ineffective now i.e. it only makes sense when we backstep
                self.taskQ.AppendTasks(BackPath)
                #do back step
            elif(rec=="HOLD"):
                x=0
                self.taskQ.HoldTopTask()##this will lock away the top task until it is appropriate to release
                #do hold
            else:
                x=0
                #error
            
            



            # self.taskQ.PopTask()#This is probably ineffective now i.e. it only makes sense when we backstep
            # self.taskQ.AppendTasks(ReccomendedConnectionPath)

            self.taskQ.PrintQ()
            #time.sleep(10)
        else:
            print("TaskHold Empty:"+ str(self.taskQ.CaptivesHeld()))
            print("Captives:"+ str(self.taskQ.TaskLock.Captives.__len__()))
            while(self.taskQ.CaptivesHeld()):
                self.taskQ.Release()
                print("Task Released!!!------------------------------------")
                print("Q Updated")
                self.taskQ.PrintQ()        
        






    #Should Validate the Task type exists
    def ValidateTask(self,task:Task): 
        x= 0
        if task.task == "FLIGHT" : 
            return True
        return False

    #We should build an action map that is imported--i.e. make it an external file of registered actions. The returned value should lead to the correct state.
    def ActionStateMap(self,action):
        if action == "FLIGHT":
            return "flight"
        elif(action == "IPERF"):
            return "iperf"
        elif(action == "IMAGE_SINGLE"):
            return "captureFrame_Single"
        elif(action == "SEND_DATA"):
            return "sendFrame"
        else:
            return "ERROR"

    #STUB----This function will provide mutiple taskLists to be evaluated, but right now, will just include one
    def GetPathToConnection(self):
        #RadioConnectionWayPoint = self.radioMap.FindClosestPointWithConnection(None,self.currentPosition,self.RadioPosition)



        #BackStep Path! always a pretty safe option
        backSteps = self.WaypointHistory.BackTrackPathForConnectivity()
        print("BackSteps: ")
        self.WaypointHistory.PrintListOfStepsGeneric(backSteps)
        taskConversion = []
        nextTask = self.taskQ.NextTask()
        backSteps.reverse()
        insertPostion = 0
        for idx, waypoint in enumerate(backSteps):
 
            if(waypoint[1]):
                print("Appending Next Task!")
                taskConversion.append(nextTask)
            t = Task(waypoint[0],"FLIGHT",0,0,self.TaskIDGen.Get())
            t.dynamicTask = True
            print("TASK ID: "+str(waypoint[2])) 
            taskConversion.append(t)
        

        BackTrackTaskList = taskConversion
        ForwardSteps = self.FindFowardConnection()
        taskConversion = []
        #for now, lets just return a list of two tasks sets, but this should be an object in the future
        taskConversion.append(BackTrackTaskList)
        if(len(ForwardSteps)):
            taskConversion.append(ForwardSteps)

        

        return taskConversion



    def BackStepPath(self):
        #RadioConnectionWayPoint = self.radioMap.FindClosestPointWithConnection(None,self.currentPosition,self.RadioPosition)



        #BackStep Path! always a pretty safe option
        backSteps = self.WaypointHistory.BackTrackPathForConnectivity()
        print("BackSteps: ")
        self.WaypointHistory.PrintListOfStepsGeneric(backSteps)
        taskConversion = []
        nextTask = self.taskQ.NextTask()
        backSteps.reverse()
        insertPostion = 0
        for idx, waypoint in enumerate(backSteps):
 
            if(waypoint[1]):
                print("Appending Next Task!")
                taskConversion.append(nextTask)
            t = Task(waypoint[0],"FLIGHT",0,0,self.TaskIDGen.Get())
            t.dynamicTask = True
            print("TASK ID: "+str(waypoint[2])) 
            taskConversion.append(t)
        

        BackTrackTaskList = taskConversion
        taskConversion = []
        #for now, lets just return a list of two tasks sets, but this should be an object in the future
        taskConversion.append(BackTrackTaskList)


        

        return BackTrackTaskList
    #This should really be managed by a dictionary
    def TaskListTimeEstimate(self,taskList):

        timeEstimate = 0
        for task in taskList:
            if task.task == "FLIGHT" :
                timeEstimate = timeEstimate + 5
            elif(task.task == "IMAGE_SINGLE"):
                timeEstimate = timeEstimate + 1
            elif(task.task == "SEND_DATA"):
                timeEstimate = timeEstimate + 3
        return timeEstimate


    def DistanceBetweenTwoPostions(self,posA,posB):
        geo = Geodesic.WGS84.Inverse(posA.lat, posA.lon, posB.lat, posB.lon)
        distanceBetweenPoints = geo.get('s12')
        return distanceBetweenPoints


    #Returns the Chance of they're being a connection
    def ConnectionChance(self,posA):
        0
        distanceToBase = self.DistanceBetweenTwoPostions(self.RadioPosition,posA)
        print("Distance:"+str(distanceToBase))
        if(distanceToBase<150):
            print("GOODCHANCE!")
            return 0.95
        else:
            return 0.0
        
    #finds the closest connection forward, jets over, then continues with normal tasks
    def FindFowardConnection(self):
        0
        #shouldn't iterating taskq like this :(
        ForwardSteps = []
        TaskPath = []
        qCount = self.taskQ.Count
        endOfQ = (qCount-1)
        iterator = endOfQ
        ConnectionTask = Task(0,0,0,0,0)
        DataDependentTask = self.taskQ.queue[endOfQ]
        ReturnFinalTask = Task(DataDependentTask.position,"FLIGHT",0,0,self.TaskIDGen.Get())
        iterator = iterator - 1
        while iterator>0:
            nextTask = self.taskQ.queue[iterator]
            if(nextTask.task == "FLIGHT"):
                0
                print("Task:" + str(nextTask.uniqueID))
                chanceOfConnection = self.ConnectionChance(nextTask.position)
                if(chanceOfConnection>0.8):
                    print("ConnectionFound")
                    ConnectionTask = nextTask
                    break
                ForwardSteps.append(nextTask)

            iterator = iterator - 1
        

        if(iterator>0):#Path exists
            TaskPath.append(ReturnFinalTask)
            ForwardStepsReverse = ForwardSteps
            ForwardStepsReverse.reverse()
            TaskPath.extend(ForwardSteps)
            TaskPath.append(self.taskQ.NextTask())
            TaskPath.append(ConnectionTask)
            TaskPath.extend(ForwardStepsReverse)
            
        return TaskPath




    def PickPathToRestablish(self, taskLists):
        reccomendedPath = taskLists[0]
        lowestTimeEstimate = self.TaskListTimeEstimate(reccomendedPath)
        for path in taskLists:
            0
            timeEstimate = self.TaskListTimeEstimate(path)
            print("PathTime: "+ str(timeEstimate))
            self.PrintPath(path)
            if(lowestTimeEstimate>timeEstimate):
                0
                reccomendedPath = path
                lowestTimeEstimate = timeEstimate
        return reccomendedPath


    def PrintPath(self,path):
        0
        for task in path:
            0
            print("Task:"+str(task.uniqueID)+", "+task.task)

        
    async def reportPositionUDP(self):
        #print (str(self.currentPosition.lat) + " " + str(self.currentPosition.lon) + " " + str(self.currentPosition.alt) + " " + str(self.currentPosition.time))
    
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "telemetry"
        msg['telemetry'] = {}
        msg['telemetry']['position'] = self.currentPosition
        msg['telemetry']['battery'] = self.currentBattery
        #msg['telemetry']['attitude'] = {} 
        #msg['telemetry']['attitude']['pitch'] = self.currentAttitude['pitch']
        #msg['telemetry']['attitude']['yaw'] = self.currentAttitude['yaw']
        #msg['telemetry']['attitude']['roll'] = self.currentAttitude['roll']  
        msg['telemetry']['heading'] = self.currentHeading
        msg['telemetry']['home'] = []
        msg['telemetry']['home'].append(self.currentHome.lat)
        msg['telemetry']['home'].append(self.currentHome.lon)
        msg['telemetry']['home'].append(self.currentHome.alt)
        msg['telemetry']['nextWaypoint'] = self.nextWaypoint

        #log telemetry
        #print("logging telemetry")
        
        teleJson = {}
        teleJson['position'] = {}
        teleJson['position']['lat'] = self.currentPosition.lat
        teleJson['position']['lon'] = self.currentPosition.lon
        teleJson['position']['alt'] = self.currentPosition.alt
        teleJson['position']['time'] = self.currentPosition.time
        teleJson['position']['fix_type'] = self.currentPosition.fix_type
        teleJson['position']['satellites_visible'] = self.currentPosition.satellites_visible
        teleJson['battery'] = {}
        teleJson['battery']['voltage'] = self.currentBattery.voltage
        teleJson['battery']['current'] = self.currentBattery.current
        teleJson['battery']['level'] = self.currentBattery.level
        #teleJson['battery']['m_kg'] = self.currentBattery.m_kg
        teleJson['heading'] = self.currentHeading
        teleJson['home'] = []
        teleJson['home'].append(self.currentHome.lat)
        teleJson['home'].append(self.currentHome.lon)
        teleJson['home'].append(self.currentHome.alt)
        result_str = json.dumps(teleJson)
            
        with open(self.logfiles['telemetry'], "a") as ofile:
            ofile.write(result_str)
            ofile.close()
        
        #print("sending telemetry")
        msg['CUR_POS'] = self.currentPosition
        serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
        if serverReply is not None:
            #print(serverReply) 
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
                return 1
            else:
                print("we have a mismatch in uuids... investigate")
                return 0
        return 0

    


def getMissions(pos, basestationIP):
    x = uuid.uuid4()
    msg = {}
    msg['uuid'] = str(x)
    msg['type'] = "mission"
    msg['CUR_POS'] = pos
    serverReply = udpClientMsg(msg, basestationIP, 20001, 10)
    if serverReply is not None:
        print(serverReply['uuid_received'])
        if serverReply['uuid_received'] == str(x):
            print(serverReply['type_received'] + " receipt confirmed by UUID")
            if 'missions' in serverReply:
                missions = serverReply['missions']
                missionObjectives = missions[0].missionObjectives
                print("missionObjective Transfer Check: "+ str(missionObjectives))  
                
                return missionObjectives
    print("NOOONE!")
    return None

def getResourceInfo(pos,basestationIP):
    x = uuid.uuid4()
    msg = {}
    msg['uuid'] = str(x)
    msg['type'] = "resourceInfo"
    #wait up to a minute to get resource info
    msg['CUR_POS'] = pos
    serverReply = udpClientMsg(msg, basestationIP, 20001, 60)
    if serverReply is not None:
        print(serverReply['uuid_received'])
        if serverReply['uuid_received'] == str(x):
            print(serverReply['type_received'] + " receipt confirmed by UUID")
            if 'resources' in serverReply:
                resources = serverReply['resources']
                return resources
    return None

def configureResources(missionLibraries, resource):#FUNCTION NOT USED
    #install any libraries needed for mission
    x = uuid.uuid4()
    msg = {}
    msg['uuid'] = str(x)
    msg['type'] = "configureResources"
    msg['missionLibraries']= missionLibraries
    msg['resource'] = resource
    
    #wait up to 5 minutes to let resources configure
    serverReply = udpClientMsg(msg, basestationIP, 20001, 300)
    if serverReply is not None:
        print(serverReply['uuid_received'])
        if serverReply['uuid_received'] == str(x):
            if 'configured' in serverReply:
                if serverReply['configured'] == True:
                    return
                else:
                    with open(self.logfiles['error'], "a") as ofile:
                        ofile.write("Error configuring resources. Try again later.")
                        ofile.close()
                        deleteResources(resources)
                        return "preflight"
            else:
                with open(self.logfiles['error'], "a") as ofile:
                        ofile.write("Error configuring resources. Try again later.")
                        ofile.close()
                        deleteResources(resources)
                        return "preflight"                        
    else:
        with open(self.logfiles['error'], "a") as ofile:
            ofile.write("Error configuring resources. Try again later.")
            ofile.close()
            deleteResources(resources)
            return "preflight"
                    
def getCurrentPosition(drone: Drone):
    if drone.connected:
        pos = drone.position
        gps = drone.gps
        thisPosition = Position()
        thisPosition.lat = pos.lat
        thisPosition.lon = pos.lon
        thisPosition.alt = pos.alt
        thisPosition.time = datetime.now().astimezone().isoformat(timespec='seconds')
        thisPosition.fix_type = gps.fix_type
        thisPosition.satellites_visible = gps.satellites_visible
        return thisPosition
    else:
        return None

def getCurrentBattery(drone: Drone):
    if drone.connected:
        battery = drone.battery
        thisBattery = Battery()
        thisBattery.voltage = battery.voltage
        thisBattery.current = battery.current
        thisBattery.level = battery.level
        return thisBattery
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
    validReq.append("waypoint_entry")
    validReq.append("flight")
    validReq.append("sendFrame")
    validReq.append("sendVideo")
    validReq.append("collectVideo")
    validReq.append("instructionRequest")

    if request in validReq:
        return 1    
    else:
        return 0

def checkPosition(thisPosition):
    #print(thisPosition.lat)
    #print(thisPosition.lon)
    #sys.exit()
    if thisPosition is None:
        print("position not available")
        return 0
    #if 'lat' in thisPosition and 'lon' in thisPosition and 'alt' in thisPosition:
    if thisPosition.lat is None or thisPosition.lon is None or thisPosition.alt is None:
        print("Unable to query current latitude and/or longitude coordinates or altitude!")
        return 0
    #else:
    #    print("lat and/or lon and/or alt missing")
    #    return 0
    #if "satellites_visible" in thisPosition:
    if thisPosition.satellites_visible is None:
        print("Unable to query for gps satellites")
        return 0
    elif thisPosition.satellites_visible == 0:
        print("no gps satellites visible")
        return 0
    #else:
    #    print("satellites visible missing")
    #    return 0
    
    #if "fix_type" in thisPosition:
    if thisPosition.fix_type is None:
        print("Unable to query for gps fix_type")
        return 0
    elif thisPosition.fix_type == 0 or thisPosition.fix_type == 1:
        print("no gps fix")
        return 0
    #else:
    #    print("fix_type missing")
    #    return 0
    
    #value check
    print("lat: " + str(thisPosition.lat))
    print("lon: " + str(thisPosition.lon))
    print("alt: " + str(thisPosition.alt)) 
    if thisPosition.lat >= -90 and thisPosition.lat <= 90:
        if thisPosition.lon > -360 and thisPosition.lon < 360:
            #alt was reporting <0, so this was failing... disabling for now
            #if thisPosition.alt >= 0:
            #could also consider checking the time
            #if thisPosition.time...
            #for now if lat and lon are good let's go
            return 1
    #value check fail
    print ("incorrect latitude or longitude values")
    return 0

def checkBattery(thisBattery, thisPosition, thisHome, destination):
    """
    destination: [lon,lat]
    """
    if destination is not None:
        #check the distance from the current location:                                                                                             
        geodesic_dx_a = Geodesic.WGS84.Inverse(thisPosition.lat, thisPosition.lon, destination[1], destination[0], 1025)
        dx_from_here = geodesic_dx_a.get('s12')
        print("distance to waypoint: " + str(dx_from_here))
        geodesic_dx_b = Geodesic.WGS84.Inverse(destination[1], destination[0], thisHome.lat, thisHome.lon, 1025)
        dx_home_from_there = geodesic_dx_b.get('s12')
        print("distance from waypoint to home: " + str(dx_home_from_there))
        total_dx = dx_home_from_there + dx_from_here
        print("total_dx is " + str(total_dx))
        #implement a model of distance to battery... for now just say ok
        if (1):
            return 1

    #also the more generic checkBattery call with just the battery specified returns a
    if thisBattery is not None:
        if thisBattery.voltage > 0:
            if thisBattery.level > 10:
                #check current
                #if thisBattery.current >= 0:
                #or don't
                return 1
            
    return 0

def checkAirspace(theseWaypoints):
    """
    checkAirspace
    TBD-->check for UVRs, weather, gps, network outages
    """
    return 1

def checkEquipment(thismission):
    """
    checkEquipment
    TBD-->status check for mission specific equipment, such as camera, anemometer, etc
    """
    return 1

def checkCloudResources(thismission):
    """
    checkCloudResources
    TBD-->first, check to see if the mission object specifies any cloud resources
    if so, check them with some status routine... not necessarily reserve them, but inquire if they are reservable
    """
    return 1

def checkEdgeResources(thismission):
    """      
    checkCloudResources 
    TBD-->first, check to see if the mission object specifies any edge resources
    if so, check them with some status routine... not necessarily reserve them, but inquire if they are reservable
    """
    return 1

def acceptMission(pos,basestationIP, thismission):
    x = uuid.uuid4()
    msg = {}
    msg['uuid'] = str(x)
    msg['type'] = "acceptMission"
    msg['CUR_POS'] = pos
    #wait up to 20 minutes for cloud resources to be procured after accepting mission
    serverReply = udpClientMsg(msg, basestationIP, 20001, 1200)
    if serverReply is not None:
        print(serverReply['uuid_received'])
        if serverReply['uuid_received'] == str(x):
            print(serverReply['type_received'] + " receipt confirmed by UUID")
            if 'missionstatus' in serverReply:
                thisMissionStatus = serverReply['missionstatus']
                
                if thisMissionStatus == "canceled":
                    return 0
                elif thisMissionStatus == "confirmed":
                    return 1
                else:
                    return 0
    return 0

def getEntryMissionActions(missiontype):
    mission_actions = []
    if missiontype == "bandwidth":
        mission_actions.append('iperf')
    elif missiontype == "videography":
        mission_actions.append('iperf')
        mission_actions.append('sendFrame')
        #mission_actions.append('sendVideo')
    elif missiontype == "fire":
        mission_actions.append('iperf')
        mission_actions.append('sendFrame')
    return mission_actions

def logState(logfile, state):
    now_rfc3339 = datetime.now().astimezone().isoformat()
    simpleStateJSON = {'time': now_rfc3339, 'state': state }
    result_str = json.dumps(simpleStateJSON)
    print(result_str)

    with open(logfile, "a") as ofile:
        ofile.write(result_str + "\n")
        ofile.close()
        
def udpClientMsg(msg, address, port, timeout_in_seconds):
    try:

        serialMsg = pickle.dumps(msg)
        serverLoc = (address, port)
        chunkSize = 8192
        UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPClientSocket.sendto(serialMsg, serverLoc)
        UDPClientSocket.setblocking(0)
        readiness = select.select([UDPClientSocket], [], [], timeout_in_seconds)
        if readiness[0]:
            #msgFromServer = []
            #while True:
            serialMsgFromServer = UDPClientSocket.recvfrom(chunkSize)
                #if not packet: break
                #msgFromServer.append(packet)
            #serialMsgFromServer = b"".join(msgFromServer)
            try:
                server_msg = pickle.loads(serialMsgFromServer[0])
                print("Reply from Server {}".format(server_msg))
                #print(server_msg)
                return server_msg
            except pickle.UnpicklingError as upe:
                print(upe)
                return None
        else:
            print("timeout")
            return None
    except pickle.PicklingError as pe:
        print("Pickle Error--" + pe)
        return None



def udpFileSend(filename, address, port, buffersz):
    #buffersz could be 1024 or 4096... not sure the best value 
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
        print("could not create udp socket")
        return 1
    #strip out basename
    basename = os.path.basename(filename)
    try:
        sock.sendto(basename.encode(), (address, port))
    except socket.error:
        print("could not send filename")
        return 1

    try:
        ifile = open(filename, "rb")
    except IOerror:
        print("could not find file: " + filename)
        return 1

    chunk = ifile.read(buffersz)
    while (chunk):
        if sock.sendto(chunk, (address, port)):
            chunk = ifile.read(buffersz)
            time.sleep(0.02)

    sock.close()
    ifile.close()
    return 0

def prometheusStatusQuery(prometheusURL):
    response = requests.get(prometheusURL, verify=False, timeout=3)
    online = False
    if response.status_code == 200:
        connected = 1
        print("status query result: " + response.text)
        nodestatusJSON = json.loads(response.content)
        print("status query dump: " + json.dumps(nodestatusJSON))
    else:
        connected = 0
        print("response status: " + str(response.status_code))
			
    if connected and nodestatusJSON["status"] is not None and nodestatusJSON["data"] is not None:
        if (nodestatusJSON["status"] == "success"):
            querydata = nodestatusJSON["data"]
            if querydata["result"] is not None:
                result = querydata["result"]
                if (result):
                    value = result[0]["value"]
                    status = value[1]
                    if (status == "1"):
                        print ("node is online")
                        online = True
                    else:
                        print ("node is offline")
                else:
                    print ("no results present")
            else:
                print ("no results present")
        else:
            print ("query failed")
    else:
        print ("not connected or null result to query")
    return online

def prometheusLoadQuery(prometheusURL):
    response = requests.get(prometheusURL, verify=False, timeout=3)
    if response.status_code == 200:
        print ("load query result: " + response.text)
        nodeloadJSON = json.loads(response.content)
        print ("load query dump: " + json.dumps(nodeloadJSON))
        if (nodeloadJSON["status"] == "success") :
            querydata = nodeloadJSON["data"]
            result = querydata["result"] 
            if (result):
                value = result[0]["value"]
                load = value[1]
                print ("load: " + load)
                return load
            else:
                print ("no load results given")
                return None
        else:
            print("node status: " + nodeloadJSON["status"])
            return None
    else:
        print("response status: " + str(response.status_code))
        return None

