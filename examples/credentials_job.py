# example credentials job
from amqpstorm import Connection

connection = Connection(
    'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
)

channel = connection.channel()

channel.queue.declare(queue='credentials.service_event', durable=True)

channel.basic.publish(
    exchange='credentials', routing_key='service_event', mandatory=True, body='{"credentials": {"id": "4711", "csp": "ec2", "payload": {"ssh_key_pair_name": "xxx", "ssh_key_private_key_file": "xxx", "access_key": "xxx", "secret_key": "xxx"}}}'
)

if channel.is_open:
    channel.close()
connection.close()
