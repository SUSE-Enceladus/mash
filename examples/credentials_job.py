# example credentials job
import json
import os

from amqpstorm import Connection

connection = Connection(
    'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
)

channel = connection.channel()

channel.queue.declare(queue='credentials.service', durable=True)

job_file = os.path.join('messages', 'credentials_job.json')
with open(job_file, 'r') as job_document:
    credentials_message = json.loads(job_document.read().strip())

channel.basic.publish(
    exchange='credentials', routing_key='job_document', mandatory=True,
    body=credentials_message
)

if channel.is_open:
    channel.close()
connection.close()
