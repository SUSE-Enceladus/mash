import sys
from amqpstorm import UriConnection

connection = UriConnection(
    'amqp://guest:guest@localhost:5672/%2F?heartbeat=600'
)

channel = connection.channel()

listen_to_queue = 'credentials.ec2_4711'
channel.queue.declare(queue=listen_to_queue, durable=True)

print('waiting for credentials service...')

def callback(body, channel, method, properties):
    channel.basic.ack(delivery_tag=method['delivery_tag'])
    print(body)
    connection.close()
    sys.exit(0)

try:
    channel.basic.consume(
        callback, queue=listen_to_queue
    )
    channel.start_consuming(to_tuple=True)
except KeyboardInterrupt:
    if channel.is_open:
        channel.close()
    connection.close()
