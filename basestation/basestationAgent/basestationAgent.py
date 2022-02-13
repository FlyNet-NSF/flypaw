import socket
import pickle
import json
import sys
#from aerpawlib.vehicle import Drone
#import aerpawlib
from datetime import datetime

class collectVideoInfo(object):
    def __init__(self, dataformat="jpgframes", duration=5, quality=100, priority = 1):
        self.dataformat = dataformat
        self.duration = duration #units seconds
        self.quality = quality #arbitrary unit
        self.priority = priority
    
    #@property
    #def dataformat(self):
        #what are you collecting?
        #for starters, jpg frames. FFMPEG to follow shortly.
    #    return self.dataformat
    #def duration(self):
        #how long to collect in seconds
    #    return self.duration
    #def quality(self):
        #video port
    #    return self.quality
    #def priority(self):
        #implement priority function
    #    return self.priority
    
class FlyPawBasestationAgent(object):
    def __init__(self, ipaddr="192.168.116.2", port=20001, chunkSize=1024) :
        self.ipaddr = ipaddr
        self.port = port
        self.chunkSize = chunkSize
        self.iperf3Agent = IperfInfo()
        self.videoTransferAgent = sendVideoInfo()
        self.videoCollectionAgent = collectVideoInfo()
        self.currentRequests = []
        self.vehicleCommands = VehicleCommands()
        
    def basestationDispatch(self):
        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPServerSocket.bind((self.ipaddr, self.port))
        print("UDP server up and listening")

        while(True):
            msgFromServer = {}
            bytesAddressPair = UDPServerSocket.recvfrom(self.chunkSize)
            serialClientMessage = bytesAddressPair[0]
            address = bytesAddressPair[1]
            try:
                clientMessage = pickle.loads(serialClientMessage)    
                print(clientMessage['type'])
        
                recvdMsg = "Message from Drone:{}".format(clientMessage)
                clientIP  = "Drone IP Address:{}".format(address)
                print(recvdMsg)
                print(clientIP)
                recvTime = datetime.now().astimezone().isoformat()
                msgFromServer['time_received'] = recvTime
                recvUUID = clientMessage['uuid']
                msgFromServer['uuid_received'] = recvUUID
                msgType = clientMessage['type']
                msgFromServer['type_received'] = msgType
                if msgType == "telemetry":
                    #do something with telemetry
                    #currentRequests = []
                    self.currentRequests.append(self.vehicleCommands['commands']['iperf']) # iperf as default                  
                elif msgType == "instructionRequest":
                    msgFromServer['requests'] = self.currentRequests
                    self.currentRequests = []
                elif msgType == "iperfResults":
                    self.iperf3Agent.mbps = clientMessage[msgType]['mbps']
                    self.iperf3Agent.rtt = clientMessage[msgType]['meanrtt']
                    #if latestBW > 10000:
                    self.currentRequests.append(self.vehicleCommands['commands']['sendVideo'])
                    #else:
                    #    self.currentRequests.append(self.vehicleCommands['commands']['flight'])                    
                elif msgType == "sendVideo":
                    self.currentRequests.append(self.vehicleCommands['commands']['flight'])
                try: 
                    serialMsgFromServer = pickle.dumps(msgFromServer)
                    UDPServerSocket.sendto(serialMsgFromServer, address)
                except pickle.PicklingError as pe:
                    print ("cannot encode reply msg: " + pe)
                
            except pickle.UnpicklingError as upe:
                print ("cannot decode message from drone: " + upe)

    class IperfInfo(object):
        def __init__(self, ipaddr="192.168.126.2", port=5201, protocol="tcp", priority=0, mbps=-1, rtt=-1):
            #collection info
            self.port = port
            self.ipaddr = ipaddr
            self.protocol = protocol
            self.priority = 1
            
            #results/current knowledge 
            self.mbps = mbps
            self.rtt = rtt
    
    class sendVideoInfo(object):
        def __init__(self, dataformat="jpgframes", ipaddr="192.168.126.2", port="23000", priority=1):
            self.dataformat = dataformat
            self.ipaddr = ipaddr
            self.port = port
            self.priority = priority

    class collectVideoInfo(object):
        def __init__(self, dataformat="jpgframes", duration=5, quality=100, priority = 1):
            self.dataformat = dataformat
            self.duration = duration #units seconds
            self.quality = quality #arbitrary for now
            self.priority = priority
    
    class VehicleCommands(object):
        def __init__(self):
            self.commands = {}
            self.commands['iperf'] = { "command" : "iperf", "protocol": self.iperf3Agent.protocol, "ipaddr": self.iperf3Agent.ipaddr, "port": self.iperf3Agent.port, "priority": self.iperf3Agent.priority }
            self.commands['sendVideo'] = { "command" : "sendVideo", "dataformat" : self.videoTransferAgent.dataformat, "ipaddr": self.videoTransferAgent.ipaddr, "port": self.videoTransferAgent.port, "priority": videoTransferAgent.priority  }
            self.commands['collectVideo'] = { "command" : "collectVideo", "dataformat" : self.videoCollectionAgent.dataformat, "duration": videoCollectionAgent.duration, "quality": videoCollectionAgent.quality, "priority": videoCollectionAgent.priority }
        
if __name__ == '__main__':
    FPBA = FlyPawBasestationAgent()
    FPBA.basestationDispatch()

