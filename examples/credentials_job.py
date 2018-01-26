# example credentials job

"""Illustrate job_document received from job creator service"""

from amqpstorm import Connection
from textwrap import dedent

credentials_job = dedent("""\
  {
    "credentialsjob":
      {
        "id": "0815",
        "framework": "ec2",
        "framework_accounts": ["rjschwei", "cn-rjschwei"],
        "requesting_user": "rjschwei"
      }
  }""")

connection = Connection(
    'localhost', 'guest', 'guest', kwargs={'heartbeat': 600}
)

channel = connection.channel()

channel.queue.declare(queue='credentials.service', durable=True)

channel.basic.publish(
    exchange='credentials', routing_key='job_document', mandatory=True, body='{"credentials": {"id": "4711", "csp": "ec2", "payload": {"ssh_key_pair_name": "xxx", "ssh_key_private_key_file": "xxx", "access_key": "xxx", "secret_key": "xxx"}}}'
)

if channel.is_open:
    channel.close()
connection.close()
