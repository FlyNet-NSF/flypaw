#!/usr/bin/env python
import sys
import os, subprocess
import pwd
import time
#import requests
#import json, geojson, time, socket, subprocess, certifi, urllib3, geopy
#import geopy.distance
#import xml.etree.ElementTree as ET
import math
from datetime import datetime
import csv
import json
from argparse import ArgumentParser
from geopy.distance import lonlat, distance
#from geographiclib.geodesic import Geodesic
#from geopy import Point

#import datetime
# json, geojson, time, csv


if __name__=="__main__":
    parser = ArgumentParser(description="Merge Vehicle and Power Logs")
    parser.add_argument("-p", "--power", metavar="POWER", type=str, help="Path to the Power Logfile", required=True)
    parser.add_argument("-v", "--vehicle", metavar="VEHICLE", type=str, help="Path to the Vehicle Logfile", required=True)
    parser.add_argument("-d", "--outdir", metavar="OUTDIR", type=str, help="Path to output directory", required=True)
    
    args = parser.parse_args()
    outdir = os.path.abspath(args.outdir)

    if not os.path.isdir(args.outdir):
        os.makedirs(outdir)

    power = args.power
    vehicle = args.vehicle

    timelist = []
    distlist = []
    starttime = None

    #fixed node
    #towerlat = 35.727451
    #towerlon = -78.695974
    #stationary rover
    towerlat = 35.727524
    towerlon = -78.697247
    towerloc = towerlat, towerlon
    #towerheight = 5 # ~5meters
    towerheight = .5 #rover
    
    with open(vehicle, newline="", mode='r') as csv_file:
        csv_parse = csv.reader(csv_file, delimiter=',')
        timedict = {}
        for row in csv_parse:
            lon = float(row[1])
            lat = float(row[2])
            v_loc = lat, lon
            height = float(row[3])
            hdist = distance(towerloc, v_loc).m
            vdist = abs(height - towerheight)
            totaldist = math.sqrt((hdist * hdist) + (vdist * vdist))
            #print(totaldist)
            distlist.append(totaldist)
            timestamp = row[-3]
            thisdt = datetime.fromisoformat(timestamp)
            tstamp = thisdt.timestamp()
            if starttime == None:
                starttime = tstamp
            tdiff = tstamp - starttime
            timelist.append(tdiff)
            #print(tdiff)
            
        csv_file.close()

    powerlist = []
    with open(power, newline="", mode='r') as txt_file:
        powerparse = csv.reader(txt_file, delimiter=' ')
        for powersample in powerparse:
            pymd = powersample[0][1:]
            phms = powersample[1][0:-1]
            ptmstr = pymd + " " + phms
            pdt = datetime.fromisoformat(ptmstr)
            ptstamp = pdt.timestamp()
            powerobj = { "timestamp": ptstamp - starttime, "power": powersample[-1] }
            powerlist.append(powerobj)

        txt_file.close()
    
    of_name = outdir + "/power_distance_scatter.txt"
    with open(of_name, 'w') as of:
        columnstr = "distance,power\n"
        of.write(columnstr)
        for pl in powerlist:
            ts = pl['timestamp']
            if ts < timelist[0]:
                continue
            x = 1
            while x < len(timelist):
                if ts < timelist[x]:
                    diffdistpercent = (ts - timelist[x-1])/(timelist[x] - timelist[x-1])
                    thisdist = (diffdistpercent * (distlist[x] - distlist[x-1])) + distlist[x-1]
                    #print("thisdist: " + str(thisdist))
                    #print("power: " + str(pl['power']))
                    outstr = str(thisdist) + "," + str(pl['power']) + "\n"
                    of.write(outstr)
                    break
                else:
                    x = x + 1
                    
            
        #of.write(dumpFC)
        of.close()
         
            

