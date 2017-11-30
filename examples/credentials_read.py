import pika
import sys

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)
channel = connection.channel()

listen_to_queue = 'credentials.ec2_4711'
channel.queue_declare(queue=listen_to_queue, durable=True)

print('waiting for credentials service...')

def callback(channel, method, properties, body):
    channel.basic_ack(method.delivery_tag)
    print(body)
    connection.close()
    sys.exit(0)

try:
    channel.basic_consume(
        callback, queue=listen_to_queue
    )
    channel.start_consuming()
except KeyboardInterrupt:
    if channel.is_open:
        channel.close()
    connection.close()
