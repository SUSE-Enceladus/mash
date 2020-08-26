# example obs jobs
import json
import os

from amqpstorm import Connection

connection = Connection(
    'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
)

channel = connection.channel()

channel.queue.declare(queue='obs.service', durable=True)

messages = ['obs_delete_job.json', 'obs_now_job.json']
for message in messages:
    job_file = os.path.join('messages', message)
    with open(job_file, 'r') as job_document:
        obs_message = job_document.read().replace(os.linesep, '')

    channel.basic.publish(
        exchange='obs', routing_key='job_document', mandatory=True,
        body=obs_message
    )

if channel.is_open:
    channel.close()
connection.close()
