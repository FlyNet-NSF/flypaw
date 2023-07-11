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
    parser.add_argument("-p", "--iperf", metavar="IPERF", type=str, help="Path to the IPERF3 json Logfile", required=True)
    parser.add_argument("-o", "--outfilename", metavar="OUTPUT", type=str, help="the output geojson filename (not the full path)", required=True)
    parser.add_argument("-d", "--outdir", metavar="OUTDIR", type=str, help="Path to output directory", required=True)
    parser.add_argument("-n", "--flightname", metavar="FLIGHTNAME", type=str, help="Name of the flight", required=True)

    args = parser.parse_args()
    outdir = os.path.abspath(args.outdir)

    if not os.path.isdir(args.outdir):
        os.makedirs(outdir)

    flightname = args.flightname
    iperf = args.iperf
    outfilename = args.outfilename

    llarr = []
    height = []
    bw = []
    retrans = []
    rtt = []
    time = []
    connection = []
        
    with open(iperf, newline="", mode='r') as json_file:
        for iperfrun in json_file:
            iperfjson = json.loads(iperfrun)
            results = iperfjson['iperfResults']
            location4d = results['location4d']
            llcouplet = [] # lon, lat per geojson standard
            llcouplet.append(float(location4d[1]))
            llcouplet.append(float(location4d[0]))
            llarr.append(llcouplet)
            height.append(location4d[2])
            time.append(location4d[3])
            connection.append(results['connection'])
            bw.append(results['mbps'])
            retrans.append(results['retransmits'])
            rtt.append(results['meanrtt'])
        json_file.close()

            
    thisLS = LineString(coordinates=llarr)
    theseProps = {}
    theseProps['name'] = flightname
    theseProps['heights'] = height
    theseProps['times'] = time
    theseProps['connection'] = connection
    theseProps['meanrtt'] = rtt
    theseProps['mbps'] = bw
    theseProps['classification'] = "flightpath"
    thisFeat = Feature(geometry=thisLS, properties=theseProps)
    features = []
    features.append(thisFeat)
    thisFC = FeatureCollection(features)

    dumpFC = geojson.dumps(thisFC, sort_keys=True)
    
    of_name = outdir + "/" + outfilename
    of = open(of_name, 'w')
    of.write(dumpFC)
    of.close()
         
            

