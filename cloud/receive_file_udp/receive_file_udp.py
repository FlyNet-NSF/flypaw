import socket
import select
import subprocess

outputDir = "/home/cc/dataset"
bindIP = "0.0.0.0"
bindPort = 8096

try:
    udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error:
    print("socket error: Could not create udpsocket")
    sys.exit()

try:
    udpsocket.bind((bindIP, bindPort))
except socket.error:
    print("socket error: Could not bind to port " + str(bindPort))
    sys.exit()
    
while True:
    batch, client = udpsocket.recvfrom(1024)
    if batch:
        fname = outputDir + "/" + batch.strip()

    try:
        ofile = open(fname, 'wb')
    except IOerror:
        print ("could not open file: " + fname)

    while True:
        done = select.select([udpsocket], [], [], 5)
        if done[0]:
            batch, client = sock.recvfrom(1024)
            ofile.write(batch)
        else:
            ofile.close()
            mountStr = outputDir + ":/coconet/dataset"
            try:
                with open("/home/cc/darknet.log", "a") as darknetlog:
                    subprocess.call(['sudo', 'docker', 'run', '-it', '-v', mountStr, 'papajim/detectionmodule:latest', '/coconet/darknet', 'detect', 'cfg/yolov3.cfg', 'yolov3.weights', fname], shell=True, stdout=darknetlog, stderr=darknetlog)
            except IOerror:
                print("could not open darknet log and run darknet.  Skipped.")
            break

        
