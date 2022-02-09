import socket
import pickle
#from aerpawlib.vehicle import Drone
#import aerpawlib
from datetime import datetime

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
    clientMessage = pickle.loads( serialClientMessage)    
    clientMsg = "Message from Client:{}".format(clientMessage)
    clientIP  = "Client IP Address:{}".format(address)
    print(clientMsg)
    print(clientIP)

    recvTime = datetime.now().astimezone().isoformat()
    msgFromServer['time_received'] = recvTime
    serialMsgFromServer = pickle.dumps(msgFromServer)
    UDPServerSocket.sendto(serialMsgFromServer, address)
