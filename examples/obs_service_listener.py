import sys
from amqpstorm import UriConnection

connection = UriConnection(
    'amqp://guest:guest@localhost:5672/%2F?heartbeat=600'
)

channel = connection.channel()

# asume we are the uploader service running job 0815 and in
# order to do something we need to wait for the obs service
# to get its part of job 0815 done

listen_to_queue = 'obs.listener_0815'
channel.queue.declare(queue=listen_to_queue, durable=True)

print('waiting for obs service...')

def callback(body, channel, method, properties):
    channel.queue.delete(queue=listen_to_queue)
    print(body)

    print('..we have all data, lets upload')
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
