import sys
from amqpstorm import UriConnection

connection = UriConnection(
    'amqp://guest:guest@localhost:5672/%2F?heartbeat=600'
)

channel = connection.channel()

# asume we are the uploader service running job 0815 and in
# order to do something we need to wait for the obs service
# to get its part of job 0815 done

channel.queue.declare(queue='mash.logger', durable=True)
channel.queue.bind(
    exchange='logger', queue='mash.logger', routing_key='mash.*'
)

def callback(message):
    message.ack()
    print(message.body)

try:
    channel.basic.consume(
        callback, queue='mash.logger'
    )
    channel.start_consuming()
except KeyboardInterrupt:
    if channel.is_open:
        channel.close()
    connection.close()
