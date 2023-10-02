
def configureBasestationProcesses(mission, resources):
    '''
    Define list of tasks to run on the basestation based on mission type here
    '''
    thisMission = mission.__dict__
    if 'missionType' in thisMission:
        missiontype = thisMission['missionType']
        if missiontype == "videography":
            #videography mission uses prometheus... configure and run
            prometheusFail = configurePrometheusForResources(resources)
            if (prometheusFail):
                return 1
        elif missiontype == "bandwidth":
            #could theoretically start iperf server, but punt for now
            return 1
        elif missiontype == "fire":
            #maybe start the udp video frame transfer server?
            #could theoretically start iperf server
            return 1
    return 0

def getMissionLibraries(mission, resources):
    '''
    Define list of libraries to install on each resource here
    Output is a list of lists... aka, one list of libraries to install for each resource
    '''
    thisMission = mission.__dict__
    if 'missionType' in thisMission:
        missiontype = thisMission['missionType']
        missionLibraries = []
        if missiontype == "bandwidth":
            for thisResource in resources: #same libraries for each resource here, but this need not be the case 
                resourceLibraries = []
                resourceLibraries.append("iperf3")
                missionLibraries.append(resourceLibraries)
        elif missiontype == "videography":
            for thisResource in resources: #same libraries for each resource here, but this need not be the case
                resourceLibraries = []
                resourceLibraries.append("iperf3")
                resourceLibraries.append("epel-release")
                resourceLibraries.append("docker")
                missionLibraries.append(resourceLibraries)
        return missionLibraries
    else:
        return None

def getMissionResourcesCommands(mission, resources):
    '''
    define what processes need to be run on each resource in the form of command line commands, after procurement and library installs
    as with above, this does the same thing on all resources... may need to be modified to assign resource roles associated with larger missions
    '''
    
    thisMission = mission.__dict__

    if 'missionType' in thisMission:
        missiontype = thisMission['missionType']
        missionResourcesCommands = [] #one list of commands per resource
        if missiontype == "bandwidth":
            for thisResource in resources:
                thisResourceInfo = thisResource.__dict__
                missionResourceCommands = []
                #open up the ports... maybe there is a more precise way to do this
                missionResourceCommands.append("sudo iptables -P INPUT ACCEPT")
                #run iperf3
                missionResourceCommands.append("iperf3 --server -J -D --logfile /home/cc/iperf3.txt")
                missionResourcesCommands.append(missionResourceCommands)
        elif missiontype == "videography":
            for thisResource in resources:
                thisResourceInfo = thisResource.__dict__
                resourceAddresses = thisResourceInfo['resourceAddresses']
                #generally address 0 is management IP, address 1 external IP...they could be the same
                #resourceAddress is a pair eg. ['external', 'xxx.xxx.xxx.xxx']
                #could cycle through each address and look for external as first part of pair rather than just assume
                externalIP = resourceAddresses[1][1]
                missionResourceCommands = []
                #open up the ports... maybe there is a more precise way to do this
                missionResourceCommands.append("sudo iptables -P INPUT ACCEPT")
                #run iperf3
                missionResourceCommands.append("iperf3 --server -J -D --logfile /home/cc/iperf3.txt")
                #start docker
                missionResourceCommands.append("sudo systemctl start docker")
                #get prometheus node exporter 
                missionResourceCommands.append("wget https://github.com/prometheus/node_exporter/releases/download/v1.0.0-rc.0/node_exporter-1.0.0-rc.0.linux-amd64.tar.gz")
                #untar prometheus node exporter
                missionResourceCommands.append("sudo tar -zxvf node_exporter-1.0.0-rc.0.linux-amd64.tar.gz -C /opt")
                #run prometheus node exporter
                missionResourceCommands.append("nohup /opt/node_exporter-1.0.0-rc.0.linux-amd64/node_exporter --web.listen-address=':8095' > /home/cc/node_exporter.log 2>&1 &")
                #get darknet container
                missionResourceCommands.append("sudo docker pull papajim/detectionmodule")
                #clone coconet github
                missionResourceCommands.append("git clone https://github.com/papajim/pegasus-coconet.git")
                #make directory for incoming images
                missionResourceCommands.append("mkdir /home/cc/dataset");
                #get receive_file_udp to receive image files and run darknet
                missionResourceCommands.append("wget https://emmy8.casa.umass.edu/flypaw/cloud/receive_file_udp/receive_file_udp_send_coconet.py")
                #run receive_file_udp
                missionResourceCommands.append("nohup python3 receive_file_udp_send_coconet.py -o /home/cc/dataset -a '0.0.0.0' -p 8096 -b 4096 > /home/cc/receive_file_udp.log 2>&1 &")

                missionResourcesCommands.append(missionResourceCommands)
                #install ffmpeg... centos 7 requires the repo install... commenting out for now
                #missionResourceCommands.append("sudo yum -y localinstall --nogpgcheck https://download1.rpmfusion.org/free/el/rpmfusion-free-release-7.noarch.rpm")
                #missionResourceCommands.append("sudo yum -y install ffmpeg");
                #missionResourceCommands.append("mkdir /home/cc/ffmpeg");
                #ffmpeg_cmd = "ffmpeg -nostdin -i udp://" + externalIP + ":23000 -c copy -flags +global_header -f segment -segment_time 10 -segment_format_options movflags=+faststart -reset_timestamps 1 /home/cc/ffmpeg/test%d.mp4 > /home/cc/ffmpeg/ffmpeg.log 2>&1 < /dev/null &"
                #ffmpeg_cmd = "ffmpeg -nostdin -i udp://" + externalIP + ":23000 -f mpegts udp://" + externalIP + ":24000"
                #missionResourceCommands.append(ffmpeg_cmd)
                
        return missionResourcesCommands
    else:
        return None

                
def getMissionCompletionCommands(mission, resources):
    thisMission = mission.__dict__
    #stub-- add things to be run at the end of a mission-- log transfer, etc
    if 'missionType' in thisMission:
        missiontype = thisMission['missionType']
        missionCompletionCommands = [] #one list of commands per resource
        if missiontype == "bandwidth":
            for thisResource in resources:
                thisResourceInfo = thisResource.__dict__
                #a list of commands for each resource
                completionCommands = []
                missionCompletionCommands.append(completionCommands)
        elif missiontype == "videography":
            for thisResource in resources:
                thisResourceInfo = thisResource.__dict__
                #a list of commands for each resource
                completionCommands = []
                missionCompletionCommands.append(completionCommands)
        return missionCompletionCommands
