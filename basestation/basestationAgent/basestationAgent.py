import socket
import pickle
import json
import sys
#from aerpawlib.vehicle import Drone
#import aerpawlib
from datetime import datetime

class IperfInfo(object):
    #collection info
    port = 5201
    ipaddr = "192.168.116.2"
    protocol = "tcp"
    priority = 1
    
    #results info
    mbps = -1
    rtt = -1

    #@property
    #define some calculation functions maybe
    #def protocol(self):
        #decide between tcp and udp
        #for now pick tcp
    #    return self.protocol
    #def ipaddr(self):
        #where is the IPerf server?
        #for now, at the basestation
    #    return self.ipaddr
    #def port(self):
        #iperf3 port
    #    return self.port
    #def priority(self):
        #implement priority function
    #    return self.priority
    #def mbps(self):
    #    return self.mbps
    #def rtt(self):
    #    return self.rtt

class sendVideoInfo(object):
    dataformat = "jpgframes"
    ipaddr = "192.168.116.2"
    port = 23000
    priority = 1
    @property
    def dataformat(self):
        #what are you sending?  Send method implied for now.
        #for starters, jpg frames. FFMPEG to follow shortly.
        return self.dataformat
    def ipaddr(self):
        #where is the video server
        #for now, at the basestation
        return self.ipaddr
    def port(self):
        #video port
        return self.port
    def priority(self):
        #implement priority function
        return self.priority

class collectVideoInfo(object):
    dataformat = "jpgframes"
    duration = 5 #units seconds
    quality = 100 #arbitrary unit
    priority = 1
    
    @property
    def dataformat(self):
        #what are you collecting?
        #for starters, jpg frames. FFMPEG to follow shortly.
        return self.dataformat
    def duration(self):
        #how long to collect in seconds
        return self.duration
    def quality(self):
        #video port
        return self.quality
    def priority(self):
        #implement priority function
        return self.priority
    
class FlyPawBasestationAgent(object):
    localIP = "192.168.116.2"
    bindIP = localIP
    udpPort = 20001
    chunkSize = 1024
    iperf3Agent = IperfInfo()
    videoTransferAgent = sendVideoInfo()
    videoCollectionAgent = collectVideoInfo()
    currentRequests = []
    
    #vehicleRequest = vehicleCommands['iperf']    
    #currentRequests.append(vehicleRequest) # iperf as default request for now
    
    def basestationDispatch(self):
        UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPServerSocket.bind((self.bindIP, self.udpPort))
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
                    currentRequests.append(getVehicleCommands(self, 'iperf')) # iperf as default                  
                elif msgType == "instructionRequest":
                    msgFromServer['requests'] = currentRequests
                    currentRequests = []
                elif msgType == "iperfResults":
                    self.iperf3Agent.mbps = clientMessage[msgType]['mbps']
                    self.iperf3Agent.rtt = clientMessage[msgType]['meanrtt']
                    #if latestBW > 10000:
                    #currentRequests = []
                    #vehicleRequest = vehicleCommands['sendVideo']
                    currentRequests.append(getVehicleCommands(self, 'sendVideo'))
                    #else:
                    #    currentRequests = []
                    #    currentRequests.append("flight")                    
                elif msgType == "sendVideo":
                    #currentRequests = []
                    #vehicleRequest = vehicleCommands['flight']
                    currentRequests.append(getVehicleCommands(self, 'flight'))
                try: 
                    serialMsgFromServer = pickle.dumps(msgFromServer)
                    UDPServerSocket.sendto(serialMsgFromServer, address)
                except pickle.PicklingError as pe:
                    print ("cannot encode reply msg: " + pe)
                
            except pickle.UnpicklingError as upe:
                print ("cannot decode message from drone: " + upe)

    
    def getVehicleCommands(self, command):
        commands = {}
        commands['iperf'] = { "command" : "iperf", "protocol": self.iperf3Agent.protocol, "ipaddr": self.iperf3Agent.ipaddr, "port": self.iperf3Agent.port, "priority": self.iperf3Agent.priority }
        commands['sendVideo'] = { "command" : "sendVideo", "dataformat" : self.videoTransferAgent.dataformat, "ipaddr": self.videoTransferAgent.ipaddr, "port": self.videoTransferAgent.port, "priority": videoTransferAgent.priority  }
        commands['collectVideo'] = { "command" : "collectVideo", "dataformat" : self.videoCollectionAgent.dataformat, "duration": videoCollectionAgent.duration, "quality": videoCollectionAgent.quality, "priority": videoCollectionAgent.priority }
        if command in commands:
            return commands[command]
        else:
            return commands

if __name__ == '__main__':
    FlyPawBasestationAgent().basestationDispatch()

