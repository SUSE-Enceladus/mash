import argparse
import json
import jwt
import os

from amqpstorm import Connection

services = ('obs', 'uploader', 'testing', 'replication', 'publisher', 'pint')


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

        prev_index = services.index(self.service) - 1
        self.prev_service = services[prev_index] if prev_index > -1 else None

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
        key = 'request.{0}'.format(self.service)
        queue = '{0}.listener'.format(exchange)

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
            'messages', '{0}_job.json'.format(self.service)
        )
        with open(template_file, 'r') as service_json:
            service_template = json.load(service_json)

        if self.prev_service:
            template_file = os.path.join(
                'messages', '{0}_result.json'.format(self.prev_service)
            )
            with open(template_file, 'r') as service_json:
                listener_template = json.load(service_json)

        for num in range(1, count):
            service_template['id'] = count
            # Send service event message
            self.channel.basic.publish(
                json.dumps(service_template),
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

            if self.prev_service:
                listener_template['id'] = count
                listener_template['status'] = status
                # Send listener message
                self.channel.basic.publish(
                    json.dumps(listener_template),
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
            'enter-a-secret',
            algorithm='HS256',
            audience='credentials',
            issuer=message.method['routing_key'].split('.')[1]
        )

        template_file = os.path.join(
            'messages', 'credentials_response.json'
        )
        with open(template_file, 'r') as creds_json:
            creds = json.load(creds_json)

        # For testing passing None for creds values uses default from config.
        for key, val in creds['credentials'].items():
            for key, val in val.items():
                val = None

        creds['iss'] = payload['aud']
        creds['aud'] = payload['iss']
        creds['id'] = payload['id']

        self.creds_message = jwt.encode(
            creds, 'enter-a-secret', algorithm='HS256'
        )

        queue = '{0}.credentials'.format(payload['iss'])
        self.channel.queue.declare(queue=queue, durable=True)
        self.channel.queue.bind(
            exchange=payload['iss'],
            queue=queue,
            routing_key='credentials_response'
        )
        # Send listener message
        self.channel.basic.publish(
            self.creds_message,
            'credentials_response',
            payload['iss'],
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
