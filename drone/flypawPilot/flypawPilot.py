import requests
import json
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
from aerpawlib.runner import BasicRunner, entrypoint, StateMachine, state, background, timed_state
from aerpawlib.util import VectorNED, Coordinate 
from aerpawlib.vehicle import Vehicle
from aerpawlib.vehicle import Drone

sys.path.append('/root/elyons/flypaw/basestation/basestationAgent')
from flypawClasses import resourceInfo, missionInfo, Position, Battery
#import flypawClasses

class FlyPawPilot(StateMachine):
    def __init__(self):
        self.currentPosition = Position()
        self.currentBattery = Battery()
        self.currentHeading = None
        self.currentHome = None
        self.nextWaypoint = []
        self.previousSelfs = [] 
        self.missions = []
        self.missionstate = None
        self.currentIperfObjArr = []
        self.communications = {}
        self.radio = {}
        self.resources = []
        self.currentWaypointIndex = 0
        self.nextStates = []
        self.logfiles = {}
        self.constantTelemetry = True #indicates a continuous periodic telemetry feed as opposed to one on waypoint entry
        self.telemetryUpdateSeconds = 2 #the number of seconds between periodic telemetry updates if constantTelemetry = True
        self.activated = False #activate after acceptance right before launch... triggers telemetry feed to start and whatever else
        self.videoLocation = "/root/video/video_diff_resolution/example1/video_1280_720.mpg"
        self.frameLocation = "/root/video/video_diff_resolution/example_frames"
        self.basestationIP = "172.16.0.1" #other side of the radio link
        self.videoURL = "udp://" + self.basestationIP + ":23000"
        self.prometheusQueryURL = "http://" + self.basestationIP + ":9090/api/v1/query?query=" 
        #frame can be used for sendVideo or sendFrame depending on mission type
        self.frame = 1

        #eNB location
        self.radio['lat'] = 35.72744
        self.radio['lon'] = -78.69607
        
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

        
    @background
    async def streamTelemetry(self, drone: Drone):
        '''
        periodic background telemetry transmission to basestation  
        enabled by constantTelemetry and activated booleans
        sent every N seconds as determined by telemetryUpdateSeconds
        '''
        if self.constantTelemetry:
            while True:
                if self.activated:
                    #update position and battery and gps and heading
                    statusAttempts = 5
                    statusAttempt = 0
                    while True:
                        print("get position.  Attempt: " + str(statusAttempt))
                        self.currentPosition = getCurrentPosition(drone)
                        if not checkPosition(self.currentPosition):
                            if statusAttempt > statusAttempts:
                                #GPS does not seem to be working... try to go home
                                print("Can't query position.  Abort")
                                with open(self.logfiles['error'], "a") as ofile:
                                    ofile.write("Can't query position.  Abort")
                                    ofile.close()
                                    return "abortMission"
                            else:
                                statusAttempt = statusAttempt + 1
                                await asyncio.sleep(1)
                        else:
                            print("position is communicating")
                            statusAttempt = 0
                            break

                    #update heading, speed, and maybe attitude
                    #self.currentAttitude = getCurrentAttitude(drone)
                    self.currentHeading = drone.heading
                    self.currentGroundspeed = drone._vehicle.groundspeed

                    print ("report telemetry and battery status")
                    recv = await self.reportPositionUDP()
                    if (recv):
                        print("report position to basestation confirmed")
                        self.communications['reportPositionUDP'] = 1
                    else:
                        print("no reply from server while transmitting position")
                        self.communications['reportPositionUDP'] = 0

                #endless loop
                await asyncio.sleep(self.telemetryUpdateSeconds)
            
    #@entrypoint
    @state(name="preflight", first=True)
    async def preflight(self, drone=Drone):
        """
        preflight mission assignment and various status and safety checks and registrations
        """
        
        logState(self.logfiles['state'], "preflight")
        
        #certain failures cause preflight to restart so let's sleep for seconds upon entry
        time.sleep(1)
        
        self.missionstate = "preflight"


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
        Home Check
        TBD--> compare it to your current location I suppose and guess if it's possible
        """
        self.currentHome = drone.home_coords
        if self.currentHome is None:
            print("Please ensure home position is set properly")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("Please ensure home position is set properly")
                ofile.close()
            return "preflight"


        """ 
        Network Check
        TBD--> Placeholder for now... Maybe check your throughput from that pad, or make it a networking system test (UE) rather than iperf
        """
        self.currentIperfObj = None


        """
        Mission Check
        TBD--> develop high level mission overview checks
        """
        self.missions = getMissions(self.basestationIP) #should probably include the position and battery and home info when asking for missions... may preclude some missions
        
        if not self.missions:
            print("No assignment... will check again in 2 seconds")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("No assignment... will check again in 1 second")
                ofile.close()
            #time.sleep(2)
            return "preflight"
        else:
            print("number of missions: " + str(len(self.missions)))
            for thisMission in self.missions:
                print("mission type: " + thisMission.missionType + " leader: " + thisMission.missionLeader + " priority: " + str(thisMission.priority))
                #print out waypoints
                for waypoint in thisMission.default_waypoints:
                    print (str(waypoint[1]) + " " + str(waypoint[0]) + " " + str(waypoint[2]))
                    
        """
        Home Check
        """
        self.currentHome = drone.home_coords
        if self.currentHome is None:
            print("Please ensure home position is set properly")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("Please ensure home position is set properly")
                ofile.close()
            return "preflight"
        
        """
        Airspace Check
        TBD--> A placeholder for future important concepts like weather checks and UVRs.  Traffic also checked with DCB later
        For now just use the first mission
        """
        if not checkAirspace(self.missions[0].default_waypoints):
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
        print("accepting mission... this can take up to 20 minutes to get confirmation while cloud resources are reserved")
        missionAccepted = acceptMission(self.basestationIP, self.missions[0])
        if missionAccepted:
            print (self.missions[0].missionType + " mission accepted")
            
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
        self.resources = getResourceInfo(self.basestationIP)
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
        if not drone.armed:
            print("drone not armed. Arming")
            await drone.set_armed(True)
            print("arming complete")
        else:
            print("drone is already armed")

        #ok... let's go!
        return "takeoff"

    @state(name="takeoff")
    async def takeoff(self, drone: Drone):
        print("takeoff")
        
        #takeoff to height of the first waypoint or 25 meters, whichever is higher                                                                                                
        if len(self.missions[0].default_waypoints) > 1:
            target_alt = self.missions[0].default_waypoints[1][2]
        else:
            print("recheck your mission")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("recheck your mission")
                ofile.close()
            return "preflight"

        if target_alt < 30:
            target_alt = 30

        print("takeoff to " + str(target_alt) + "m")
        await drone.takeoff(target_alt)
        print("reached " + str(target_alt) + "m")
        
        #you should be at default_waypoints[1] now
        #with [1] being directly above [0], which is the home position on the ground                                                                                              
        self.currentWaypointIndex = 1
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
        while True:
            print("get position.  Attempt: " + str(statusAttempt))
            self.currentPosition = getCurrentPosition(drone)
            if not checkPosition(self.currentPosition):
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
                print("position is communicating")
                statusAttempt = 0
                break
               
        while True:
            print("check battery.  Attempt: " + str(statusAttempt))
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
                print("battery is communicating")
                statusAttempt = 0
                break
        
        #self.currentAttitude = getCurrentAttitude(drone)
        self.currentHeading = drone.heading
        

        #lets look at our next waypoint right away... don't love putting this here
        if not len(self.missions[0].default_waypoints) > (self.currentWaypointIndex + 1):
            print("no more waypoints... go home if not already there and land")  
            return "abortMission"

        self.nextWaypoint = []
        self.nextWaypoint.append(self.missions[0].default_waypoints[self.currentWaypointIndex + 1][0])
        self.nextWaypoint.append(self.missions[0].default_waypoints[self.currentWaypointIndex + 1][1])
        self.nextWaypoint.append(self.missions[0].default_waypoints[self.currentWaypointIndex + 1][2])

        #if we're not sending telemetry periodically in the background, send it now
        if not self.constantTelemetry:
            print ("report telemetry and battery status")
            recv = await self.reportPositionUDP()
            if (recv):
                print("report position to basestation confirmed")
                self.communications['reportPositionUDP'] = 1
            else:
                self.communications['reportPositionUDP'] = 0
                print("no reply from server while transmitting position")
       
        #check for mission actions to be performed at the start of this state
        #if the drone is the mission leader, or there's no comms to the basestation
        if not self.communications['reportPositionUDP'] or self.missions[0].missionLeader == "drone":
            self.nextStates = getEntryMissionActions(self.missions[0].missionType)

        else:
            #if you have comms and the basestation is the leader, ask what to do
            print("asking what to do")
            self.nextStates = await self.instructionRequest()
            #if you don't have any instructions figure it out for yourself
            if not self.nextStates:
                print("no answer... we're on our own")
                self.nextStates = getEntryMissionActions(self.missions[0].missionType)

        return "nextAction"
        
        
    @state(name="flight")
    async def flight(self, drone: Drone):
        logState(self.logfiles['state'], "flight")
        #check if we have enough to go, at minimum, from here to the next default waypoint and to home
        print ("check for sufficient battery... note, no good way to do this yet, so it's a placeholder")
        if not len(self.missions[0].default_waypoints) > (self.currentWaypointIndex + 1):
            print("no more waypoints... go home if not already there and land")
            return "abortMission"

        battery_check = checkBattery(self.currentBattery, self.currentPosition, self.currentHome, self.missions[0].default_waypoints[self.currentWaypointIndex + 1])
        if not battery_check:
            print("battery check fail")
            with open(self.logfiles['error'], "a") as ofile:
                ofile.write("battery check fail.  Abort")
                ofile.close()
            return "abortMission"

        defaultNextCoord = Coordinate(self.missions[0].default_waypoints[self.currentWaypointIndex + 1][1], self.missions[0].default_waypoints[self.currentWaypointIndex + 1][0], self.missions[0].default_waypoints[self.currentWaypointIndex + 1][2])
        

        ##set heading... unnecessary unless we want to have a heading other than the direction of motion 
        #drone.set_heading(bearing_from_here)
        
        await drone.goto_coordinates(defaultNextCoord)

        #if you are not using await above, delete this
        self.currentWaypointIndex = self.currentWaypointIndex + 1
        
        """
        below, implement things to do while flying... skip for now... might have to remove the await statement above to do this stuff
        while True:
            #perform mission stuff like iperf eventually, but here just track your progress                                                                           
            while True:
                self.currentPosition = getCurrentPosition(drone)
                if not checkPosition(self.currentPosition):
                    if statusAttempt > statusAttempts:
	                #GPS does not seem to be working... try to go home               
                        print("Can't query position.  Abort")
                        return "abortMission"
                    else:
                        statusAttempt = statusAttempt + 1
                        time.sleep(1)
                else:
                    #position seems fine                                                                                                                 
                    statusAttempt = 0
                    break
            
            geodesic_dx = Geodesic.WGS84.Inverse(self.currentPosition.lat, self.currentPosition.lon, self.missions[0].default_waypoints[self.currentWaypointIndex + 1][1], self.missions[0].default_waypoints[self.currentWaypointIndex + 1][0], 1025)
            flight_dx_from_here = geodesic_dx.get('s12')
            print(str(self.currentPosition.lat) + " " + str(self.currentPosition.lon) + " " + str(self.currentPosition.alt))
            #get within 5 meters?                                                                                                                                     
            if flight_dx_from_here < 5:
                print("arrived at initial waypoint")
                self.currentWaypointIndex = self.currentWaypointIndex + 1
                break
            time.sleep(1)
        """
        #you've arrived at your next waypoint
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
                
    @timed_state(name="iperf",duration = 20)
    async def iperf(self, drone: Drone):
        print("iperf state")
        logState(self.logfiles['state'], "iperf")

        params = self.nextStates[0]['parameters']
        print("params: " + json.dumps(params))
        #pop this state
        self.nextStates.pop(0)
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
        iperfResult = await self.runIperf(self.basestationIP, drone)
        print("iperf result finished")
        print(iperfResult['iperfResults'])
        iperfObjArr.append(iperfResult['iperfResults'])

        #now yaw toward the radio and do it again
        geodesic_azi = Geodesic.WGS84.Inverse(self.currentPosition.lat, self.currentPosition.lon, self.radio['lat'], self.radio['lon'], 512)
        bearing_to_radio = geodesic_azi.get('azi1')
        print("set bearing to " + str(bearing_to_radio))
        await drone.set_heading(bearing_to_radio)
        print("bearing set, now run iperf again")
        #now toward the radio                                                                                                                
        iperfResult = await self.runIperf(self.basestationIP, drone)
        print("second iperf result finished")
        print(iperfResult['iperfResults'])
        iperfObjArr.append(iperfResult['iperfResults'])
        
        #at the end append all the individual iperf results to the self array
        self.currentIperfObjArr.append(iperfObjArr)
        
        return "nextAction"

    @state(name="sendFrame")
    async def sendFrame(self, _ ):
        logState(self.logfiles['state'], "sendFrame")
        print("sendFrame state")
        
        params = self.nextStates[0]['parameters']
        print("params: " + json.dumps(params))
        self.nextStates.pop(0)
        
        if (self.frame > 1401): #only because the test data has like 1450 frames
            self.frame = 1

        framestr = str(self.frame).zfill(7) + ".jpg"
        framefn = self.frameLocation + "/" + framestr

        #move the below elsewhere
        #figure out where to send
        #i) check prometheus
        #up_array = []
        #load_array = []
        #for resource in self.resources:
        #    externalIP = None
        #    for address in resource.resourceAddresses:
        #        print("address type: " + address[0])
        #        if (address[0] == "external"):
        #            externalIP = address[1]
        #            statusQueryURL = self.prometheusQueryURL + 'up{instance="' + externalIP + ':8095"}'
        #            print("status query: " + statusQueryURL)
        #            nodeOnline = prometheusStatusQuery(statusQueryURL)
        #            nodeOnlineObj = {}
        #            nodeOnlineObj['externalIP'] = externalIP
        #            nodeOnlineObj['online'] = nodeOnline
        #            if nodeOnlineObj not in up_array:
        #                up_array.append(nodeOnlineObj)
        #            if nodeOnline:
        #                loadQueryURL = self.prometheusQueryURL + 'node_load1{instance="' + externalIP + ':8095"}'
        #                print("load query: " + loadQueryURL)
        #                loadResult = prometheusLoadQuery(loadQueryURL)
        #                loadObj = {}
        #                if loadResult is not None:
        #                    loadObj['externalIP'] = externalIP
        #                    loadObj['load'] = loadResult
        #                    load_array.append(loadObj)

        #minload = 100.1
        #bestnode = None
        #for onlineNode in load_array:
        #    load = float(onlineNode['load'])
        #    print("node: " + onlineNode['externalIP'])
        #    print("load: " + str(load))
        #    if load < minload:
        #        bestnode = onlineNode['externalIP']
        #        minload = load
        #if bestnode is not None:
        #    print("send to: " + bestnode)
                    
        #    fileSendFail = udpFileSend(framefn, bestnode, 8096, 1024) #try 1024 for buffer size for now

        fileSendFail = udpFileSend(framefn, params['ipaddr'], params['port'], params['chunksize'])
        if fileSendFail:
            print("couldn't send video")
        else:
            print("successfully sent frames")
            self.frame = self.frame + 50
            
            x = uuid.uuid4()
            msg = {}
            msg['uuid'] = str(x)
            msg['type'] = "sendFrame"
            msg['sendFrame'] = {}
            serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
            if serverReply is not None:
                print(serverReply['uuid_received'])
                if serverReply['uuid_received'] == str(x):
                    print(serverReply['type_received'] + " receipt confirmed by UUID")

        return "nextAction"
    
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
        serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")

        #pop this state
        self.nextStates.pop(0)
                
        return "nextAction"

        
    @state(name="collectVideo")
    async def collectVideo(self, _ ):
        logState(self.logfiles['state'], "collectVideo")
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "collectVideo"
        msg['collectVideo'] = {}
        serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")

        #pop this state
        self.nextStates.pop(0)
                
        return "nextAction"

    @state(name="abortMission")
    async def abortMission(self, drone: Drone):
        logState(self.logfiles['state'], "abortMission")
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "abortMission"
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
        print("cleaning up")
        logState(self.logfiles['state'], "completed")
        x = uuid.uuid4()
        msg = {}
        msg['uuid'] = str(x)
        msg['type'] = "completed"
        serverReply = udpClientMsg(msg, self.basestationIP, 20001, 1)
        if serverReply is not None:
            print(serverReply['uuid_received'])
            if serverReply['uuid_received'] == str(x):
                print(serverReply['type_received'] + " receipt confirmed by UUID")
        print("exiting")
        sys.exit()
        
    @state(name="nextAction")
    async def nextAction(self, _ ):
        #check to see if we have anything else pending to do                                                                                                                         
        logState(self.logfiles['state'], "nextAction")
        if self.nextStates:
            print("we have states pending")
            for st in self.nextStates:
                print(json.dumps(st))
                
            while self.nextStates:
                reqIsValid = validateRequest(self.nextStates[0]['command'])
                if not reqIsValid:
                    print("state: " + self.nextStates[0]['command'] + " is not valid")
                    self.nextStates.pop(0)
                else:
                    print("state: " + self.nextStates[0]['command'] + " is valid")
                    nextState = self.nextStates[0]['command']
                    #maybe don't pop til the end of the next state?
                    #self.nextStates.pop(0)
                    return nextState
                
        #nothing pending
        #if basestation or cloud is the leader, return instruction request as default

        if self.missions:
            if self.missions[0].missionLeader == "basestation" or self.missions[0].missionLeader == "cloud":
                self.nextStates = await self.instructionRequest()
                if not self.nextStates:
                    #if you get nothing back just fly
                    self.nextStates.push("flight")
                    return "flight"
                    
        #if drone is the missionLeader, return flight
        return "flight"
    
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
        
    async def reportPositionUDP(self):
        print (str(self.currentPosition.lat) + " " + str(self.currentPosition.lon) + " " + str(self.currentPosition.alt) + " " + str(self.currentPosition.time))
    
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
        print("logging telemetry")
        
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
        
        print("sending telemetry")
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

    
def getMissions(basestationIP):
    '''
    returns a new mission from the basestation
    '''
    x = uuid.uuid4()
    msg = {}
    msg['uuid'] = str(x)
    msg['type'] = "mission"
    serverReply = udpClientMsg(msg, basestationIP, 20001, 2)
    if serverReply is not None:
        print(serverReply['uuid_received'])
        if serverReply['uuid_received'] == str(x):
            print(serverReply['type_received'] + " receipt confirmed by UUID")
            if 'missions' in serverReply:
                missions = serverReply['missions']
                return missions
    return None

def getResourceInfo(basestationIP):
    '''
    returns a list of your external resources in the resourceInfo class
    '''
    x = uuid.uuid4()
    msg = {}
    msg['uuid'] = str(x)
    msg['type'] = "resourceInfo"
    #wait up to a minute to get resource info
    serverReply = udpClientMsg(msg, basestationIP, 20001, 60)
    if serverReply is not None:
        print(serverReply['uuid_received'])
        if serverReply['uuid_received'] == str(x):
            print(serverReply['type_received'] + " receipt confirmed by UUID")
            if 'resources' in serverReply:
                resources = serverReply['resources']
                return resources
    return None
                    
def getCurrentPosition(drone: Drone):
    '''
    get the position of the drone
    '''
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
    '''
    get the battery state of the drone
    '''
    if drone.connected:
        battery = drone.battery
        thisBattery = Battery()
        thisBattery.voltage = battery.voltage
        thisBattery.current = battery.current
        thisBattery.level = battery.level
        return thisBattery
    else:
        return None

def getCurrentAttitude(vehicle: Vehicle):
    '''
    get the attitude of the drone
    '''
    #not currently working
    #    if drone.connected:
    #        attitude = drone.Attitude
    #        currentAttitude = {}
    #        currentAttitude['pitch'] = attitude[0]
    #        currentAttitude['yaw'] = attitude[1]
    #        currentAttitude['roll'] = attitude[2]
    #        return currentAttitude
    #    else:
    return None

def getVideoLocation():
    '''
    check on the specific camera software configuration
    maybe add a camera argument
    just hardcode for now as Aerpaw vehicles do not yet have a camera
    '''
    videoLocation = "/opt/video/"
    return videoLocation
    
    
def validateRequest(request):
    '''
    make sure any action the basestation is telling you to do is a known command
    '''
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
    '''
    a function to validate a reported position
    '''
    #print(thisPosition.lat)
    #print(thisPosition.lon)
    
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
    if thisPosition.lat >= -90 and thisPosition.lat <= 90:
        if thisPosition.lon > -360 and thisPosition.lon < 360:
            if thisPosition.alt >= 0:
                #if thisPosition.time... 
                #or don't
                return 1
    #value check fail
    print ("incorrect latitude or longitude values")
    return 0

def checkBattery(thisBattery, thisPosition, thisHome, destination):
    '''
    a function to make sure the vehicle has enough battery to move to a position and still return home thereafter
    this is a good idea, but without a good battery usage model, we can't do this correctly 
    '''

    #destination: [lon,lat]
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
    checkAirspace stub
    TBD-->check for UVRs, weather, gps, network outages
    """
    return 1

def checkEquipment(thismission):
    """
    checkEquipment stub
    TBD-->status check for mission specific equipment, such as camera, anemometer, etc
    """
    return 1

def checkCloudResources(thismission):
    """
    checkCloudResources stub
    Right now the basestation is handling this, though this could be an explicit check for such on the drone side
    TBD-->first, check to see if the mission object specifies any cloud resources
    if so, check them with some status routine... not necessarily reserve them, but inquire if they are reservable
    """
    return 1

def checkEdgeResources(thismission):
    """      
    checkEdgeResources stub
    We don't have any edge resources right now aside from the basestation... could check that if necessary
    TBD-->first, check to see if the mission object specifies any edge resources
    if so, check them with some status routine... not necessarily reserve them, but inquire if they are reservable
    """
    return 1

def acceptMission(basestationIP, thismission):
    '''
    this function accepts the mission given to the drone
    upon acceptance the basestation registers the flight and may spin up cloud resources so we allow up to 20 minutes for a response that we are ready for launch
    '''
    x = uuid.uuid4()
    msg = {}
    msg['uuid'] = str(x)
    msg['type'] = "acceptMission"
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
    '''
    these are things we do upon arrival at a waypoint, if any
    '''
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
    '''
    this dumps the current state machine state into a file to record the state transitions
    '''
    now_rfc3339 = datetime.now().astimezone().isoformat()
    simpleStateJSON = {'time': now_rfc3339, 'state': state }
    result_str = json.dumps(simpleStateJSON)
    print(result_str)

    with open(logfile, "a") as ofile:
        ofile.write(result_str + "\n")
        ofile.close()
        
def udpClientMsg(msg, address, port, timeout_in_seconds):
    ''' 
    a udp socket message wrapper with a pre defined max wait time for a response
    '''
    try:
        serialMsg = pickle.dumps(msg)
        serverLoc = (address, port)
        chunkSize = 4096
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
        print(pe)
        return None

def udpFileSend(filename, address, port, buffersz):
    '''
    a udp socket wrapper for file transfer
    '''
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
    '''
    a wrapper to query a prometheus server for status info to make sure cloud or edge resources are online
    '''
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
    '''
    a wrapper to query a prometheus server for load info on resources as a precursor to do explicit load balancing
    '''
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

