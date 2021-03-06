# example obs jobs
import json
import os

from amqpstorm import Connection

connection = Connection(
    'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
)

channel = connection.channel()

channel.queue.declare(queue='upload.service', durable=True)
channel.queue.declare(queue='obs.service', durable=True)
channel.queue.declare(queue='credentials.service', durable=True)

messages = [
    ('credentials', 'credentials_job.json'),
    ('obs', 'obs_job_delete.json'),
    ('obs', 'obs_now_job.json'),
    ('upload', 'upload_job.json')
]

for exchange, message in messages:
    job_file = os.path.join('messages', message)
    with open(job_file, 'r') as job_document:
        obs_message = job_document.read().replace(os.linesep, '')

    channel.basic.publish(
        exchange=exchange, routing_key='job_document', mandatory=True,
        body=obs_message
    )

if channel.is_open:
    channel.close()
connection.close()
