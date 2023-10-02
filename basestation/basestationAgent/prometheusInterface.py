import requests
import json

def configurePrometheusForResources(resources, prometheusAddress="http://127.0.0.1", prometheusPort=9090, prometheusFile="/root/prometheus/targets.json"):
    '''
    configure a running prometheus server to scrape data from the resources you have procured
    '''
    prometheusReloadURL = prometheusAddress + ":" + prometheusPort + "/-/reload"
    prometheus_config_array = []
    prometheus_config_obj = {}
    resource_ip_array = []
    for resource in resources:
        thisResourceInfo = resource.__dict__
        resourceAddresses = thisResourceInfo['resourceAddresses']
        externalIP = resourceAddresses[1][1]
        externalIPandPort = externalIP + ":8095"
        #redundancy check
        if externalIPandPort not in resource_ip_array:
            resource_ip_array.append(externalIPandPort)
            
        prometheus_config_obj['labels'] = {}
        prometheus_config_obj['labels']['job'] = "node"
        prometheus_config_obj['targets'] = resource_ip_array
        prometheus_config_array.append(prometheus_config_obj)
    try:
        with open(prometheusFile, "w") as ofile:
            json.dump(prometheus_config_array,ofile)
            ofile.close()
    except IOError:
        print("could not open prometheus config file")
        return 1
    #tell prometheus to reload config 
    time.sleep(1)
    updateresp = requests.post(prometheusReloadURL, data={})
    if updateresp.status_code == 200:
        print("Prometheus configured and reloaded")
    else:
        print("Prometheus reload failed with status_code: " + str(status_code))
        return 1
    return 0

