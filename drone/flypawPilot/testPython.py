from __future__ import annotations
from dataclasses import dataclass, field

from ast import Str
from turtle import position
import json
import jsonpickle
import json
import copy
from geographiclib.geodesic import Geodesic
import importlib
import os
import sys

thisFileDir = os.path.realpath(os.path.dirname(__file__))
flypawRootDir = os.path.realpath(os.path.join(thisFileDir , '..', '..'))
flypawClassDir = os.path.realpath(os.path.join(flypawRootDir, 'basestation','basestationAgent'))

#Append the directory that contains the flypawClass.py file
sys.path.append(flypawClassDir)


from flypawClasses import *




dump_q_path = os.path.realpath(os.path.join(flypawRootDir, 'drone','flypawPilot','json_dump_q.txt'))
with open(dump_q_path,'r') as f:
    tq = jsonpickle.decode(f.read())
    tq.TaskLock.__RESET__()

dump_wph_path = os.path.realpath(os.path.join(flypawRootDir, 'drone','flypawPilot','json_dump_wph.txt'))
with open(dump_wph_path,'r') as f:
    wph:WaypointHistory = jsonpickle.decode(f.read())

dump_t_path = os.path.realpath(os.path.join(flypawRootDir, 'drone','flypawPilot','json_dump_t.txt'))
with open(dump_t_path,'r') as f:
    t = jsonpickle.decode(f.read())

dump_id_path = os.path.realpath(os.path.join(flypawRootDir, 'drone','flypawPilot','json_dump_id.txt'))
with open(dump_id_path,'r') as f:
    id:TaskIDGenerator = jsonpickle.decode(f.read())

dump_id_path = os.path.realpath(os.path.join(flypawRootDir, 'drone','flypawPilot','dump_watchdog.json'))
with open(dump_id_path,'r') as f:
    wd:WatchDog = jsonpickle.decode(f.read())

t = tq.NextTask()
wd.DumpReport()
pt = TaskPenaltyTracker(tq,wd,wph)
# pt.AnalyzeTaskCost(wph,tq)
emptyList = list()
root:Node =  Node(0,tq,t,0,0,wph,id,emptyList,pt,1.0,"TEST_PYTHON")
tree:PredictiveTree = PredictiveTree(root)
tree.HaltPoint(False)
tree.PrintNodes()
exper = ExperimentResults()
tree.CurrentWatchdog = wd
a  = tree.BuildSolutionObject()
recommendedSolution:Solution = a.GetRecommendation()
executionRec = wd.GetActionList()
exper.SpeculativeSolutionSets.append(a)
exper.ExecutionRecord = executionRec
JSON_DUMP_TASK = jsonpickle.encode(exper,unpicklable=False,indent=True)

with open('experimentDebug.json','w') as f:
    f.write(JSON_DUMP_TASK)




