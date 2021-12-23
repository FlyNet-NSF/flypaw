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
  output_directory = args.output
  output_file_name = "flypaw_%s.json" % (current_timestring)
  output_file = output_directory + "/" + output_file_name

  basestation_host = args.basestation_host
  basestation_port = args.basestation_port

  while True:
    output_json = {}
    client = iperf3.Client()        
    client.server_hostname = basestation_host
    client.port = basestation_port
    client.duration = 1
    client.json_output = True
    result = client.run()
    err = result.error
    if err is not None:
      output_json['connection'] = err
      output_json['mbps'] = None
      output_json['retransmits'] = None
      output_json['meanrtt'] = None
      thistime = datetime.now()
      unixsecs = datetime.timestamp(thistime)
      output_json['unixsecs'] = int(unixsecs) 
      time.sleep(1)
    else:
      datarate = result.sent_Mbps
      retransmits = result.retransmits
      unixsecs = result.timesecs
      result_json = result.json
      meanrtt = result_json['end']['streams'][0]['sender']['mean_rtt']
      output_json['connection'] = 'ok'
      output_json['mbps'] = datarate
      output_json['retransmits'] = retransmits
      output_json['unixsecs'] = unixsecs
      output_json['meanrtt'] = meanrtt

    result_str = json.dumps(output_json)
    with open(output_file, "a") as ofile:
      ofile.write(result_str + "\n")
      
      ofile.close()
          
    del client

def handleArguments(properties):
  parser = ArgumentParser()
  parser.add_argument("-b", "--basestation-host", dest="basestation_host", default=properties['basestation_host'],
                      type=str, help="The host/IP address for the basestation. Default is in the config file.")
  parser.add_argument("-p", "--basestation-port", dest="basestation_port", default=properties['basestation_port'],
                      type=str, help="The iperf3 server port on the basestation RabbitMQ.  Default is in the config file.")
  parser.add_argument("-o", "--output", dest="output", default=properties['output'],
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
  configProperties = readConfig("/root/flypaw/drone/config.ini")
  args = handleArguments(configProperties)
  main(args)
  #daemonize()

