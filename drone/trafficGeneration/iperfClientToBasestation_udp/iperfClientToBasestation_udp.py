#!/usr/bin/python3
import sys
import os
import configparser
import socket
import iperf3
import json
import time
from datetime import datetime
from argparse import ArgumentParser

def readConfig(file):
  config = configparser.ConfigParser()
  config.read(os.path.join(os.path.dirname(__file__), file))
  return config['properties']

def main(args):

  now = datetime.now()
  current_timestring = now.strftime("%Y%m%d-%H%M%S")
  output_directory = args.output_directory
  output_file_name = "iperf3_udpclient_%s.json" % (current_timestring)
  output_file = output_directory + "/" + output_file_name

  basestation_host = args.basestation_host
  basestation_port = args.basestation_port

  if basestation_host is None or basestation_port is None:
    print("Please declare config file and/or provide command line arguments properly")
    sys.exit()
  
  while True:
    output_json = {}
    client = iperf3.Client()        
    client.server_hostname = basestation_host
    client.port = basestation_port
    client.duration = 1
    client.protocol = 'udp'
    client.bandwidth = 10000000
    client.json_output = True
    result = client.run()
    err = result.error
    if err is not None:
      output_json['connection'] = err
      output_json['mbps'] = None
      thistime = datetime.now()
      unixsecs = datetime.timestamp(thistime)
      output_json['unixsecs'] = int(unixsecs)
      output_json['jitter_ms'] = None
      time.sleep(1)
    else:
      output_json['connection'] = 'ok'
      thistime = datetime.now()
      unixsecs = datetime.timestamp(thistime)
      output_json['unixsecs'] = unixsecs
      output_json['mbps'] = result.json['intervals'][0]['sum']['bits_per_second']
      output_json['jitter_ms'] = result.json['end']['sum']['jitter_ms']
      #time.sleep(3)
    del client
      
    result_str = json.dumps(output_json)
    with open(output_file, "a") as ofile:
      ofile.write(result_str + "\n")     
      ofile.close()
      
    
def handleArguments(properties):
  parser = ArgumentParser()
  parser.add_argument("-b", "--basestation-host", dest="basestation_host", default=properties['basestation_host'],
                      type=str, help="The host/IP address for the basestation. Default is in the config file.")
  parser.add_argument("-p", "--basestation-port", dest="basestation_port", default=properties['basestation_port'],
                      type=str, help="The iperf3 server port on the basestation.  Default is in the config file.")
  parser.add_argument("-o", "--output-directory", dest="output_directory", default=properties['output_directory'],
                      type=str, help="output directory path for json output")
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

if __name__ == '__main__':
  # read the config file which is config.ini
  configProperties = readConfig("./config.ini")
  args = handleArguments(configProperties)
  main(args)
  #daemonize()

