
def registerACS(default_waypoints, eventName, acsAddress, acsUsername, acsPassword):
        '''                                                                      
        ACS registration-- The CASA CityWarn Alert Control System interface for situational awareness and flight monitoring  
        '''
        
        print("register in ACS")
        
        lineString = gj.LineString(default_waypoints)
        userProperties = {}
        featureList = []
        userProperties['classification'] = "scheduledFlight";
        eventName = eventName
        currentUnixsecs = datetime.now(tz=pytz.UTC).timestamp()
        laterUnixsecs = currentUnixsecs + 1800  #half an hour from now
        
        currentDT = datetime.fromtimestamp(currentUnixsecs, tz=pytz.UTC)
        laterDT = datetime.fromtimestamp(laterUnixsecs, tz=pytz.UTC)
        startTime = currentDT.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        endTime = laterDT.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        #MRMS_PRECIP here monitors the flight for rainfall rates greater than defined threshold
        feature = gj.Feature(geometry=lineString, properties={"eventName": eventName, "startTime": startTime, "endTime": endTime, "userProperties": userProperties, "products": [{"hazard": "MRMS_PRECIP", "parameters": [{"thresholdUnits": "inph", "comparison": ">=", "distance": 5, "distanceUnits": "miles", "threshold": 0.1}]}]})
        featureList.append(feature)
        fc = gj.FeatureCollection(featureList)
        dumpFC = gj.dumps(fc, sort_keys=True)
        FC_data = {'json': dumpFC}
        flightsubmitresp = requests.post(acsAddress, auth=(acsUsername, acsPassword), data=FC_data)
        registerResp = {}
        registerResp['registrationStatusCode'] = flightsubmitresp.status_code
        print(flightsubmitresp.status_code)
        if flightsubmitresp.status_code == 200:
            registerResp['registration'] = "OK"
            print(json.dumps(registerResp))
            return True
        else:
            print("could not register flight in ACS")
            registerResp['registration'] = "FAILED"
            print(json.dumps(registerResp))
            return False

def updateACS(droneSim, name, acsUpdateURL, acsUsername, acsPassword):
        postData = {}
        postData['type'] = 'Feature'
        
        geometry = {}
        geometry['type'] = 'Point'

        currentLocation = []
        currentLocation.append(droneSim.position.lon)
        currentLocation.append(droneSim.position.lat)
        currentLocation.append(droneSim.position.alt)
        geometry['coordinates'] = currentLocation
        postData['geometry'] = geometry
        
        properties = {}
        #just use the first mission name for now
        properties['eventName'] = name
        properties['locationTimestamp'] = droneSim.position.time
        
        nextWP = {}
        nextWPGeo = {}
        nextWPGeo['type'] = 'Point'

        nextWPGeo['coordinates'] = []
        nextWPGeo['coordinates'].append(droneSim.nextWaypoint[0])
        nextWPGeo['coordinates'].append(droneSim.nextWaypoint[1])
        nextWPGeo['coordinates'].append(droneSim.nextWaypoint[2])
        
        nextWP['geometry'] = nextWPGeo
        nextWP['type'] = 'Feature'
        properties['nextWaypoint'] = nextWP        
        properties['userProperties'] = {}
        properties['userProperties']['heading'] = droneSim.heading
        postData['properties'] = properties
        post_json_data = json.dumps(postData)

        postParameters = {}
        postParameters['json'] = post_json_data
        flightupdateresp = requests.post(acsUpdateURL, auth=(acsUsername, acsPassword), data=postParameters)
        updateResp = {}
        updateResp['registrationStatusCode'] = flightupdateresp.status_code

        if flightupdateresp.status_code == 200:
            updateResp['registration'] = "OK"
        else:
            updateResp['registration'] = "FAILED"
        return updateResp['registration']
