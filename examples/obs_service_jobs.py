# example testing jobs and pipelining
import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost')
)
channel = connection.channel()

channel.queue_declare(queue='obs.service_event', durable=True)


channel.basic_publish(
    exchange='obs', routing_key='service_event', mandatory=True, body='{"obsjob_delete": "0815"}'
)
channel.basic_publish(
    exchange='obs', routing_key='service_event', mandatory=True, body='{"obsjob":{"id": "0815","project": "Virtualization:Appliances:Images:Testing_x86","image": "test-image-iso","utctime": "now"}}'
)
channel.basic_publish(
    exchange='obs', routing_key='service_event', mandatory=True, body='{"obsjob":{"id": "4711","project": "Virtualization:Appliances:Images:Testing_x86","image": "test-image-docker","utctime": "always"}}'
)

listen_to_queue = 'obs.listener_0815'
channel.queue_declare(queue=listen_to_queue, durable=True)
channel.basic_publish(
    exchange='obs', routing_key='service_event', mandatory=True, body='{"obsjob_listen": "0815"}'
)

if channel.is_open:
    channel.close()
connection.close()
