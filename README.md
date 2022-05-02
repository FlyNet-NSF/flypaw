
# flypaw
FlyNet Experiments for the AERPAW Testbed

FlyNet is an NSF funded (Award #: 2018074) CC* Integration project lead by the University of Massachusetts Amherst, in conjunction with the University of Southern California ISI, University of North Carolina at Chapel Hill RENCI, and the University of Missouri.  FlyNet looks to demonstrate deeply programmable, network-centric, edge-to-core workflows with a focus on use cases for the rapidly developing unmanned aviation industry.  We believe that the NSF funded AERPAW testbed is a natural fit, and we hope to utilize the infrastructure that AERPAW makes available to advance our workflows beyond simulation environments into the real world for added significance and realism.

The flypaw repository shall contain tools and libraries that can be used in isolation, or as part of larger end-to-end experiments. Integration codes will largely consist of python3 and shell scripts made available to users, but specific applications for given experiments may be written in C, C++, or java, in some cases with only containers made avaliable from dockerhub.  Individual tools and larger experiment frameworks shall be described below as they are created.

A flowchart illustrating the proposed multi-tiered architecture with some example mission objectives.  Some of this has been implemented already, some of it is placeholders.  Consider how your experiment might fit similarly!

![flypaw_architecture](https://user-images.githubusercontent.com/30157582/166251625-3c03cbe1-c2c1-4b4f-a48d-49d8bf37e731.png)

CURRENT REPOSITORY STRUCTURE

/basestation

	#Base directory for software designed to run on the basestation
	/basestation_agent
		#Communications hub, mission relay, cloud and edge resource acquisition, network bridge.  
		#Locate lightweight but essential computing tasks here.... works hand in hand with flypawPilot.
		/basestation_agent.py
			#udp based comms server, relays flight plan to drone preflight, currently implementing cloud resource allocation preflight
		/plans
			#several planfiles... of note... 
			/aerpaw_waypoint.plan
				#a simple plan nearby but too close to the boundary... Saved because it was the first test of the flypawPilot
			/aerpaw_waypoint_videoExp.plan
				#current waypoint to waypoint plan for a simulated video mission.  Away from the boundary
	/experiment_install_scripts
		#Helper script to install libraries and copy runtime code onto new emulator instance or when transitioned to the field for real flights
		/bandwidth.sh
			#simple script to install scripts for bandwidth testing... could be extended easily for other mission types
	
	/experiment_run_scripts
		#Helper scripts to run code, including via screen in the background. Adheres to tutorial standards for running things.
		/bandwidth
			#scripts for the bandwidth measuring experiments with srsRAN
				/startBandwidthExperiment.sh
					#the master start script
				/startBasestationAgent.sh
					#runs basestationAgent via screen
				/startIperf3Server_tcp.sh
					#runs a tcp based command line tool iperf server to receive drone client measurements
				/startIperf3Server_udp.sh
					#runs a udp based python wrapped iperf server to receive drone client measurements
	
	/iperfServer_UDP
		#a python based iperfServer using UDP generating JSON formatted output
		/config.ini
			#config file for iperfServer_udp.py
		/iperfServer_udp.py
			
/drone

	#Base directory for software designed to run on the drone
        /experiment_install_scripts
		#Helper script to install libraries and copy runtime code onto new emulator instance or when transitioned to the field for real flights
		/bandwidth.sh
			#simple script to install scripts for bandwidth testing... could be extended easily for other mission types
	
	/experiment_run_scripts
		#Helper scripts to run code, including via screen in the background. Adheres to tutorial standards for running things.
		/bandwidth
			#scripts for the bandwidth measuring experiments with srsRAN
				/flypawPilot.sh
					#the flypawPilot executable
				/startBandwidthExperiment.sh
					#the master start script
				/startFlypawPilot.sh
					#runs flypawPilot.sh via screen
	/flypawPilot
		#The main drone localized command and control.  State framework using aerpawlib/dronekit.  Works in conjunction with basestationAgent
		#receives and executes missions, issues flight commands, numerous safety checks... this is where the smarts of the vehicle exist
		/flypawPilot.py
			#designed to be mission neutral, but current instantiation cannot be said to have achieved that.  Clone/update this code.
	
        /planfiles
		#These are .plan files describing flight paths.  Useful for the autopilot script.
		#flypawPilot shall get its plan during preflight state from the basestation agent
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
		/iperfClientToBasestation_udp
			#same as above but using UDP protocol and fields
			/iperfClientToBasestation_udp.py
			/config.ini
				#config file for udp client  
		/scripts
			/startIperfClient.sh
				#simple shell script to start and stop iperfClientToBasestation within sample AERPAW experiment framework
	
