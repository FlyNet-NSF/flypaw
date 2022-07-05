import sys
import os
import time
import socket

from argparse import ArgumentParser

def udpFileSend(filename, address, port, buffersz):
    #buffersz could be 1024 or 4096... not sure the best value 
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
        print("could not create udp socket")
        return 1
    #strip out basename
    basename = os.path.basename(filename)
    try:
        sock.sendto(basename.encode(), (address, port))
    except socket.error:
        print("could not send filename")
        return 1

    try:
        ifile = open(filename, "rb")
    except IOerror:
        print("could not find file: " + filename)
        return 1

    chunk = ifile.read(buffersz)
    while (chunk):
        #if sock.sendto(chunk.encode('utf-16'), (address, port)):
        if sock.sendto(chunk, (address, port)):
            chunk = ifile.read(buffersz)
            time.sleep(0.02)

    sock.close()
    ifile.close()
    return 0

if __name__ == '__main__':
    parser = ArgumentParser(description="File Transfer Client")
    parser.add_argument("-f", "--filename", metavar="FILENAME", type=str, help="location of file to transfer", required=True)
    parser.add_argument("-a", "--address", metavar="ADDRESS", type=str, help="IP address of server", required=True)
    parser.add_argument("-p", "--port", metavar="PORT", type=int, help="Server port", required=True)
    parser.add_argument("-b", "--buffersz", metavar="BUFFERSZ", type=int, help="Buffer size to read", required=True)

    args = parser.parse_args()
    filename = args.filename
    address = args.address
    port = args.port
    buffersz = args.buffersz
    badResult = udpFileSend(filename, address, port, buffersz)
    if badResult:
        print("transfer failed")
    else:
        print("transfer succeeded")
