# example testing jobs and pipelining
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)
channel = connection.channel()

channel.queue_declare(queue='obs.service_event')

channel.basic_publish(
    exchange='obs', routing_key='service_event', body='{"obsjob":{"id": "4711","project": "Virtualization:Appliances:Images:Testing_x86","image": "test-image-docker","utctime": "always"}}'
)

channel.basic_publish(
    exchange='obs', routing_key='service_event', body='{"obsjob_delete": "0815"}'
)

channel.basic_publish(
    exchange='obs', routing_key='service_event', body='{"obsjob":{"id": "0815","project": "Virtualization:Appliances:Images:Testing_x86","image": "test-image-iso","utctime": "now"}}'
)

channel.basic_publish(
    exchange='obs', routing_key='service_event', body='{"obsjob_listen": "4711"}'
)

if channel.is_open:
    channel.close()
connection.close()
