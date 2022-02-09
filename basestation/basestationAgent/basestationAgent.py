import socket
import pickle
import json
#from aerpawlib.vehicle import Drone
#import aerpawlib
from datetime import datetime

currentRequests = []
currentRequests.append("iperf") #default
bindIP     = "192.168.116.2"
udpPort   = 20001
chunkSize  = 1024
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPServerSocket.bind((bindIP, udpPort))
print("UDP server up and listening")
while(True):
    msgFromServer = {}
    bytesAddressPair = UDPServerSocket.recvfrom(chunkSize)
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
            currentRequests = []
            currentRequests.append("iperf")
        elif msgType == "instructionRequest":
            msgFromServer['requests'] = currentRequests
        elif msgType == "iperfResults":
            latestBW = clientMessage[msgType]['mbps']
            latestRTT = clientMessage[msgType]['meanrtt']
            #if latestBW > 10000:
            currentRequests = []
            currentRequests.append("videoAnalysis")
            #else:
            #    currentRequests = []
            #    currentRequests.append("flight")
        elif msgType == "videoAnalysis":
            currentRequests = []
            currentRequests.append("flight")
        try: 
            serialMsgFromServer = pickle.dumps(msgFromServer)
            UDPServerSocket.sendto(serialMsgFromServer, address)
        except pickle.PicklingError as pe:
            print ("cannot encode reply msg: " + pe)
    except pickle.UnpicklingError as upe:
        print ("cannot decode message from drone: " + upe)

    
