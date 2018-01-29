# example obs jobs

"""Illustrate job_document received from job creator service"""

from amqpstorm import Connection
from textwrap import dedent

now_job = dedent("""\
  {
    "obs_job": {
                "id": "0815",
                "project": "Virtualization:Appliances:Images:Testing_x86",
                "image": "test-image-iso",
                "utctime": "now"
              }
  }""")

always_job = dedent("""\
  {
    "obs_job": {
                "id": "4711",
                "project": "Virtualization:Appliances:Images:Testing_x86",
                "image": "test-image-docker",
                "utctime": "always"
               }
  }""")

delete_job = dedent("""\
  {
    "obs_job_delete": "0815"
  }""")

connection = Connection(
    'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
)

channel = connection.channel()

channel.queue.declare(queue='obs.service', durable=True)


channel.basic.publish(
    exchange='obs', routing_key='job_document', mandatory=True, body=delete_job
)

channel.basic.publish(
    exchange='obs', routing_key='job_document', mandatory=True, body=now_job
)

channel.basic.publish(
    exchange='obs', routing_key='job_document', mandatory=True, body=always_job
)

if channel.is_open:
    channel.close()
connection.close()
