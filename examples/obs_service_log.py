import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)
channel = connection.channel()

channel.queue_declare(queue='logger.log_event')

def callback(channel, method, properties, body):
    print(body)

try:
    channel.basic_consume(
        callback, queue='logger.log_event', no_ack=True
    )
    channel.start_consuming()
except KeyboardInterrupt:
    if channel.is_open:
        channel.close()
    connection.close()
