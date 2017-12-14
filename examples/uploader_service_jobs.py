# example obs jobs
from amqpstorm import Connection

connection = Connection(
    'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
)

channel = connection.channel()

channel.queue.declare(queue='uploader.service_event', durable=True)

channel.basic.publish(
    exchange='uploader', routing_key='service_event', mandatory=True, body='{"uploadjob_delete": "123"}'
)

channel.basic.publish(
    exchange='uploader', routing_key='service_event', mandatory=True, body='{"uploadjob": {"id": "123", "utctime": "now", "cloud_image_name": "ms_image", "cloud_image_description": "My Image", "ec2": {"launch_ami": "ami-bc5b48d0", "region": "eu-central-1"}}}'
)

if channel.is_open:
    channel.close()
connection.close()
