#!/usr/bin/env python
import sys
import os, subprocess
import pwd
#import time
import json, geojson
import math
#from datetime import datetime
from argparse import ArgumentParser
from geopy.distance import lonlat, distance

if __name__=="__main__":
    parser = ArgumentParser(description="Distance/BW scatterplot")
    parser.add_argument("-g", "--gjfile", metavar="INPUT", type=str, help="Path to the geojson input file", required=True)
    parser.add_argument("-d", "--outdir", metavar="OUTDIR", type=str, help="Path to output directory", required=True)
    
    args = parser.parse_args()
    outdir = os.path.abspath(args.outdir)

    if not os.path.isdir(args.outdir):
        os.makedirs(outdir)
        
    gjfile = args.gjfile
    f = open(gjfile)
    geoj = json.load(f)
    feat = geoj['features'][0]
    #fixed node
    towerlat = 35.727451
    towerlon = -78.695974
    towerloc = towerlat, towerlon
    towerheight = 5 # ~5meters

    coordsarr = feat['geometry']['coordinates']
    heightsarr = feat['properties']['heights']
    mbpsarr  = feat['properties']['mbps']
    distlist = []
    mbpslist = []
    
    for idx, coord in enumerate(coordsarr):
        
        c_loc = coord[1], coord[0]
        hdist = distance(towerloc, c_loc).m
        height = heightsarr[idx]
        #don't use the higher measurements
        if height > 35:
            continue
        vdist = abs(height - towerheight) 
        totaldist = math.sqrt((hdist * hdist) + (vdist * vdist))
        #totaldist = hdist
        #print(totaldist)
        #print(height)
        distlist.append(totaldist)
        mbpslist.append(mbpsarr[idx])
    
    of_name = outdir + "/experiment_distance_scatter.txt"
    with open(of_name, 'w') as of:
        for idx, x in enumerate(distlist):
            #outstr = str(distlist[idx]) + "," + str(mbpsarr[idx]) + "\n"
            outstr = str(distlist[idx]) + "," + str(mbpslist[idx]) + "\n"
            of.write(outstr)
        of.close()

