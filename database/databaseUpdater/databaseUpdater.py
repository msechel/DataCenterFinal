import time
import os
import sys
import json
import redis
import pika
from skyfield.api import load
from pyorbital import tlefile

redisHost = os.getenv("REDIS_HOST") or "localhost"
rabbitMQHost = os.getenv("RABBITMQ_HOST") or "localhost"

constellationRedis = {}
constellationToLink = {}

initialized = False

ts = load.timescale()


print("Connecting to rabbitmq({}) and redis({})".format(rabbitMQHost,redisHost))


def loadSatellites(val):
    satellites = load.tle_file(constellationToLink[val]["link"], filename="%s.txt"%val)

    redisServer = constellationRedis[val]

    for satellite in satellites:
        data = {}
        tle = tlefile.read(satellite.name, "%s.txt"%val)
        data['platform'] = tle.platform
        data['line1'] = tle.line1
        data['line2'] = tle.line2
        json_data = json.dumps(data)
        redisServer.set(tle.platform, json_data)

    os.remove("%s.txt"%val)

    message = "Loaded " +  str(len(satellites)) + " satellites to " + str(val) + " database"
    print(message)
    connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=rabbitMQHost))
    logChannel = connection.channel()
    logChannel.exchange_declare(exchange='logs', exchange_type='topic')
    logChannel.basic_publish(exchange='logs', routing_key='databaseUpdater.info', body=message)

def updateLoop():
    global initialized
    startTime = time.time()
    while True:
        current_time = time.time()
        elapsed_time = current_time - startTime

        if elapsed_time > 3600 or not initialized:
            for val in constellationToLink:
                loadSatellites(val)
            initialized = True
            startTime = time.time()

def loadConstellationLinks(path):
    try:
        file = open(path)
        constellationToLink.update(json.load(file))
        for val in constellationToLink:
            database = redis.Redis(host=redisHost, port=6379, db=constellationToLink[val]["redis_id"])
            constellationRedis[val] = database

            message = "Added Redis for " + str(val) + " at index " + str(constellationToLink[val]["redis_id"])
            print(message)
            connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=rabbitMQHost))
            logChannel = connection.channel()
            logChannel.exchange_declare(exchange='logs', exchange_type='topic')
            logChannel.basic_publish(exchange='logs', routing_key='databaseUpdater.info', body=message)
    except IOError:
        print("Cannot open file %s" % path)
        exit()

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 databaseUpdater.py path/to/constellation/json")
        exit()

    loadConstellationLinks(sys.argv[1])
    updateLoop()

if __name__ == "__main__":
    main()