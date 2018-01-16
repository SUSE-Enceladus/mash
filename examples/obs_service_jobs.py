# example obs jobs
from amqpstorm import Connection

connection = Connection(
    'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
)

channel = connection.channel()

channel.queue.declare(queue='obs.service', durable=True)


channel.basic.publish(
    exchange='obs', routing_key='job_document', mandatory=True, body='{"obsjob_delete": "0815"}'
)

channel.basic.publish(
    exchange='obs', routing_key='job_document', mandatory=True, body='{"obsjob":{"id": "0815","project": "Virtualization:Appliances:Images:Testing_x86","image": "test-image-iso","utctime": "now"}}'
)

channel.basic.publish(
    exchange='obs', routing_key='job_document', mandatory=True, body='{"obsjob":{"id": "4711","project": "Virtualization:Appliances:Images:Testing_x86","image": "test-image-docker","utctime": "always"}}'
)

if channel.is_open:
    channel.close()
connection.close()
