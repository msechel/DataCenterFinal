import sys
import os
import pika
import jsonpickle
import uuid
import json
from flask import Flask, request, Response

# Initialize the Flask application
app = Flask(__name__)

##
## Configure test vs. production
##
rabbitMQHost = os.getenv("RABBITMQ_HOST") or "localhost"

print("Connecting to rabbitmq({})".format(rabbitMQHost))

# Class adapted from rabbitmq tutorial 6 (RPC)
# https://www.rabbitmq.com/tutorials/tutorial-six-python.html
class requestHandler(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitMQHost))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue='',exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(queue=self.callback_queue, on_message_callback=self.reponseChecker, auto_ack=True)

    def reponseChecker(self, ch, method, properties, body):
        if self.correlation_id == properties.correlation_id:
            self.currentSatellites = body

    def sendDatabaseManagerRequest(self, constellationMessage):
        self.currentSatellites = None
        self.correlation_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='', routing_key='databaseManagerRequests', 
        properties=pika.BasicProperties(reply_to=self.callback_queue, correlation_id=self.correlation_id), body=constellationMessage)
        while(self.currentSatellites is None):
            self.connection.process_data_events()
        return self.currentSatellites

@app.route('/', methods=['GET'])
def hello():
    messageBody =   {}
    message=jsonpickle.encode(messageBody)
    return Response(response=messageBody, status=200, mimetype="application/json")

@app.route('/constellationRequest/', methods=['POST'])
def doRequest():
    requester = requestHandler()
    r = request
    request_json = r.get_json()

    messageBody =   {
                        'constellation' : request_json.get('constellation'),
                        'coordinates' : request_json.get('coordinates')
                    }

    message=jsonpickle.encode(messageBody)
    response = requester.sendDatabaseManagerRequest(message)      
    return Response(response=response, status=200, mimetype="application/json")

def main():
    # start flask app
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    main()
