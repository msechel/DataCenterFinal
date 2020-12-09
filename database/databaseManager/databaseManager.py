import sys
import json
import os
import requests
import pika
import redis
import jsonpickle
from datetime import datetime,timezone,timedelta
from skyfield.api import EarthSatellite, Topos, load

##
## Configure test vs. production
##
redisHost = os.getenv("REDIS_HOST") or "localhost"
rabbitMQHost = os.getenv("RABBITMQ_HOST") or "localhost"
requestRedisIDHost = os.getenv("REQUEST_REDIS_HOST") or "localhost"

print("Connecting to rabbitmq({}) and redis({})".format(rabbitMQHost,redisHost))

connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitMQHost))
channel = connection.channel()
channel.queue_declare(queue='databaseManagerRequests')

satellites = []

ts = load.timescale()

def getRedis(addr, constellation):
    returnVal = None
    url = addr + "/constellationRedisId/" + constellation
    response = requests.get(url)
    json_data = json.loads(response.text)

    if response.status_code == 200:
        returnVal = json_data['redis_id']

    return returnVal

def databaseManagerRequestHandler(ch, method, properties, body):
    test = json.loads(body.decode())
    constellation = test.get('constellation')
    coordinatesInput = test.get('coordinates')
    if(coordinatesInput and len(coordinatesInput) == 2):
        coordinates = Topos(coordinatesInput[0], coordinatesInput[1])
    else:
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return
    messageBody = {}
    if constellation is not None:
        addr = "http://" + str(requestRedisIDHost) + ":5000"
        redisID = getRedis(addr, constellation)
        if redisID is not None:
            database = redis.Redis(host=redisHost, port=6379, db=redisID)
            satellites.clear()
            satellitesReturn = []
            currentTime = ts.now()
            print("CURRENT TIME:", currentTime.utc_datetime())
            for key in database.keys():
                currentSat = json.loads(database.get(key.decode("utf-8")).decode("utf-8"))
                satellite = EarthSatellite(currentSat['line1'], currentSat['line2'], currentSat['platform'], ts)
                satellites.append(satellite)

            overheadCount = 0
            for satellite in satellites:
                pos_diff = satellite - coordinates
                current_diff = pos_diff.at(currentTime)
                alt, az, distance = current_diff.altaz()
                if alt.degrees > 0:
                    overheadCount+=1
                    satellitesReturn.append(satellite.name)
            print(overheadCount)
            messageBody['satellite_count'] = overheadCount
            messageBody['satellites'] = satellitesReturn

    message=jsonpickle.encode(messageBody)
    ch.basic_publish(exchange='',routing_key=properties.reply_to, properties=pika.BasicProperties(correlation_id=properties.correlation_id), body=message)                
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='databaseManagerRequests', on_message_callback=databaseManagerRequestHandler)
    channel.start_consuming()

if __name__ == "__main__":
    main()