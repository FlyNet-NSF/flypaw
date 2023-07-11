#!/usr/bin/env python3
import json
import copy
from pickle import FALSE
from queue import Empty
from geographiclib.geodesic import Geodesic
import jsonpickle
from datetime import *
import time


class Position(object):
    """
    lon: float units degrees (-180..180)
    lat: float units degrees (-90..90)
    alt: float units M AGL
    time: str, iso8601 currently
    fix_type: int (0..4), 0-1 = no fix, 2 = 2D fix, 3 = 3D fix
    satellites_visible: int (0..?)
    """
    def __init__(self):
        self.lon = float
        self.lat = float
        self.alt = float
        self.time = str
        self.fix_type = int
        self.satellites_visible = int
    def InitParams(self,lon,lat,alt,time,fix,satellites):
        self.lon = lon
        self.lat = lat
        self.alt = alt
        self.time = time
        self.fix_type = fix
        self.satellites_visible = satellites
    def __str__(self):
        return "(Lat:" + str(self.lat) + " Lon:" + str(self.lon) + " Altitude:" + str(self.alt) + ")"
    def __repr__(self):
        return "(Lat:" + str(self.lat) + " Lon:" + str(self.lon) + " Altitude:" + str(self.alt) + ")"

class Battery(object):
    """
    voltage: float units V
    current: float units mA
    level: int unitless (0-100)
    m_kg: battery mass, units kg
    """
    def __init__(self):
        self.voltage = float
        self.current = float
        self.level = float
        self.m_kg = float
        
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

class sendFrameInfo(object):
    def __init__(self, dataformat="jpgframes", ipaddr="172.16.0.1", port="8096", priority=1):
        self.dataformat = dataformat #jpgframes, ffmpeg, etc
        self.ipaddr = ipaddr #string ip address
        self.port = port #int port number
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
        self.tasks = []#tasks associated with each waypoint
        self.missionType = str #videography, delivery, air taxi, etc.
        self.missionLeader = str #basestation, drone, cloud, edge device(s)
        self.priority = float #normalized float from 0-1
        self.planfile = str #path to planfile optional 
        self.name = str #the name of the mission
        self.resources = bool #true-> outside resources/edge devices false-> just drone and basestation
        self.STATUS = str
        self.missionObjectives = []

class MissionObjective(object):
        def __init__(self,way,type,static):
            self.Waypoint = way
            self.Type = type
            self.Static = static

        
class resourceInfo(object):
    def __init__(self):
        self.name = str #identifier for resource
        self.location = str #edge, cloud x, cloud y
        self.purpose = str #mission related I guess
        self.interface = str #thinking something like direct vs kubectl
        self.resourceAddresses = [] #one or more ways to communicate with resource... possibly a pairing? eg ("management", "xxx.xxx.xxx.xxx")
        self.state = str #resource reservation state
        self.load = float #placeholder for now... maybe if we have info from prometheus or something
    
class VehicleCommands(object):#This is like a task?
    def __init__(self):
        self.commands = {}
        self.commands['iperf'] = {}
        self.commands['sendFrame'] = {}
        self.commands['sendVideo'] = {} 
        self.commands['collectVideo'] = {}
        self.commands['flight'] = {}
        
    def setIperfCommand(self, iperfObj):
        self.commands['iperf'] = { "command" : "iperf", "protocol": iperfObj.protocol, "ipaddr": iperfObj.ipaddr, "port": iperfObj.port, "priority": iperfObj.priority } 
    def setCollectVideoCommand(self, collectVideoObj):
        self.commands['collectVideo'] = { "command" : "collectVideo", "dataformat" : collectVideoObj.dataformat, "duration": collectVideoObj.duration, "quality": collectVideoObj.quality, "priority": collectVideoObj.priority }
    def setSendFrameCommand(self, sendFrameObj):
        self.commands['sendFrame'] = { "command" : "sendFrame", "dataformat" : sendFrameObj.dataformat, "ipaddr": sendFrameObj.ipaddr, "port": sendFrameObj.port, "priority": sendFrameObj.priority  }
    def setSendVideoCommand(self, sendVideoObj):
        self.commands['sendVideo'] = { "command" : "sendVideo", "dataformat" : sendVideoObj.dataformat, "ipaddr": sendVideoObj.ipaddr, "port": sendVideoObj.port, "priority": sendVideoObj.priority  }
    def setFlightCommand(self, flightObj):
        self.commands['flight'] = { "command" : "flight", "destination" : flightObj.destination, "speed": flightObj.speed, "priority": flightObj.priority }
    def setMissionCommand(self, missionObj):
        self.commands['mission'] = { "command": "mission", "defaultWaypoints": missionObj.defaultWaypoints, "missionType": missionObj.missionType, "missionControl": missionObj.missionControl, "priority": missionObj.priority }

class droneSim(object):
    def __init__(self):
        self.position = Position()
        self.nextWaypoint = []
        self.battery = Battery()
        self.heading = float
        self.home = []


class taskedWaypoint(object):
    def __init__(self):
        self.position = Position()
        self.task = str
        self.TimeSensitive = bool

class Task(object):
    def __init__(self, pos,task,sensitive,prio,uid):
        self.position = pos
        self.task = task
        self.TimeSensitive = sensitive
        self.priority = prio
        self.comms_required = False
        self.dynamicTask = False
        self.uniqueID = uid
        self.LocationLocked = False
        self.ConnectionConfirmed = False

    def Actionable(self):#Stub, needs to be implemented--dictates whether a task can be completed under the current circumstances
        x=0

    def ChangePosition(self,pos:Position):
        if(not self.LocationLocked):
            self.position = pos
            return True
        else:
            return False



    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result


#Ensures IDs for tasks are unique and assigned by a third party....maybe I should've just built it into TaskQ, something like, NewEmptyTask()
class TaskIDGenerator(object):
    def __init__(self):
        self.CurrentTaskID= 0

    def Get(self):
        id = self.CurrentTaskID
        self.CurrentTaskID = self.CurrentTaskID + 1
        return id


    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result

class IDGenerator(object):
    def __init__(self):
        self.CurrentID= 0

    def Get(self):
        id = self.CurrentID
        self.CurrentID = self.CurrentID + 1
        return id

    def Check(self):
        return self
    


class TaskStopwatch(object):
    def __init__(self,t:Task):
        self.StartTime = None
        self.EndTime = None
        self.Task = t
        self.Started = False
        self.Stopped = False
        

    def StartWatch(self):
        if(not self.Started):
            self.StartTime = time.time()
            self.Started = True
        else:
            x=0
            #throw Exception
    

    def StopWatch(self):
        if((not self.Stopped) and self.Started):
            self.EndTime = time.time()
            self.Stopped = True
        else:
            x=0
            #throw Exception

    def GetTime(self):
        if((self.Stopped) and self.Started):
            return self.EndTime-self.StartTime
        else:
            x=0

class WatchDog(object):
    def __init__(self):
        self.Stopwatches = dict()
        self.Actions = dict()#tasks
        self.ActionTimeStamps = dict()#timestamp completed
        self.OrderofExecution = dict()
        self.keys = list()
        self.InitializedStopwatches = False
        self.StartedStopwatches = False
        self.WatchdogStartStamp = None
        self.ExecutionOrderGenerator = IDGenerator()
        self.Normal:TaskPenaltyNormalizer = None
        self.LastTimeStamp = None
        self.StartingPosition = None

    def GetStartingPosition(self):

        if(self.StartingPosition==None):
            self.StartingPosition = Position()
            self.StartingPosition.InitParams(-78.69611, 35.727279,0,0,0,0)
            return self.StartingPosition
        else:
            return self.StartingPosition


    def InitStopwatches(self,criticalTasks:list):
        x=0
        for t in criticalTasks:
            sw:TaskStopwatch = TaskStopwatch(t)
            self.Stopwatches[t.uniqueID]=sw
        self.InitializedStopwatches = True
        
    def StartStopwatches(self):
        if(not self.StartedStopwatches):
            for sw in self.Stopwatches:
                self.Stopwatches.get(sw).StartWatch()
            self.StartedStopwatches = True 
            self.WatchdogStartStamp = time.time()
            self.LastTimeStamp = self.WatchdogStartStamp
        else:
            x=0#throw exception

    def ActionComplete(self,task:Task):
        print("ACTION COMPLETE!")
        if(not self.Actions.get(task.uniqueID)):
            self.Actions[task.uniqueID] = task
            self.ActionTimeStamps[task.uniqueID] = time.time()
            self.lastTimeStamp = self.ActionTimeStamps[task.uniqueID]
            print("TTE: " + str(self.LastTimeStamp))
            self.CheckStopwatches(task.uniqueID)
            self.keys.append(task.uniqueID)
            self.OrderofExecution[task.uniqueID] = self.ExecutionOrderGenerator.Get()
        else:
            print("Watchdog Error: Action Completed Twice Exist!")

    def CheckStopwatches(self,id):
        if(not self.Stopwatches.get(id)):
            #error
            x=0
        else:
            self.Stopwatches.get(id).StopWatch()

    def Print(self):
        for k in self.keys:
            print("Task ID: "+ str(k)+ " Action: "+ str(self.Actions.get(k).task))
    #OBSOLETE FIX TO MATCH GE ACTION LIST
    def DumpReport(self):
        records = list()
        lastTime = 0
        for k in self.keys:
            if(self.Actions.get(str(k))):
                t:Task = self.Actions.get(str(k))
                d_time = self.ActionTimeStamps.get(str(k))-lastTime
                lastTime = self.ActionTimeStamps.get(str(k))
                penalty = 0
                if(t.comms_required):
                    penalty = self.ActionTimeStamps.get(str(k)) - self.WatchdogStartStamp 
                rec = ActionRecord(d_time,t.task,t.position,penalty,"",100)
                records.append(rec)
            else:
                print("DumpReport:ERROR!")
        JSON_DUMP_LIST = jsonpickle.encode(records)
        with open('ActionRecord.json','w') as f:
            f.write(JSON_DUMP_LIST)

    def GetActionList(self):
        
        records = list()
        lastTime = 0
        iteratorType = "STRING"
        print("Action List Keys: "+str(self.keys.__len__()))
        print("KEYS: ")
        print(str(self.keys))
        print(str(self.Actions))
        JSON_DUMP_LIST = jsonpickle.encode(self.Actions)
        with open('ActionError.json','w') as f:
            f.write(JSON_DUMP_LIST)
        for j in self.Actions.keys():
            keyType = type(j)

        for k in self.keys:

            if(keyType==str):
                x=0
                k_itr = str(k)
            else:
                x=0
                k_itr = int(k)

            if(self.Actions.get(k_itr)):
                t:Task = self.Actions.get(k_itr)
                
                if(records.__len__()<1):
                    d_time = self.ActionTimeStamps.get(k_itr)-self.WatchdogStartStamp
                else:
                    d_time = self.ActionTimeStamps.get(k_itr)-lastTime
                lastTime = self.ActionTimeStamps.get(k_itr)
                penalty = 0
                if(t.comms_required):
                    penalty = self.ActionTimeStamps.get(k_itr) - self.WatchdogStartStamp
                rec = ActionRecord(d_time,t.task,t.position,penalty,"",100)
                records.append(rec)
            else:
                print("GetActionList:ERROR!")

        return records
        
            

        
class ActionRecord(object):
    def __init__(self, tte,t:Task,pos:Position,penalty,decision,confidence):
        self.TimeToExecute = tte
        self.Task = t
        self.Position = pos
        self.Penalty = penalty
        self.Decision = decision
        self.Confidence = confidence
        self.Caller = ""

class Solution(object):
    def __init__(self):
        self.OptionNumber = -1
        self.TimeStamp = None
        self.HaltTask = None
        self.Priority = ""
        self.Distance = 0
        self.Record = list() #of action record
        self.Confidence = 100.0
        self.DecisionStack = list()#of decisions
        self.Penalty:TaskPenaltyTracker = None




class SpeculativeProduct(object):
    def __init__(self):
        self.Solutions  = list()
        self.ElectedSolution = -1 #soln. number
        self.Priority = ""
        self.Confidences = list()
        self.Delays = list()
        self.SolutionsCount  = 0
        self.Specifications = list()
        

    def Recommend(self):
        priority = self.Priority
        bestSolution:Solution = self.Solutions[0]
        
        for sol in self.Solutions:
            if(priority == "DISTANCE"):
                if(sol.Distance<bestSolution.Distance):
                    bestSolution = sol
            if(priority == "CONFIDENCE"):
                if(sol.Confidence>bestSolution.Confidence):
                    bestSolution = sol
            if(priority == "PENALTY"):
                if(sol.Penalty.TotalPenalty()<bestSolution.Penalty.TotalPenalty()):
                    bestSolution = sol
        print("Based on "+ priority + " option #" + str(bestSolution.OptionNumber) + " is the optimal solution")#need a space here U.U
        self.ElectedSolution = bestSolution.OptionNumber

    def GetRecommendation(self):
        if(self.ElectedSolution > -1):
            return self.Solutions[self.ElectedSolution]
        


class ExperimentResults(object):
    def __init__(self):
        self.SpeculativeSolutionSets  = list()
        self.ExecutionRecord = 0 #soln. number



class WaypointHistory(object):
    def __init__(self):
        self.TrueWaypointsAndConnection =[]
        self.WaypointsAndConnection = []#list of Tuples (waypoint,connection_status,id)
        self.Count = 0
        self.TrueCount = 0
    def _empty(self):
        if(self.Count<1):
            return 1
        else:
            return 0


    def __deepcopy__(self, memo):
        #print('Class'+ str(self.__class__))
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result

    def AddPoint(self,Waypoint,Connected):#compresses into tuple
        self.WaypointsAndConnection.insert(0,(Waypoint,Connected,self.TrueCount))
        self.TrueWaypointsAndConnection.insert(0,(Waypoint,Connected,self.TrueCount))
        self.Count = self.Count + 1
        self.TrueCount = self.TrueCount + 1

    def StackPop(self):#return tuple
        if(not self._empty()):
            self.Count = self.Count - 1
            return self.WaypointsAndConnection.pop(0)

        else:
            return None

    def Peek(self):


        if(not self._empty()):
            return self.WaypointsAndConnection[0]
        else:
            return None


    def PeekConnectivity(self):
        if(not self._empty()):
            tuple = self.WaypointsAndConnection[0]
            return tuple[1]
        else:
            return None


    def BackTrackPathForConnectivity(self):
        Connected = 0
        StartingLocation = self.StackPop()
        StepsBack = []
        StepsForward = []
        tasks = []
        StepsForward.insert(0,StartingLocation)
        while((not Connected)and (not self._empty())):
            if(self.PeekConnectivity()):
                Step = self.StackPop()
                #print("Step Popped: "+ str(Step))
                StepsBack.append(Step)
                Connected = 1
            else:
                Step = self.StackPop()
                #print("Step Popped: "+ str(Step))
                StepsBack.append(Step)
                StepsForward.insert(0,Step)
        if(self._empty() and (not Connected)):
            print("BackTrackError1")
            return None
        else:
            StepsBack.extend(StepsForward)
            return StepsBack



            
    def PrintWorkingHistory(self):
        print("History:")
        print("TrueCount: "+ str(self.TrueCount))
        print("Working Count: "+ str(self.Count))
        for tuple in self.TrueWaypointsAndConnection:
            print("ID: "+ str(tuple[2]) + " Position: "+ str(tuple[0])+ " Connected: "+ str(bool(tuple[1])))


    def PrintListOfStepsGeneric(self,list):
        for tuple in list:
            print("ID: "+ str(tuple[2]) + " Position: "+ str(tuple[0])+ " Connected: "+ str(bool(tuple[1])))


class TaskQueue(object):

    def __init__(self):
        self.queue = []
        self.Count = 0
        self.TaskLock = TaskHold()
    def PushTask(self, task:Task):
        self.queue.insert(0,task)
        self.Count =  self.Count + 1
    def AppendTask(self, task:Task):
        self.queue.append(task)
        self.Count =  self.Count + 1    
    def AppendTasks(self, tasks):
        for task in tasks:
            self.queue.append(task)
            self.Count =  self.Count + 1  

    def PopTask(self):
        if(self.queue):
            self.Count = self.Count-1 #Adjust count
            return self.queue.pop(self.Count)#Pop item at end of queue
    def EnvelopeNextTask(self,tasks,pos):
        nextTask = self.PopTask()
        tasks.insert(nextTask,pos)
        for task in tasks :
            self.AppendTask(task)

        
    def PrintQ(self):#change this to lower case please
        if self.Empty():
            print("Empty!")
        else:
            print("")
            print("============")
            print("====TOP\u2193 ===")
            for idx, task in enumerate(self.queue):
                if(task.dynamicTask):
                    print("|D"+str(task.task).rjust(10,"+")+"|")
                else:
                    print("|"+str(task.task).rjust(10," ")+"|")
                #print("Task#: "+str(idx)+" Lat:"+ str(task.position.lat)+ " Lon:"+ str(task.position.lon)+" Alt:"+ str(task.position.alt) )
            print("===BOTTOM===")
            print("============")
            print("Count: "+ str(self.Count))
            print("Next Task: " + str(task.task) + ": Position-- Lat:"+ str(task.position.lat)+ " Lon:"+ str(task.position.lon)+" Alt:"+ str(task.position.alt))
            print("")
            print("Task Hold:")
            print("============")
            print("Count: " + str(self.TaskLock.Captives.__len__()))
            print("============")
            print("-----------------------------------------------")


    def Empty(self):
        if(self.Count == 0):
            return True
        elif(self.Count>0): 
            return False

    def Peek(self):#Same function as next ???
        if(not self.Empty()):
            return self.queue[self.Count-1]
        else:
            return None

    def NextTask(self):
        if not self.Empty():
            return self.queue[self.Count-1]
        else:
            return False
    def AppendTask(self,task):
        self.queue.append(task)
        self.Count =  self.Count + 1

    def HoldTopTask(self):
        self.TaskLock.HoldTask(self.PopTask())


    def Release(self):
        task = self.TaskLock.ReleaseTask()
        self.AppendTask(task)

    def ReleaseModifyPos(self,pos:Position):
        task:Task = self.TaskLock.ReleaseTask()
        task.ChangePosition(pos)
        self.AppendTask(task)

    def GetCriticalTasks(self):
        x=0
        taskList = list()
    
        for t in self.queue:
            if(t.comms_required):
                taskList.append(t)

        return taskList
    

    def CaptivesHeld(self):
        x=0
        if(self.TaskLock.Count<1):
            return False
        else:
            return True


    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result



    
    


class TaskPenaltyTracker(object):
    def __init__(self, Q:TaskQueue, watchDog:WatchDog,wph:WaypointHistory):
        
        self.taskID = list()    
        self.taskStatus = list()    
        self.taskDelay = list()
        self.ShortestTransmission = list()
        self.AoI = list()
        self.Penalties = list()
        memo = dict()

        totalExecutedTripTime = self.GetTotalExecutedTime(watchDog)
        
        for t in Q.queue:
            if(t.comms_required):
                self.AddTaskWithDelay(t.uniqueID,totalExecutedTripTime)

    def AddTask(self, TaskID):
        if( (self.FindTaskByID(TaskID)==-1)):
            self.taskID.append(TaskID)
            self.taskStatus.append("NOT-HALTED")
            self.taskDelay.append()



    def AddTaskWithDelay(self, TaskID, delay):
        if( (self.FindTaskByID(TaskID)==-1)):
            self.taskID.append(TaskID)
            self.taskStatus.append("NOT-HALTED")
            self.taskDelay.append(delay)
            self.ShortestTransmission.append(delay) 
            self.Penalties.append(-1)
            self.AoI.append(0)

    def HaltTask(self, TaskID, wph:WaypointHistory, Q:TaskQueue):
        index = self.FindTaskByID(TaskID)
        if(self.taskStatus[index]=="NOT-HALTED"):
            bs_cost = self.BackstepCost(wph,Q)
            self.ShortestTransmission[index] = bs_cost + self.taskDelay[index]
            self.taskStatus[index]="HANGING"
        else:
            x=0

    
    def Miracle(self, TaskID, wph:WaypointHistory, Q:TaskQueue):
        index = self.FindTaskByID(TaskID)
        if(self.taskStatus[index]=="NOT-HALTED"):
            bs_cost = self.BackstepCost(wph,Q)
            self.ShortestTransmission[index] = bs_cost + self.taskDelay[index]

        else:
            x=0
      

    def Penalize(self,leadingAction:Task, previousLocation:Position):
        ActionTimeEstimate = self.DelayEstimatorOLD(leadingAction,previousLocation)
        for i, t in enumerate(self.taskID):
            if((self.taskStatus[i]=="HANGING")or(self.taskStatus[i]=="NOT-HALTED")):
                self.taskDelay[i] = self.taskDelay[i] + ActionTimeEstimate
                self.AoI[i] = self.AoI[i] + ActionTimeEstimate
            if(leadingAction.uniqueID==self.taskID[i]):
                if(self.taskStatus[i] == "NOT-HALTED"):
                    x=0
                    # self.ShortestTransmission[i] =  self.taskDelay[i]
                self.taskStatus[i] = "COMPLETE"


            

    def Print(self):
        #print("Number Penalized of Tasks: " + str(self.taskID.__len__()))
        for i, n in enumerate(self.taskID):
            print("Task: " + str(self.taskID[i]))
            print("Status: " + str(self.taskStatus[i]))
            print("Delay: " + str(self.taskDelay[i]))
            print("")


    def CompleteTask(self,taskID):
        if(not (self.FindTaskByID(taskID)==-1)):
            self.taskStatus[self.FindTaskByID(taskID)]="COMPLETE"

    def FindTaskByID(self,id):#naive :(
        index = -1
        for i, t in enumerate(self.taskID):
            if(self.taskID[i]==id):
                index = i
        return index
    
    def GetTotalExecutedTime(self,wd:WatchDog):
        x=0
        actions = wd.GetActionList()
        a:ActionRecord
        previousLocation = wd.GetStartingPosition()
        total =0
        for i,a in enumerate(actions):
            
            start = previousLocation
            end = a.Position
            total = total + self.DelayEstimator(start,end,a.Task)
            previousLocation = end
        return total
    
    def BackstepCost(self,wph_origin:WaypointHistory,Q:TaskQueue):
        x=0
        memo = dict()
        wph:WaypointHistory = wph_origin.__deepcopy__(memo)

        backSteps = wph.BackTrackPathForConnectivity()
        nextTask:Task = Q.NextTask()
        startingPosition =  nextTask.position
        start:Position = startingPosition
        end:Position = startingPosition
        total = 0
        # backSteps.reverse()
        connectionReached = False
        for waypoint in backSteps:

            end = waypoint[0]
            if(waypoint[1]):
                #print("Appending Next Task!")
                total = total + self.DelayEstimator(start,end,"SEND_DATA")
                total = total + self.DelayEstimator(start,end,"FLIGHT")
                connectionReached = True
                break
            else:
                total = total + self.DelayEstimator(start,end,"FLIGHT")
            start = end

        return total
    
    def AnalyzePenalty(self):
        total=0
        for i, t in enumerate(self.taskID):
            
            self.Penalties[i] = self.taskDelay[i]-self.ShortestTransmission[i]     
            total = total + self.Penalties[i]

        return total



        

        



            
    
        

    def DelayEstimatorOLD(self,action:Task, prev:Position):
        speed = 10 #m/s
        if(action.task=="FLIGHT"):
            start:Position = prev
            end:Position = action.position
            geo = Geodesic.WGS84.Inverse(start.lat, start.lon, end.lat,end.lon)
            distance = geo.get('s12')
            return distance/speed
        else:
            return 1.0
    def DelayEstimator(self,start:Position, end:Position,task:str):
        speed = 10 #m/s
        if(task=="FLIGHT"):
            geo = Geodesic.WGS84.Inverse(start.lat, start.lon, end.lat,end.lon)
            distance = geo.get('s12')
            return distance/speed
        else:
            return 1.0
        
    def TotalDelay(self):
        total = 0
        for d in self.taskDelay:
            total = d + total
        return total
    
    def TotalPenalty(self):
        total = 0
        for d in self.Penalties:
            total = d + total
        return total
        
    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result


class TaskPenaltyNormalizer(object):
    def __init__(self,q:TaskQueue):
        self.memo_q = {}
        self.Q = q.__deepcopy__(self.memo_q)
        self.Base:TaskPenaltyTracker = TaskPenaltyTracker(self.Q)
        t:Task = self.Q.PopTask()
        currentPosition = t.position
        prevPosition = t.position
        self.Base.Penalize(t,prevPosition)
        while(not self.Q.Empty()):
            t = self.Q.PopTask()
            self.Base.Penalize(t,prevPosition)
            prevPosition = currentPosition
        print("Penalty Normalizer:")
        self.Base.Print()

    def Normailze(self,PenaltyTracker:TaskPenaltyTracker):
        memo_pt = dict()
        Normalized = PenaltyTracker.__deepcopy__(memo_pt)
        for i, task in enumerate(Normalized.taskDelay):
            x=0
            Normalized.taskDelay[i] = Normalized.taskDelay[i] - self.Base.taskDelay[i]
        return Normalized
            






class RadioMap(object):
    def __init__(self,RadioPosition):
        self.lats = []
        self.lons = []
        self.headings = []
        self.dataRate = []
        self.length = 0
        self.positions =[]
        self.maxDistance = 0
        self.radioPosition = RadioPosition
    def Add(self, lat, lon, heading, rate,alt):
        self.lats.append(lat)
        self.lons.append(lon)
        self.headings.append(heading)
        self.dataRate.append(rate)
        self.length = self.length + 1
        pos = Position()
        pos.InitParams(lon,lat,alt,0,0,0)
        self.positions.append(pos)

        if(rate>0):
            x =0
            geo = Geodesic.WGS84.Inverse(pos.lat, pos.lon, self.radioPosition.lat,self.radioPosition.lon)
            distance_to_radio = geo.get('s12')
            if distance_to_radio>self.maxDistance:
                self.maxDistance = distance_to_radio
            #print("The distance to radio is {:.3f} m.".format(geo['s12']))




    def ConnectionProbabilty(self,currentPosition):
        rMax = self.maxDistance
        geo = Geodesic.WGS84.Inverse(currentPosition.lat, currentPosition.lon, self.radioPosition.lat,self.radioPosition.lon)
        d = geo.get('s12')
        if(d<1.05*rMax):
            return 0.95
        elif(d<1.1*rMax):
            return 0.75
        elif(d<1.2*rMax):
            return 0.50
        elif(d<1.3*rMax):
            return 0.30
        elif(d<1.4*rMax):
            return 0.15
        elif(d<1.5*rMax):
            return 0.03
        else:
            return 0.01



    def FindClosestPointWithConnection(self,nextPoint,currentPosition,radioPosition):
        geo = Geodesic.WGS84.Inverse(currentPosition.lat, currentPosition.lon, radioPosition.lat, radioPosition.lon)
        distance_to_base = geo.get('s12')
        minFlightDistance = distance_to_base
        suggestedPositon = radioPosition

        for idx, position in enumerate(self.positions) :
            if(self.dataRate[idx]>0):

                geo = Geodesic.WGS84.Inverse(currentPosition.lat, currentPosition.lon, position.lat, position.lon)
                distance_to_drone = geo.get('s12')
                if minFlightDistance>distance_to_drone :
                    minFlightDistance = distance_to_drone
                    suggestedPositon = position
            

        return suggestedPositon


class Node(object):#Interdependent PredictiveTree Class, can exist without one, but its hopelessly lost  :(
    def __init__(self,ID_num,q:TaskQueue,task:Task,finish,connected,waypointHistory:WaypointHistory, id_gen:TaskIDGenerator,decisionStack:list,penalty:TaskPenaltyTracker,confidence:float,callingOrigin:str):#this contructor is getting to long.... >:(
        self.q_memo = dict()
        self.id_memo = dict()
        self.wph_memo = dict()
        self.ds_memo = dict()
        self.pt_memo = dict()
        self.Q = q.__deepcopy__(self.q_memo)
        self.ID = ID_num #identifies node
        self.Parent = -1 #  -1 represents orphan status
        self.Children = []
        self.Finish = finish
        self.LeadingTask = task
        self.Position = task.position
        self.TravelHistory:WaypointHistory = waypointHistory.__deepcopy__(self.wph_memo)
        self.ID_GEN = id_gen.__deepcopy__(self.id_memo)
        self.Connected = connected
        self.DecisionStack = copy.deepcopy(decisionStack,self.ds_memo)
        self.PenaltyTracker = penalty.__deepcopy__(self.pt_memo)
        self.Confidence = confidence
        self.CallingOrigin = callingOrigin



        
    def Accept(self,parent):#child node recognizes and catalogs parent
        self.Parent = parent.ID
        if(self.ID ==-1):
            x=0
            #children can't be adopted twice, throw an exception or warning or something


    def Adopt(self,child):
        self.Children.append(child.ID)
        if(self.ID==0):
            x=0
        child.Accept(self)
        #print('adopt!')

    def Print(self):
        print('Node:'+ str(self.ID))
        print('Node Parent:'+ str(self.Parent))
        if(self.Children.__len__()):
            for i, child in enumerate(self.Children):
                print('Child:'+ str(child))
        else:
            print("END OF BRANCH")

        print("Task Penalty ID" + str(self.PenaltyTracker.taskID))
        print("Task Statuses" + str(self.PenaltyTracker.taskStatus))
        print("Confidence: " + str(self.Confidence))


    def ChildrenCount(self):
        return self.Children.count
    
    def GetLastDecision(self):
        x= 0
        if(self.DecisionStack.__len__()>0):
            return None
        else:
            return self.DecisionStack[self.DecisionStack.__len__()]
        
    def PenaltyHalt(self):
        x=0
        nextTask:Task = self.Q.NextTask()
        self.PenaltyTracker.HaltTask(nextTask.uniqueID,self.TravelHistory,self.Q)
    def LeapOfFaithMiracle(self):
        x=0
        nextTask:Task = self.Q.NextTask()
        self.PenaltyTracker.Miracle(nextTask.uniqueID,self.TravelHistory,self.Q)






class TreeStatusHolder(object):
    def __init__(self):
        self.Position = -1
        self.Connected = -1
    
    def Update(self,position:Position,connected:bool):
        self.Position = position
        self.Connected = connected

    def Reset(self):
        self.Position = -1
        self.Position = -1

class TaskHold(object):
    def __init__(self):
        self.Captives = []
        self.Reasons = []
        self.Count = 0


    def HoldTask(self, t):
        self.Captives.append(t)
        self.Reasons.append("CONNECTION")
        self.Count = self.Count + 1

    def ReleaseTask(self):
        self.Reasons.pop()
        self.Count = self.Count - 1
        return self.Captives.pop()

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result

    def __RESET__(self):
        self.Captives = []
        self.Reasons = []
        self.Count = 0

class HaltSolution(object):
    def __init__(self,optionNum,branch,confidence,distance,penaltyTracker, decisions):
        self.OptionNum = optionNum
        self.Branch = branch
        self.Confidence = confidence # ?/100%
        self.TotalDistance = distance # meters
        self.Penalties = penaltyTracker # seconds
        self.DecisionStack = decisions

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, copy.deepcopy(v, memo))
        return result

class HaltSolutionAnalyzer(object):
    def __init__(self, solutions:list):
        x=0
        self.Solutions = solutions
        
    def Recommend(self,priority):
        bestSolution:HaltSolution = self.Solutions[0]
        for sol in self.Solutions:
            if(priority == "DISTANCE"):
                if(sol.TotalDistance<bestSolution.TotalDistance):
                    bestSolution = sol
            if(priority == "CONFIDENCE"):
                if(sol.Confidence>bestSolution.Confidence):
                    bestSolution = sol
            if(priority == "TOTAL_DELAY"):
                if(sol.Penalties.TotalDelay()<bestSolution.Penalties.TotalDelay()):
                    bestSolution = sol
        print("Based on "+ priority + " option #" + str(bestSolution.OptionNum) + "is the optimal solution")
        return bestSolution

        



# class StateContainer(object):
#     def __init__(self,tasks:TaskQueue,history:WaypointHistory,id_gen:TaskIDGenerator):
#         self.CurrentQueue = tasks.__deepcopy__()
#         self.TravelHistory = history.__deepcopy__()
#         self.ID_GEN = id_gen.__deepcopy__()

class PredictiveTree(object):
    def __init__(self,root:Node):
        self.Nodes = []
        self.NodeMap = dict()
        self.Root = root
        self.ID_Gen = IDGenerator()
        self.TasksHeld = TaskHold()
        self.maxDistance = 150 #this should be passed in eventually i.e. Dynamic
        self.Status = TreeStatusHolder()
        self.radio = {}
        self.radio['lat'] = 35.72744
        self.radio['lon'] = -78.69607
        self.RadioPosition = Position()
        self.RadioPosition.InitParams(self.radio['lon'], self.radio['lat'],0,0,0,0)
        self.BranchEnds = list()
        self.BranchNodes = list()
        memo = dict()
        self.UnmodifiedTaskQ = self.Root.Q.__deepcopy__(memo)
        self.Priority = "PENALTY"
        self.Solutions = list()
        self.CurrentWatchdog:WatchDog  = None
        
        self.Root.Parent = -1
        #self.Root.ID = self.ID_Gen.Get()
        r = self.Root
        self.NewNode(r.Q,r.LeadingTask,r.Finish,r.Connected,r.TravelHistory,r.ID_GEN,r.DecisionStack,r.PenaltyTracker,1.0,"START")
        self.Status.Update(r.LeadingTask.position,r.Connected)

    def PrintNodes(self):
        n:Node
        for i, n in enumerate(self.Nodes):
            n.Print()
            print("-------------------")


    #Naive linear search--this is pretty inefficient :(
    def GetNode(self,key):
        x=0

        for i, n in enumerate(self.Nodes):
            if(n.ID == key):
                return n
        





    def NewNode(self,taskQ:TaskQueue,t:Task,finish,connected,prevWaypointHistory:WaypointHistory,id_gen:TaskIDGenerator,ds:list,pt:TaskPenaltyTracker,con:float,calledFrom:str):#deines a new node and adds it to the list of nodes

        memo_id = dict()

        id  =  self.ID_Gen.Get()
        call = calledFrom

        if(id==0):
            x=0

        id_gen_cpy = id_gen.__deepcopy__(memo_id)

        if(t.task=="FLIGHT"):
            prevWaypointHistory.AddPoint(t.position,connected)
        newNode = Node(id,taskQ,t,finish,connected,prevWaypointHistory,id_gen_cpy,ds,pt,con,call)
        self.Nodes.append(newNode)
        self.NodeMap[newNode.ID] = newNode
        
        return newNode

    def ConnectionProbabilty(self,currentPosition):
        rMax = self.maxDistance
        geo = Geodesic.WGS84.Inverse(currentPosition.lat, currentPosition.lon, self.radio['lat'],self.radio['lon'])
        d = geo.get('s12')
        if(d<rMax):
            return 1.00
        elif(d<1.05*rMax):
            return 0.95
        elif(d<1.1*rMax):
            return 0.75
        elif(d<1.2*rMax):
            return 0.50
        elif(d<1.3*rMax):
            return 0.30
        elif(d<1.4*rMax):
            return 0.15
        elif(d<1.5*rMax):
            return 0.03
        else:
            return 0.01

    def PrintTree():#stub for now
        x=0
    def AnalyzeOptions():#stub for now
        x=0
    def GetRoot(self,n:Node):#returns the root of a given node
        if(n.Parent == -1):
            return n
        else:
            return self.GetRoot(self.NodeMap[n.Parent])
        

    def BuildSolutionObject(self):
        now = datetime.now()
        branches = 0
        self.Solutions= list()
        solutionHolder = list()
        solutionConfidences = list()
        solutionDelays = list()
        specificationList = list()
        memo_sol = dict()
        for i, n in enumerate(self.Nodes):
            if(not (n.Children.__len__())):
                branches = branches + 1
                self.BranchEnds.append(n.ID)
                self.BranchNodes.append(n)
        for i, n in enumerate(self.BranchNodes):
            soln = Solution()
            branch = self.GetFullBranch(n)
            # print("Solution# "+str(i))
            # self.PrintBranch(branch)
            d = self.GetBranchDistance(branch)
            c = self.GetBranchConfidence(branch)
            print("Confidence:"+ str(c))
            actionList = self.GetBranchActionList(branch)
            #p_norm = penaltyNormalizer.Normailze(n.PenaltyTracker)
            p_norm:TaskPenaltyTracker = n.PenaltyTracker
            totalPenalty = p_norm.AnalyzePenalty()
            soln.OptionNumber = i
            soln.Confidence = c
            soln.DecisionStack = n.DecisionStack
            soln.HaltTask = None
            soln.Distance =d
            soln.Record = actionList
            soln.Penalty = p_norm
            solutionHolder.append(soln)
            solutionConfidences.append(c)
            solutionDelays.append(p_norm)
            specificationList.append({"DECISION_STACK":n.DecisionStack,"CONFIDENCE_METRIC":c,"TOTAL_Penalty":totalPenalty,"DISTANCE":soln.Distance})

        spec = SpeculativeProduct()
        spec.Priority = self.Priority
        spec.Solutions = solutionHolder
        spec.Confidences = solutionConfidences
        spec.Delays = solutionDelays
        spec.SolutionsCount = spec.Solutions.__len__()
        spec.Specifications = specificationList
        spec.Recommend()
        
        return spec
    
    def PrintBranch(self,branch:list):
        x=0 
        n:Node
        for i, n in enumerate(branch):
                
            print("Node: "+ str(i))    
            tte = n.PenaltyTracker.DelayEstimatorOLD(n.LeadingTask,n.Position) ##This is probably wrong
            print("TimeToExecute: "+ str(tte))    
            print("Leading Task: "+ n.LeadingTask.task)    
            print("Decsion Stack: "+ str(n.DecisionStack))    
            print("------------------------------------")



    def GetBranchActionList(self, branch:list):
        x=0
        actions = list()
        
        n:Node
        if(self.CurrentWatchdog):
            actions.append(self.CurrentWatchdog.GetActionList())



        for i, n in enumerate(branch):
                
                if( i < (branch.__len__()-2 )):
                    pos:Position = branch[i].Position
                    tte = n.PenaltyTracker.DelayEstimatorOLD(n.LeadingTask,n.Position) ##This is probably wrong
                    d = n.DecisionStack 
                    p = n.PenaltyTracker
                    action_temp  = ActionRecord(tte,n.LeadingTask.task,pos,p,d,n.Confidence)
                    action_temp.Caller = n.CallingOrigin
                    actions.append(action_temp)

        return actions

    def Recommend_OBSOLETE(self):
        priority = self.Priority
        bestSolution:HaltSolution = self.Solutions[0]
        for sol in self.Solutions:
            if(priority == "DISTANCE"):
                if(sol.TotalDistance<bestSolution.TotalDistance):
                    bestSolution = sol
            if(priority == "CONFIDENCE"):
                if(sol.Confidence>bestSolution.Confidence):
                    bestSolution = sol
            if(priority == "TOTAL_DELAY"):
                if(sol.Penalties.TotalDelay()<bestSolution.Penalties.TotalDelay()):
                    bestSolution = sol
        print("Based on "+ priority + " option #" + str(bestSolution.OptionNum) + " is the optimal solution")
        return bestSolution  



    def GetBranchDistance(self,branch:list):
        x=0
        distance = 0
        
        for i, n in enumerate(branch):
            if( i < (branch.__len__() -2)):
                start:Position = branch[i].Position
                end:Position = branch[i+1].Position
                geo = Geodesic.WGS84.Inverse(start.lat, start.lon, end.lat,end.lon)
                distance = distance + geo.get('s12')

        return distance

            
    def GetBranchConfidence(self,branch:list):
        confidence = 1.0
        for i, n in enumerate(branch):
                confidence = confidence * n.Confidence
                print("CON: "+str(i)+"---"+str(n.Confidence))
        return confidence*100.0
            

        

    
    def GetFullBranch(self,leaf:Node):
        x=0
        branch = list()
        n:Node = leaf
        while(not (n.Parent ==-1)):
            branch.append(n)
            n = self.NodeMap[n.Parent]
        branch.append(n)
        branch.reverse()
        return branch
    
        
    def BranchDistances(self):
        x=0
        branchFlightDistances = list()
        for n in self.BranchNodes:
            branch = self.GetFullBranch(n)
            d = self.GetBranchDistance(branch)
            print("Distance: "+str(d)+" m")
            branchFlightDistances.append(d)
        return branchFlightDistances
        








    def BackStep(self,node:Node):
        memo_wph = dict()
        memo_q = dict()
        Q = node.Q.__deepcopy__(memo_q)
        #print('Class'+ str(node.TravelHistory.__class__))
        wph:WaypointHistory = node.TravelHistory.__deepcopy__(memo_wph)
        wph_debug:WaypointHistory = node.TravelHistory.__deepcopy__(memo_wph)
        t_debug:Task = Q.Peek()
        
        # Update Q here to return to connection complete task, then return on same path
        # we should return a new node here
        

        backSteps = wph.BackTrackPathForConnectivity()
        taskConversion = []
        nextTask:Task = Q.NextTask()
        backSteps.reverse()
        for idx, waypoint in enumerate(backSteps):
 
            if(waypoint[1]):
                #print("Appending Next Task!")
                # nextTask.ChangePosition(waypoint[0])
                taskConversion.append(nextTask)
            t = Task(waypoint[0],"FLIGHT",0,0,node.ID_GEN.Get())
            t.dynamicTask = True
            #print("TASK ID: "+str(waypoint[2])) 
            taskConversion.append(t)
        

        


        t = Q.PopTask()
        Q.AppendTasks(taskConversion)


        n = self.NewNode(Q,t,False,False,wph,node.ID_GEN,node.DecisionStack,node.PenaltyTracker,1.0,"BACKSTEP")
        n.DecisionStack.append("BLOCK")
        # n.DecisionStack.append("Task: "+str(nextTask.uniqueID)+"~BLOCK")
        #n.PenaltyTracker.AddTask(nextTask.uniqueID)
        return n
        


    def CheckHold(self,Q:TaskQueue):
        if(self.Status.Connected):
            while(Q.TaskLock.Captives):
                Q.ReleaseModifyPos(self.Status.Position)


    def ActionableTask(self,t:Task,connected):#maybe this can be expanded to check battery etc.
        if(t.task == "SEND_DATA"):
            return connected #this means if we have a send task, its actionable I.F.F. we have a connection
        else:
            return True


    def ConnectionThreshold(self,position,threshold):
        probabilty = self.ConnectionProbabilty(position)
        if(probabilty>=threshold):
            self.Status.Connected = True
            return True
        else:
            self.Status.Connected = False
            return False
    

    def Continue(self,nextNode:Node):
        memo_q = dict()
        memo_n = dict()
        Q = nextNode.Q.__deepcopy__(memo_q)
        currentNode:Node = nextNode
        currentPosition = currentNode.LeadingTask.position
        LeadingTask = currentNode.LeadingTask
        
        
        


        while(not Q.Empty()):

            
            self.Status.Update(currentNode.LeadingTask.position,currentNode.Connected)
            previousLeadingTask = LeadingTask
            #t:Task = Q.PopTask()



            #this ~if~ block seems redundant?
            if(self.ActionableTask(Q.Peek(),self.Status.Connected)):
                t:Task = Q.PopTask()
                previousPosition = currentPosition
                currentPosition = t.position
                nextLocationConnected = self.ConnectionThreshold(t.position,1.00)
                finish = Q.Empty()
                if(not finish):
                    probabilty = self.ConnectionProbabilty(Q.Peek().position)#nothing really happens with this here


                self.CheckHold(Q)   

                n = self.NewNode(Q,t,finish,nextLocationConnected,currentNode.TravelHistory,currentNode.ID_GEN,currentNode.DecisionStack,currentNode.PenaltyTracker,1.0,"CONTINUE")
                LeadingTask = t
                n.PenaltyTracker.Penalize(t,previousPosition)
                currentNode.Adopt(n)
                currentNode = n

                # if(t.task=="FLIGHT"):#def ActionSimulator(self) to be called here instead
                #     currentNode.TravelHistory.AddPoint(currentPosition,self.Status.Connected)
            else:
                probabilty = self.ConnectionProbabilty(Q.Peek().position)
                finish = Q.Empty()
                n_P = self.NewNode(Q,LeadingTask,finish,True,currentNode.TravelHistory,currentNode.ID_GEN,currentNode.DecisionStack,currentNode.PenaltyTracker,probabilty,"LOF:PASS")
                #tHIS appear to reveal some issue...both shouldn't have been send_data here...double stack?
                # print("00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
                # print("NT: " + str(Q.NextTask().task))
                # print("LT: " + str(LeadingTask.task))
                # print("00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")
                n_F = self.NewNode(Q,LeadingTask,finish,False,currentNode.TravelHistory,currentNode.ID_GEN,currentNode.DecisionStack,currentNode.PenaltyTracker,1.0-probabilty,"LOF:FAIL")
                n_P.DecisionStack.append("LOF")#Leap of faith! P/F# Lets see how it looks without this...may be create another list of meta-decsions made or something
                n_F.DecisionStack.append("LOF")#Leap of faith! P/F # Lets see how it looks without this...its really not useful for decision making
                currentNode.Adopt(n_P)
                currentNode.Adopt(n_F)
                currentNode = n
                if(probabilty>0.01):
                    n_P.LeapOfFaithMiracle()
                    self.Continue(n_P) #these should be the same except for probabilty
                    self.HaltPoint(n_F)#these should be the same
                break
        return currentNode

    def HaltPoint(self,HaltNode:Node):
        if(not HaltNode):
            HaltNode = self.Nodes[0]
        if(HaltNode.Finish):
            return
        else:
            HaltNode.PenaltyHalt()
            BlockTreeHalt = self.Block(HaltNode)
            #print('BLOCK-ADOPTED')

            self.HaltPoint(BlockTreeHalt)


            HoldTreeHalt = self.Hold(HaltNode)
            #print('HOLD-ADOPTED')

            self.HaltPoint(HoldTreeHalt)



    def Block(self,HaltNode:Node):
        nextNode = self.BackStep(HaltNode)
        HaltNode.Adopt(nextNode)
        return self.Continue(nextNode)

    
    def Hold(self,HaltNode:Node):
        nodesHeld = list()
        memo_q = dict()
        Q:TaskQueue = HaltNode.Q.__deepcopy__(memo_q) #want to return a node with the same Q (just updated)
        nextTask = Q.Peek()
        currentPosition = HaltNode.LeadingTask.position
        connected = self.ConnectionThreshold(currentPosition,1.00)
        self.Status.Update(currentPosition,connected)
        while(not self.ActionableTask(Q.Peek(),connected)):
            nodesHeld.append(Q.Peek())
            Q.HoldTopTask()
        if(not Q.Empty()):


            t:Task = Q.PopTask()
            finish = Q.Empty()#UNSTABLE
            n = self.NewNode(Q,t,finish,False,HaltNode.TravelHistory,HaltNode.ID_GEN,HaltNode.DecisionStack,HaltNode.PenaltyTracker,1.0,"HOLD")
            for n_held in nodesHeld:
                #n.PenaltyTracker.AddTask(n_held.uniqueID)
                n.DecisionStack.append("HOLD")
                # n.DecisionStack.append("Task: "+str(n_held.uniqueID)+"~HOLD")
            HaltNode.Adopt(n)
            return self.Continue(n)
        else:
            x=0
            #This shouldn't happen...throw a warning or something like that...
        

