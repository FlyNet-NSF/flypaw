#!/usr/bin/python3
import requests
import json
import geojson
import time
import sys
import os
#import pika
import threading
import configparser
import random
from datetime import datetime
from argparse import ArgumentParser
from os import path
#from geopy.distance import lonlat, distance, Distance
#from geopy import Point
#from geographiclib.geodesic import Geodesic
from distutils.util import strtobool

# constants
worker_interface = "tun_srsue"

def readConfig(file):
  config = configparser.ConfigParser()
  config.read(os.path.join(os.path.dirname(__file__), file))
  return config['properties']

def main(args):
  #credentials = pika.PlainCredentials(args.rabbituser, args.rabbitpass)
  #baseconnection = pika.BlockingConnection(pika.ConnectionParameters(host=args.basestation_host, virtual_host=args.basestation_vhost, credentials=credentials))
  #basechannel = baseconnection.channel()
  #basechannel.queue_declare(queue=args.basestation_queue, durable=True)

  vehicle_log = args.vehicle_log
  #print (vehicle_log)
  currentPosition = getCurrentPosition(vehicle_log)
  previousPosition = None
  if currentPosition is not None:
    print (currentPosition)
    previousPosition = currentPosition
  
  #currentLat = currentPosition['lat']
  #currentLon = currentPosition['lon']
  #currentAlt = currentPosition['alt']
  
  
  #endLat = 33.0
  #endLon = -97.2
  #currentTuple = [currentLon, currentLat, currentAlt]
  #endTuple = [endLon, endLat, currentAlt]
  #currentBattery = random.randint(50, 100)
  #currentBattery = 100 
  #endless = 0

  #drone_flights = [] #in case we want more than one
  #archived_updates = []
  #cell_towers = []
  #ground_stations = []
  
  
  #droneData = {}
  #droneData['type'] = "Feature"
  #droneData['properties'] = {}
  #droneData['properties']['eventName'] = "FlyPawDemo"
  #droneData['properties']['classification'] = "proposedFlight"
  #droneData['properties']['userProperties'] = {}
  #droneData['properties']['userProperties']["cost"] = "cost estimate pending"

  #flight_analysis = Geodesic.WGS84.Inverse(currentLat, currentLon, endLat, endLon)
  #flight_bearing = flight_analysis['azi1']
  #flight_distance = flight_analysis['s12']
  #droneData['properties']['userProperties']["distance"] = flight_distance
  #droneData['properties']['userProperties']["flightType"] = 4 #speed
  
  #droneData['properties']['userProperties']['vehicle'] = {}
  #this_vehicle = getVehicleData(1);
  #droneData['properties']['userProperties']['vehicle'] = this_vehicle
  
  #droneData['properties']['userProperties']['celltowers'] = {}
  #droneData['properties']['userProperties']['celltowers']['type'] = "FeatureCollection"
  #droneData['properties']['userProperties']['celltowers']['features']= []
  #droneData['properties']['userProperties']['groundstations'] = {}
  #droneData['properties']['userProperties']['groundstations']['type'] = "FeatureCollection"
  #droneData['properties']['userProperties']['groundstations']['features']= []
  #droneData['properties']['dynamicProperties'] = {}
  #droneData['properties']['dynamicProperties']['altitude'] = 500
  #droneData['properties']['dynamicProperties']['location'] = {}
  #droneData['properties']['dynamicProperties']['location']['type'] = "Point"
  #droneData['properties']['dynamicProperties']['location']['coordinates'] = []
  #droneData['properties']['dynamicProperties']['location']['coordinates'] = currentTuple
  #droneData['properties']['dynamicProperties']['bearing'] = flight_bearing
  #droneData['properties']['dynamicProperties']['archivedUpdates'] = []
  #droneData['geometry'] = {}
  #droneData['geometry']['type'] = "LineString"
  #droneData['geometry']['coordinates'] = []
  #droneData['geometry']['coordinates'].append(currentTuple)
  #droneData['geometry']['coordinates'].append(endTuple)
  
  #while currentBattery > 0:
  #  print("currentBattery: " + str(currentBattery))
    # update drone data
    #droneData['properties']['userProperties']['batterylife'] = currentBattery

    # move drone
    #prevLat = currentLat
    #prevLon = currentLon
    #prevFeat = {}
    #prevFeat['type'] = "Feature"
    #prevFeat['geometry'] = {}
    #prevFeat['geometry']['type'] = "Point"
    #prevFeat['geometry']['coordinates'] = []
    #prevFeat['geometry']['coordinates'].append(prevLon)
    #prevFeat['geometry']['coordinates'].append(prevLat)
    #droneData['properties']['dynamicProperties']['archivedUpdates'].append(prevFeat)
    
    #currentLat = currentLat + .01
    #currentLon = currentLon - .01
    #currentTuple = [currentLon, currentLat, currentAlt]
    #droneData['properties']['dynamicProperties']['location']['coordinates'] = currentTuple
    #droneData['geometry']['coordinates'][0] = currentTuple
    #flight_analysis = Geodesic.WGS84.Inverse(prevLat, prevLon, currentLat, currentLon)
    #flight_bearing = flight_analysis['azi1']
    #droneData['properties']['dynamicProperties']['bearing'] = flight_bearing

    #drone_point = Point(currentLat, currentLon, currentAlt)

    #cell_towers = generateCellTowers(drone_point, cell_towers)  # regenerate cell towers

    #ground_stations = modulateGroundStationsLoad(25, ground_stations) #the integer represents maximum change in load from timeframe to timeframe
    #ground_stations = generateGroundStations(drone_point, ground_stations) #regenerate ground stations
    
    #for tower in cell_towers:
    #  towerDistanceCalc = Geodesic.WGS84.Inverse(currentLat, currentLon, tower['geometry']['coordinates'][1], tower['geometry']['coordinates'][0])
    #  towerDistance = towerDistanceCalc['s12']
    #  tower['properties']['distance'] = towerDistance
    #  signal = 50 + (int(towerDistance / 1000) * 5) + random.randint(0,10) # calculate signal with some randomness (function of distance)... should max out around 110dB
    #  tower['properties']['signal'] = signal 
    #  rtt = int(towerDistance / 2000) + random.randint(0,5)  # calculate RTT with some randomness (factor of distance)
    #  tower['properties']['rtt'] = rtt

    #  if 'bw' not in tower:
    #    bw = 10 * ((50/signal) * (50/signal) * (50/signal)) #if signal is maxed out at 50dB this should yield 10mbps, falling off exponentially
    #    tower['properties']['bandwidth'] = bw

     # for station in ground_stations:
     #   towerToStationDistanceCalc = Geodesic.WGS84.Inverse(station['geometry']['coordinates'][1], station['geometry']['coordinates'][0], tower['geometry']['coordinates'][1], tower['geometry']['coordinates'][0])
      #  towerToStationDistance = towerToStationDistanceCalc['s12']
      #  towerToStationRTT = int(towerToStationDistance / 3000) + random.randint(0,5)
      #  tower['properties']['groundstationRTT'][station['properties']['name']] = towerToStationRTT
      #  tower['properties']['groundstationDistance'][station['properties']['name']] = towerToStationDistance
      #  station['properties']['towerRTT'][tower['properties']['name']] = towerToStationRTT
      #  station['properties']['towerDistance'][tower['properties']['name']] = towerToStationDistance

    #find the closest tower to the drone
    #nearestTowerDistance = 999999999 #huge val
    #nearestCellTower = ""
    #for tower in cell_towers:
    #  if tower['properties']['distance'] < nearestTowerDistance:
    #    nearestTowerDistance = tower['properties']['distance']
    #    nearestCellTower = tower['properties']['name']

    #denote it to the celltower object
    #for tower in cell_towers:
    #  if tower['properties']['name'] == nearestCellTower:
    #    tower['properties']['nearestCellTower'] = "true"
    #  else:
    #    tower['properties']['nearestCellTower'] = "false"

      #denote the closest ground station to the tower
    #  nearestGroundstationDistance = 999999999
    #  nearestGroundstation = ""
    #  for key in tower['properties']['groundstationDistance'].keys():
    #    if tower['properties']['groundstationDistance'][key] < nearestGroundstationDistance:
    #      nearestGroundstationDistance = tower['properties']['groundstationDistance'][key]
    #      nearestGroundstation = key
    #  tower['properties']['nearestGroundStation'] = nearestGroundstation
     
    #droneData['properties']['userProperties']['celltowers']['features'] = cell_towers
    #droneData['properties']['userProperties']['groundstations']['features'] = ground_stations

    #drone_flights = [] #clear out the list of flights for now... ideally we'd just update a flight already existing in the list
    #drone_flights.append(droneData)

    #drones = {}
    #drones['type'] = "FeatureCollection"
    #drones['features'] = []
    #drones['features'] = drone_flights
    
    # battery simulation
    #currentBattery = currentBattery - 1

    #print(droneData)
    #droneMessage = str(droneData, 'utf-8')
    #droneMessage = droneData
    #submitToBasestation(args, basechannel, drones)

  #  time.sleep(20)
  
  print("Flight is complete.  Exiting")
  sys.exit()

#def 
def getCurrentPosition(vehicleLog):
  currentPosition = {}
  with open(vehicleLog, 'rb') as vfile:
    try:
      vfile.seek(-2, os.SEEK_END)
      while vfile.read(1) != b'\n':
        vfile.seek(-2, os.SEEK_CUR)
    except OSError:
      vfile.seek(0)
    vline = vfile.readline().decode()
    vfile.close()
  if vline is not None and vline is not '\n':
    print(vline)
    vlinearr = vline.split(',')
    if len(vlinearr) > 5:
      currentPosition['lat'] = vlinearr[2]
      currentPosition['lon'] = vlinearr[1]
      currentPosition['alt'] = vlinearr[3]
      currentPosition['time'] = vlinearr[5]
      return currentPosition
    else:
      return None
  else:
    return None
  
def generateGroundStations(location, existing = []):
  count = 2
  distance_limit = 10000 #10 km

  # remove out of range stations                                                                                                                                           
  for station in existing:
    drone_station_distance = Geodesic.WGS84.Inverse(location.latitude, location.longitude, station['geometry']['coordinates'][1], station['geometry']['coordinates'][0])['s12']
    if drone_station_distance > distance_limit:
      existing.remove(station)

  # add stations if needed                                                                                                                                                 
  out = existing
  if len(existing) < count:
    for i in range(count - len(existing)):
      rand_distance = distance_limit - random.randint(int(distance_limit/1.1),distance_limit)
      rel_bearing = random.random() * 180 - 90  # calculate a random relative heading between -90 and 90 degrees from the drone
      new_station_dist = distance(kilometers=rand_distance / 1000)
      new_station = new_station_dist.destination(location, rel_bearing)
      longitude = new_station.longitude
      latitude = new_station.latitude
      this_tuple = [longitude, latitude, 0]
      key = "gs_" + str(round(longitude,4)) + "_" + str(round(latitude,4))
      this_station = {}
      this_station['type'] = "Feature"
      this_station['geometry'] = {}
      this_station['geometry']['type'] = "Point"
      this_station['geometry']['coordinates'] = this_tuple
      this_station['properties'] = {}
      this_station['properties']['ipaddress'] = assignIPAddr(existing)
      this_station['properties']['classification'] = "groundstation"
      this_station['properties']['name'] = key
      this_station['properties']['towerRTT'] = {}
      this_station['properties']['towerDistance'] = {}
      this_station['properties']['load'] = random.randint(0, 100);
      out.append(this_station)
  return out

def modulateGroundStationsLoad(maxChange, existing = []):
  for station in existing:
    station['properties']['load'] = station['properties']['load'] + random.randint(maxChange*-1, maxChange)
    if station['properties']['load'] > 100:
      station['properties']['load'] = 100
    elif station['properties']['load'] < 0:
      station['properties']['load'] = 0
  return existing

#def assignIPAddr(existing):
#  eligibleIPs = []
#  usedIPs = []
#  for gstation in existing:
#    usedIPs.append(gstation['properties']['ipaddress'])
    
#  ipAddrFile = "/var/lib/hostkey/public.json" #maybe move to args... main or local
#  ipF = open(ipAddrFile, "r") # Use file to refer to the file object                                                                                                       
#  ipdict = json.load(ipF)
#  ipkeys = ipdict.keys()
#  for key in ipkeys:
#    if "worker" in key:
#      if ipdict[key] not in usedIPs:
#        eligibleIPs.append(ipdict[key])
#  ipAddr = random.choice(eligibleIPs)
#  return ipAddr
  
def getVehicleData(vehicleType):
  thisVehicle = {}
  if vehicleType == 1:
    #FreeFly Alta drone... a surveillance drone
    thisVehicle['weather_tolerances'] = {}
    thisVehicle['weather_tolerances']['max_temperature'] = 45 #deg C                                                
    thisVehicle['weather_tolerances']['min_temperature'] = -20 #deg C                                               
    thisVehicle['weather_tolerances']['wind_tolerance']  = 13 #m/s ~= 25 kts                                        
    thisVehicle['weather_tolerances']['precip_tolerance'] = 0 #normally units should be mm/hr                       
    thisVehicle['vehicle_description'] = "Surveillance Drone"
    thisVehicle['vehicle_model'] = "Freefly Alta Pro"
    thisVehicle['vehicle_type'] = "multirotor"
    thisVehicle['propulsion'] = {}
    thisVehicle['propulsion']['num_props'] = 8
    thisVehicle['propulsion']['piloted'] = 0
    thisVehicle['propulsion']['can_hover'] = 1
    thisVehicle['propulsion']['horizontal_velocity'] = 15 #units m/s                                                
    thisVehicle['power'] = {}
    thisVehicle['power']['battery_mass'] = 0.515 #units kg                                                          
    thisVehicle['power']['primary_power_source'] = "battery"
    thisVehicle['power']['battery_voltage'] = 22.8
    thisVehicle['power']['battery_type'] = "lithium"
    thisVehicle['power']['battery_mAh'] = 4280
    thisVehicle['power']['number_of_batteries'] = 1
    thisVehicle['power']['battery_energy'] = 97.58
    thisVehicle['vehicle_cost'] = 10000 # in USD                                                                    
    thisVehicle['limits'] = {}
    thisVehicle['limits']['max_payload_mass'] = 9.07 #kg                                                            
    thisVehicle['limits']['max_noise'] = 60
    thisVehicle['limits']['max_range'] = 45 #km
    thisVehicle['limits']['max_airspeed'] = 20 #m/s                                                                 
    thisVehicle['dimensions'] = {}
    thisVehicle['dimensions']['drag_coefficient'] = 0.54
    thisVehicle['dimensions']['front_surface'] = 1 #m^3                                                             
    thisVehicle['dimensions']['vehicle_mass'] = 6.17 #kg                                                            
    thisVehicle['dimensions']['width'] = 1.325 #m

  return thisVehicle

def handleArguments(properties):
  parser = ArgumentParser()
  parser.add_argument("-u", "--rabbituser", dest="rabbituser", default=properties['rabbituser'],
                      type=str, help="The username for RabbitMQ.  Default is in the config file.")
  parser.add_argument("-p", "--rabbitpass", dest="rabbitpass", default=properties['rabbitpass'],
                      type=str, help="The password for RabbitMQ.  Default is in the config file.")
  parser.add_argument("-b", "--basestation-host", dest="basestation_host", default=properties['basestation_host'],
                      type=str, help="The host/IP address for the basestation RabbitMQ.  Default is in the config file.")
  parser.add_argument("-v", "--basestation-vhost", dest="basestation_vhost", default=properties['basestation_vhost'],
                      type=str, help="The virtual host for the basestation RabbitMQ.  Default is in the config file.")
  parser.add_argument("-q", "--basestation-queue", dest="basestation_queue", default=properties['basestation_queue'],
                          type=str, help="The basestation RabbitMQ queue name.  Default is in the config file.")
  parser.add_argument("-e", "--basestation-exchange", dest="basestation_exchange", default=properties['basestation_exchange'],
                          type=str, help="The basestation RabbitMQ exchange name.  Default is in the config file.")
  parser.add_argument("-n", "--noisy", dest="noisy", action='store_true',
                      help="Enable noisy output.")
  parser.add_argument("-l", "--vehicle-log", dest="vehicle_log", default=properties['vehicle_log'],
                      type=str, help="The vehicle log file.  Default is in the config file.")
  return parser.parse_args()

def daemonize():
    try:
        pid = os.fork()
    except OSError as e:
        raise Exception("%s [%d]" % (e.strerror, e.errno))

    if (pid == 0):
        os.setsid()
        try:
            pid = os.fork()    # Fork a second child.
        except OSError as e:
            raise Exception("%s [%d]" % (e.strerror, e.errno))
        if (pid == 0):
            os.chdir("/")
            os.umask(0)
        else:
            os._exit(0)
    else:
        os._exit(0)

#def submitToBasestation(args, channel, message):
#  channel.basic_publish(
#    exchange=args.basestation_exchange,
#    routing_key=exchangeRoutingKey,
#    body=json.dumps(message),
#    properties=pika.BasicProperties( delivery_mode = 2 )
#  )
#  return

if __name__ == '__main__':
  # read the config file which is config.ini
  configProperties = readConfig("config.ini")
  exchangeRoutingKey = "#"; #may need to be read out of config
  args = handleArguments(configProperties)
  main(args)
  #daemonize()
  #t = threading.Thread(target=main, args=[args])
  #threads.append(t)
  #t.start()
  #print(threading.currentThread().getName())
