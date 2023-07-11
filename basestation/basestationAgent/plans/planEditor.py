#   This python script will take a Mission Plan file (.plan) generated from QGC and insert TASK items.
#   It defaults to inserting 'TASK' : 'IPERF' on all mission items. Waypoint entry number are inputed,
#   and it will insert 'TASK' : 'IMAGE_LOCATION_QUICK' on those instead. 
#   The script also changes 'fileType' : 'Plan' to 'TaskQ'
#
#   Todo list:
#       Better handling of files. Prompt for file name to use, could use GUI window
#       Option for other TASK items
#
import json
import os
import tkinter as tk
from tkinter import filedialog
TK_SILENCE_DEPRECATION=1
root = tk.Tk()
root.withdraw()
#open a choose file window
oldFilePath = filedialog.askopenfilename()
file_path_temp = oldFilePath.split('.')
newFilePath = file_path_temp[0] + "_TaskQ.plan"

#oldPlan = "mission_original.plan"
#newPlan = "mission_updated.plan"
# ROOT_DIR = os.path.realpath(os.path.dirname(__file__))
# oldFilePath = os.path.join(ROOT_DIR, oldPlan)
# newFilePath = os.path.join(ROOT_DIR, newPlan)

taskIperf = {"TASK" : "IPERF"}
taskImage = {"TASK" : "IMAGE_LOCATION_QUICK"}

imageTaskLocations = input("Input waypoint numbers to perform image task, space delimited\n")
itl = imageTaskLocations.split(' ')
#exit(0)
oldFile = open(oldFilePath, "r+")

missionFile = json.load(oldFile)
oldFile.close()

missionFile['fileType'] = 'TaskQ_Plan'
mission =  missionFile['mission']
items = mission['items']
index = 0
for item in items:
    if str(index) in itl:
        item.update(taskImage)
    else:
        item.update(taskIperf)
    #print(item)
    index = index + 1

with open(newFilePath, 'w') as newFile:
    json.dump(missionFile, newFile, indent=4)

exit(0)


