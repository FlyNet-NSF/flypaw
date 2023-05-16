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
    parser.add_argument("-v", "--vehicle", metavar="VEHICLE", type=str, help="Path to the Vehicle Logfile", required=True)
    parser.add_argument("-d", "--outdir", metavar="OUTDIR", type=str, help="Path to output directory", required=True)
    
    args = parser.parse_args()
    outdir = os.path.abspath(args.outdir)

    if not os.path.isdir(args.outdir):
        os.makedirs(outdir)
        
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
    towerheight = 5 # ~5meters
    
    with open(vehicle, newline="", mode='r') as csv_file:
        csv_parse = csv.reader(csv_file, delimiter=',')
        timedict = {}
        for row in csv_parse:
            lon = float(row[1])
            lat = float(row[2])
            v_loc = lat, lon
            height = float(row[3])
            #hdist = distance(towerloc, v_loc).m
            hdist = math.sqrt(((lon-towerlon)*(lon-towerlon)) + ((lat-towerlat) * (lat-towerlat))) * 111319.5
            distlist.append(hdist)
            #vdist = abs(float(height) - towerheight)
            #totaldist = math.sqrt((hdist * hdist) + (vdist * vdist))
            #print(totaldist)
            #distlist.append(totaldist)
            timestamp = row[-3]
            thisdt = datetime.fromisoformat(timestamp)
            tstamp = thisdt.timestamp()
            if starttime == None:
                starttime = tstamp
            tdiff = tstamp - starttime
            timelist.append(tdiff)
            #print(tdiff)
            
        csv_file.close()
    
    of_name = outdir + "/distance_scatter.txt"
    with open(of_name, 'w') as of:
        x = 1
        while x < len(timelist):
            outstr = str(timelist[x]) + "," + str(distlist[x]) + "\n"
            of.write(outstr)
            x = x + 1
            
            
        #of.write(dumpFC)
        of.close()
         
            

