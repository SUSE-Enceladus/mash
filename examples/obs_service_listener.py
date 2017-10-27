import pika
import sys

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)
channel = connection.channel()

# asume we are the uploader service running job 0815 and in
# order to do something we need to wait for the obs service
# to get its part of job 0815 done

listen_to_queue = 'obs.listener_0815'
channel.queue_declare(queue=listen_to_queue, durable=True)

print('waiting for obs service...')

def callback(channel, method, properties, body):
    channel.queue_delete(queue=listen_to_queue)
    print(body)

    print('..we have all data, lets upload')
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
