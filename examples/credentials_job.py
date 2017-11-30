# example testing jobs and pipelining
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)
channel = connection.channel()

channel.queue_declare(queue='credentials.service_event', durable=True)

channel.basic_publish(
    exchange='credentials', routing_key='service_event', mandatory=True, body='{"credentials": {"id": "4711", "csp": "ec2", "payload": {"ssh_key_pair_name": "xxx", "ssh_key_private_key_file": "xxx", "access_key": "xxx", "secret_key": "xxx"}}}'
)

if channel.is_open:
    channel.close()
connection.close()
