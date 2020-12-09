import requests
import json
import sys
import os
import ipinfo
import jsonpickle

def sendRequest(constellationSelect, requestHandlerHost):
    returnVal = None
    url = "http://" + requestHandlerHost + "/constellationRequest/"
    print(url)
    handler = ipinfo.getHandler()
    userDetails = handler.getDetails()
    lat = "%s N" %userDetails.latitude
    longitude = "%s W"%userDetails.longitude
    coordinatesSelect = [lat, longitude]

    headers = {'content-type': 'application/json'}
    # send http request with image and receive response
    data = jsonpickle.encode({ "constellation" : constellationSelect,
                                "coordinates" : coordinatesSelect})
    response = requests.post(url, data=data, headers=headers)

    if response.status_code == 200:
        test = json.loads(response.text)
        if test:
            print("There are currently", test["satellite_count"], "satellites of the", constellationSelect, "constellation above the location", coordinatesSelect[0], coordinatesSelect[1])
            print("Overhead Satellites:")
            for satellite in test['satellites']:
                print(satellite)

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 requestClient.py [constellation] [serviceHost]")
        exit()

    sendRequest(sys.argv[1], sys.argv[2])

if __name__ == "__main__":
    main()