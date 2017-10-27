import pika
import sys

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)
channel = connection.channel()

# asume we are the uploader service running job 0815 and in
# order to do something we need to wait for the obs service
# to get its part of job 0815 done

channel.queue_declare(queue='mash.logger', durable=True)
channel.queue_bind(
    exchange='logger', queue='mash.logger', routing_key='mash.*'
)

def callback(channel, method, properties, body):
    channel.basic_ack(method.delivery_tag)
    print(body)

try:
    channel.basic_consume(
        callback, queue='mash.logger'
    )
    channel.start_consuming()
except KeyboardInterrupt:
    if channel.is_open:
        channel.close()
    connection.close()
