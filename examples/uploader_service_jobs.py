# example obs jobs
import json
import os

from amqpstorm import Connection

connection = Connection(
    'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
)

channel = connection.channel()

channel.queue.declare(queue='uploader.service', durable=True)
channel.queue.declare(queue='obs.service', durable=True)
channel.queue.declare(queue='credentials.service', durable=True)

messages = [
    ('obs', 'obs_job_delete.json'),
    ('obs', 'obs_now_job.json'),
    ('uploader', 'uploader_job.json')
]

# keep this until the credentials service has been rewritten
# stub credentials service data still needed for testing
channel.basic.publish(
    exchange='credentials', routing_key='job_document', mandatory=True, body='{"credentials": {"id": "123", "csp": "ec2", "payload": {"ssh_key_pair_name": "xxx", "ssh_key_private_key_file": "xxx", "access_key": "xxx", "secret_key": "xxx"}}}'
)

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
