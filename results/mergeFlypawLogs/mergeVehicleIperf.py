#!/usr/bin/env python
import sys
import os, subprocess
import pwd
import time
#import requests
#import json, geojson, time, socket, subprocess, certifi, urllib3, geopy
#import geopy.distance
#import xml.etree.ElementTree as ET
from datetime import datetime
import csv
import json
from argparse import ArgumentParser
#from geopy import Point

#import datetime
# json, geojson, time, csv
import geojson
from geojson import Feature, LineString, FeatureCollection

if __name__=="__main__":
    parser = ArgumentParser(description="Merge Vehicle and IPerf3 Logs")
    parser.add_argument("-p", "--iperf", metavar="IPERF", type=str, help="Path to the IPERF3 Logfile", required=True)
    parser.add_argument("-v", "--vehicle", metavar="VEHICLE", type=str, help="Path to the Vehicle Logfile", required=True)
    parser.add_argument("-d", "--outdir", metavar="OUTDIR", type=str, help="Path to output directory", required=True)
    parser.add_argument("-n", "--flightname", metavar="FLIGHTNAME", type=str, help="Name of the flight", required=True)

    args = parser.parse_args()
    outdir = os.path.abspath(args.outdir)

    if not os.path.isdir(args.outdir):
        os.makedirs(outdir)

    flightname = args.flightname
    iperf = args.iperf
    vehicle = args.vehicle

    timelist = []
    
    with open(vehicle, newline="", mode='r') as csv_file:
        csv_parse = csv.reader(csv_file, delimiter=',')
        timedict = {}
        for row in csv_parse:
            lon = row[1]
            lat = row[2]
            height = row[3]
            timestamp = row[5]
            dtspl = timestamp.split('.', 1)
            thisdt = datetime.fromisoformat(dtspl[0])
            unixtime = int(thisdt.timestamp())
            timedict[unixtime] = {'lat': lat, 'lon': lon, 'height': height}
            timelist.append(unixtime)

        csv_file.close()
    
    with open(iperf, newline="", mode='r') as json_file:
        iperfparse = csv.reader(json_file, delimiter='\n')
        for iperfrun in iperfparse:
            iperfjson = json.loads(iperfrun[0])
            if iperfjson['unixsecs'] in timedict:
                #print(timedict[iperfjson['unixsecs']])
                timedict[iperfjson['unixsecs']]['mbps'] = iperfjson['mbps']
                timedict[iperfjson['unixsecs']]['retransmits'] = iperfjson['retransmits']
                timedict[iperfjson['unixsecs']]['connection'] = iperfjson['connection']
                timedict[iperfjson['unixsecs']]['meanrtt'] = iperfjson['meanrtt']
        json_file.close()

    waypoints = []
    heights = []
    mbps = []
    connection = []
    retransmits = []
    meanrtt = []
    
    for thistime in timelist:
        print(timedict[thistime])
        thisWaypoint = (float(timedict[thistime]['lon']), float(timedict[thistime]['lat']))
        waypoints.append(thisWaypoint)
        heights.append(timedict[thistime]['height'])
        if 'mbps' in timedict[thistime]:
            if timedict[thistime]['mbps'] is not None:
                mbps.append(timedict[thistime]['mbps'])
            else:
                mbps.append(-1)
        else:
            mbps.append(-1)

        if 'retransmits' in timedict[thistime]:
            if timedict[thistime]['retransmits'] is not None:
                retransmits.append(timedict[thistime]['retransmits'])
            else:
                retransmits.append(-1)
        else:
            retransmits.append(-1)

        if 'meanrtt' in timedict[thistime]:
            if timedict[thistime]['meanrtt'] is not None:
                meanrtt.append(timedict[thistime]['meanrtt'])
            else:
                meanrtt.append(-1)
        else:
            meanrtt.append(-1)

        if 'connection' in timedict[thistime]: 
            if timedict[thistime]['connection'] is not None:
                connection.append(timedict[thistime]['connection'])
            else:
                connection.append("No connection was made")
        else:
            connection.append("No connection was made")
            
    thisLS = LineString(coordinates=waypoints)
    theseProps = {}
    theseProps['heights'] = heights
    theseProps['times'] = timelist
    theseProps['connection'] = connection
    theseProps['meanrtt'] = meanrtt
    theseProps['mbps'] = mbps
    theseProps['classification'] = "flightpath"
    thisFeat = Feature(geometry=thisLS, properties=theseProps)
    features = []
    features.append(thisFeat)
    thisFC = FeatureCollection(features)

    dumpFC = geojson.dumps(thisFC, sort_keys=True)
    
    of_name = outdir + "/AERPAW.geojson"
    of = open(of_name, 'w')
    of.write(dumpFC)
    of.close()
         
            

