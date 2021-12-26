# flypaw
FlyNet Experiments for the AERPAW Testbed

FlyNet is an NSF funded (Award #: 2018074) CC* Integration project lead by the University of Massachusetts Amherst, in conjunction with the University of Southern California ISI, University of North Carolina at Chapel Hill RENCI, and the University of Missouri.  FlyNet looks to demonstrate deeply programmable, network-centric, edge-to-core workflows with a focus on use cases for the rapidly developing unmanned aviation industry.  We believe that the NSF funded AERPAW testbed is a natural fit, and we hope to utilize the infrastructure that AERPAW makes available to advance our workflows beyond simulation environments into the real world for added significance and realism.

The flypaw repository shall contain tools and libraries that can be used in isolation, or as part of larger end-to-end experiments. Integration codes will largely consist of python3 and shell scripts made available to users, but specific applications for given experiments may be written in C, C++, or java, in some cases with only containers made avaliable from dockerhub.  Individual tools and larger experiment frameworks shall be described below as they are created.


/drone

	#Base directory for software designed to run on the drone
	/planfiles
		#These are .plan files describing flight paths
		/perimeter_30m_80m.plan
			#Two loops near the outskirts of the Lake Wheeler test field, first at 30m, then again in the same track at 80m.

	/trafficGeneration
		#These are tools and scripts used to generate and measure network traffic
		/iperfClientToBasestation
			#Simple python code with iperf3 libraries to continuously send one second bursts of traffic and log results
			#Assumes iperf3 server is running on basestation machine
			#Uses TCP protocol
			#Selected fields logged as JSON... subset of fields to be logged can be added to easily
			#See: https://iperf3-python.readthedocs.io/en/latest/modules.html#client
			/iperfClientToBasestation.py
			#default config file for iperfClientToBasestation.py
			/config.ini

		/scripts
			/startFlypawIperfClient.sh
				#simple shell script to start and stop iperfClientToBasestation within sample AERPAW experiment framework
