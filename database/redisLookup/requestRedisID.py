import os
import sys
import pika
import json
import jsonpickle
from flask import Flask, request, Response

##
## Configure test vs. production
##
redisHost = os.getenv("REDIS_HOST") or "localhost"
rabbitMQHost = os.getenv("RABBITMQ_HOST") or "localhost"

print("Connecting to rabbitmq({}) and redis({})".format(rabbitMQHost,redisHost))

constellationToRedisIndex = {}

# Initialize the Flask application
app = Flask(__name__)

@app.route('/', methods=['GET'])
def hello():
    return '<h1> requestRedisID </h1><p> Use a valid endpoint </p>'

@app.route('/constellationRedisId/<constellation>', methods=['GET'])
def match(constellation):
    r = request

    connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=rabbitMQHost))
    logChannel = connection.channel()
    logChannel.exchange_declare(exchange='logs', exchange_type='topic')

    response =  {
                    'redis_id' : constellationToRedisIndex.get(constellation)["redis_id"]
                }
    response_pickled = jsonpickle.encode(response)

    return Response(response=response_pickled, status=200, mimetype="application/json")

def loadConstellationLinks(path):
    try:
        file = open(path)
        constellationToRedisIndex.update(json.load(file))
    except IOError:
        print("Cannot open file %s" % path)
        exit()

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 databaseUpdater.py path/to/constellation/json")
        exit()

    loadConstellationLinks(sys.argv[1])
    # start flask app
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()