# example testing job

"""Illustrate job_document received from job creator service"""

import argparse
import json
import jwt
import os

from amqpstorm import Connection
from textwrap import dedent

testing_job = dedent("""\
  {
    "testingjob":
      {
        "id": "0815",
        "utctime": "now",
        "framework": "ec2",
        "test_regions":
          {
            "us-east-1": "rjschwei",
            "cn-north-1": "cn-rjschwei"
          }
        "tests": ['sles-basic', 'openqa-glibc']
       }
  }""")


class Test(object):
    connection = None
    channel = None

    msg_properties = {
        'content_type': 'application/json',
        'delivery_mode': 2
    }

    def __init__(self, service, count=1, status='"success"'):
        count += 1
        self.service = service

        self.connect()
        self.consume_credentials()

        try:
            self.send_jobs(count, status)
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
            self.close_connection()

    def connect(self):
        self.connection = Connection(
            'localhost',
            'guest',
            'guest',
            kwargs={'heartbeat': 600}
        )

        self.channel = self.connection.channel()
        self.channel.confirm_deliveries()

    def consume_credentials(self):
        exchange = 'credentials'
        key = 'request'
        queue = '{0}.{1}'.format(exchange, key)

        template_file = os.path.join(
            'data', '{0}_credentials.json'.format(self.service)
        )
        with open(template_file, 'r') as creds_json:
            creds = json.loads(creds_json.read().strip())
        self.creds_message = jwt.encode(creds, 'mash', algorithm='HS256')

        self.channel.exchange.declare(
            exchange=exchange, exchange_type='direct', durable=True
        )
        self.channel.queue.declare(
            queue=queue, durable=True
        )
        self.channel.queue.bind(
            exchange=exchange,
            queue=queue,
            routing_key=key
        )
        self.channel.basic.consume(
            callback=self.send_credentials, queue=queue
        )

    def close_connection(self):
        self.channel.close()
        self.connection.close()

    def send_jobs(self, count, status):
        self.channel.exchange.declare(
            exchange=self.service, exchange_type='direct', durable=True
        )

        service_queue = '{0}.service'.format(self.service)
        self.channel.queue.declare(
            queue=service_queue, durable=True
        )
        self.channel.queue.bind(
            exchange=self.service,
            queue=service_queue,
            routing_key='job_document'
        )

        template_file = os.path.join(
            'data', '{0}_service_event.json'.format(self.service)
        )
        with open(template_file, 'r') as service_json:
            service_template = service_json.read().strip()

        template_file = os.path.join(
            'data', '{0}_listener_event.json'.format(self.service)
        )
        with open(template_file, 'r') as service_json:
            listener_template = service_json.read().strip()

        for num in range(1, count):
            # Send service event message
            self.channel.basic.publish(
                service_template % num,
                'job_document',
                self.service,
                properties=self.msg_properties,
                mandatory=True
            )

            listener_queue = '{0}.listener'.format(self.service)
            listener_key = '{0}'.format(num)
            self.channel.queue.declare(
                queue=listener_queue,
                durable=True
            )
            self.channel.queue.bind(
                exchange=self.service,
                queue=listener_queue,
                routing_key=listener_key
            )
            # Send listener message
            self.channel.basic.publish(
                listener_template % (num, status),
                listener_key,
                self.service,
                properties=self.msg_properties,
                mandatory=True
            )

    def send_credentials(self, message):
        # Process creds message and get service + id
        message.ack()
        payload = jwt.decode(
            message.body,
            'mash',
            algorithm='HS256'
        )
        service = payload['service']
        job_id = payload['job_id']

        queue = 'credentials.{0}.{1}'.format(service, job_id)
        self.channel.queue.declare(queue=queue, durable=True)
        self.channel.queue.bind(
            exchange=self.service,
            queue=queue,
            routing_key=queue
        )
        # Send listener message
        self.channel.basic.publish(
            self.creds_message,
            queue,
            service,
            properties=self.msg_properties
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mash testing script!.')
    parser.add_argument(
        '--service', type=str,
        help='Service exchange name.'
    )
    parser.add_argument(
        '--jobs', type=int, default=1,
        help='Number of jobs to run.'
    )
    parser.add_argument(
        '--status', type=str, default='"success"',
        help='Status of incoming listener events.'
    )

    args = parser.parse_args()
    Test(args.service, args.jobs, args.status)
