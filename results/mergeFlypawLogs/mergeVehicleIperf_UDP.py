#!/usr/bin/env python
import sys
import os, subprocess
import pwd
import time
from datetime import datetime
import csv
import json
from argparse import ArgumentParser
import geojson
from geojson import Feature, LineString, FeatureCollection

if __name__=="__main__":
    parser = ArgumentParser(description="Merge Vehicle and IPerf3 Logs")
    
    parser.add_argument("-c", "--iperf_client", metavar="IPERF_CLIENT", type=str, help="Path to the IPERF3 Client Logfile", required=True)
    parser.add_argument("-s", "--iperf_server", metavar="IPERF_SERVER", type=str, help="Path to the IPERF3 Server Logfile", required=True)
    parser.add_argument("-v", "--vehicle", metavar="VEHICLE", type=str, help="Path to the Vehicle Logfile", required=True)
    parser.add_argument("-d", "--outdir", metavar="OUTDIR", type=str, help="Path to output directory", required=True)
    parser.add_argument("-n", "--flightname", metavar="FLIGHTNAME", type=str, help="Name of the flight", required=True)

    args = parser.parse_args()
    outdir = os.path.abspath(args.outdir)

    if not os.path.isdir(args.outdir):
        os.makedirs(outdir)

    flightname = args.flightname
    iperf_client = args.iperf_client
    iperf_server = args.iperf_server
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
    
    with open(iperf_client, newline="", mode='r') as json_file:
        iperfparse = csv.reader(json_file, delimiter='\n')
        for iperfrun in iperfparse:
            iperfjson = json.loads(iperfrun[0])
            if iperfjson['unixsecs'] in timedict:
                #print(timedict[iperfjson['unixsecs']])
                timedict[iperfjson['unixsecs']]['mbps_client'] = iperfjson['mbps']
                timedict[iperfjson['unixsecs']]['jitter_ms_client'] = iperfjson['jitter_ms']
                timedict[iperfjson['unixsecs']]['connection_client'] = iperfjson['connection']
        json_file.close()

    with open(iperf_server, newline="", mode='r') as json_server_file:
        iperfserverparse = csv.reader(json_server_file, delimiter='\n')
        for iperfserverrun in iperfserverparse:
            iperfserverjson = json.loads(iperfserverrun[0])
            if iperfserverjson['unixsecs'] in timedict:
                #print(timedict[iperfjson['unixsecs']])
                timedict[iperfserverjson['unixsecs']]['mbps_server'] = iperfserverjson['mbps']
                timedict[iperfserverjson['unixsecs']]['jitter_ms_server'] = iperfserverjson['jitter_ms']
                timedict[iperfserverjson['unixsecs']]['connection_server'] = iperfserverjson['connection']
        json_file.close()

    waypoints = []
    heights = []
    mbps_client = []
    mbps_server = []
    jitter_ms_client = []
    jitter_ms_server = []
    connection = []
    
    for thistime in timelist:
        #print(timedict[thistime])
        thisWaypoint = (float(timedict[thistime]['lon']), float(timedict[thistime]['lat']))
        waypoints.append(thisWaypoint)
        heights.append(timedict[thistime]['height'])
        if 'mbps_client' in timedict[thistime]:
            if timedict[thistime]['mbps_client'] is not None:
                mbps_client.append(timedict[thistime]['mbps_client'])
            else:
                mbps_client.append(-1)
        else:
            mbps_client.append(-1)

        if 'mbps_server' in timedict[thistime]:
            if timedict[thistime]['mbps_server'] is not None:
                mbps_server.append(timedict[thistime]['mbps_server'])
            else:
                mbps_server.append(-1)
        else:
            mbps_server.append(-1)
        
        if 'jitter_ms_client' in timedict[thistime]:
            if timedict[thistime]['jitter_ms_client'] is not None:
                jitter_ms_client.append(timedict[thistime]['jitter_ms_client'])
            else:
                jitter_ms_client.append(-1)
        else:
            jitter_ms_client.append(-1)

        if 'jitter_ms_server' in timedict[thistime]:
            if timedict[thistime]['jitter_ms_server'] is not None:
                jitter_ms_server.append(timedict[thistime]['jitter_ms_server'])
            else:
                jitter_ms_server.append(-1)
        else:
            jitter_ms_server.append(-1)

        if 'connection' in timedict[thistime]: 
            if timedict[thistime]['connection'] is not None:
                connection.append(timedict[thistime]['connection'])
            else:
                connection.append("No connection was made")
        else:
            connection.append("No connection was made")
            
    thisLS = LineString(coordinates=waypoints)
    theseProps = {}
    theseProps['name'] = args.flightname
    theseProps['heights'] = heights
    theseProps['times'] = timelist
    theseProps['connection'] = connection
    theseProps['mbps_client'] = mbps_client
    theseProps['mbps_server'] = mbps_server
    theseProps['jitter_ms_client'] = jitter_ms_client
    theseProps['jitter_ms_server'] = jitter_ms_server
    theseProps['classification'] = "flightpath"
    thisFeat = Feature(geometry=thisLS, properties=theseProps)
    features = []
    features.append(thisFeat)
    thisFC = FeatureCollection(features)

    dumpFC = geojson.dumps(thisFC, sort_keys=True)
    
    of_name = outdir + "/" + args.flightname + ".geojson"
    of = open(of_name, 'w')
    of.write(dumpFC)
    of.close()
         
            

