# example obs jobs
from amqpstorm import Connection

connection = Connection(
    'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
)

channel = connection.channel()

channel.queue.declare(queue='uploader.service', durable=True)
channel.queue.declare(queue='obs.service', durable=True)
channel.queue.declare(queue='credentials.service', durable=True)

channel.basic.publish(
    exchange='obs', routing_key='job_document', mandatory=True, body='{"obsjob_delete": "0815"}'
)
channel.basic.publish(
    exchange='obs', routing_key='job_document', mandatory=True, body='{"obsjob":{"id": "0815","project": "Virtualization:Appliances:Images:Testing_x86","image": "test-image-iso","utctime": "now"}}'
)

channel.basic.publish(
    exchange='credentials', routing_key='job_document', mandatory=True, body='{"credentials": {"id": "0815", "csp": "ec2", "payload": {"ssh_key_pair_name": "xxx", "ssh_key_private_key_file": "xxx", "access_key": "xxx", "secret_key": "xxx"}}}'
)

channel.basic.publish(
    exchange='uploader', routing_key='job_document', mandatory=True, body='{"uploadjob": {"id": "0815", "utctime": "now", "cloud_image_name": "ms_image", "cloud_image_description": "My Image", "ec2": {"launch_ami": "ami-bc5b48d0", "region": "eu-central-1"}}}'
)

if channel.is_open:
    channel.close()
connection.close()
