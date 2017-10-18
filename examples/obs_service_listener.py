import pika
import sys

listen_to_queue = 'obs.listener_4711'

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)
channel = connection.channel()

channel.queue_declare(queue=listen_to_queue)

def callback(channel, method, properties, body):
    print(body)
    channel.queue_delete(queue=listen_to_queue)
    connection.close()
    sys.exit(0)

try:
    channel.basic_consume(
        callback, queue=listen_to_queue, no_ack=True
    )
    channel.start_consuming()
except KeyboardInterrupt:
    if channel.is_open:
        channel.close()
    connection.close()
