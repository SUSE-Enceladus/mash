import argparse
import json
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

        try:
            self.connect()
            self.send_jobs(count, status)
        except Exception:
            raise
        finally:
            self.close_connection()

    def connect(self):
        self.connection = Connection(
            'localhost', 'guest', 'guest',
            kwargs={'heartbeat': 600}
        )

        self.channel = self.connection.channel()
        self.channel.confirm_deliveries()

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

        # Service job
        template_file = os.path.join(
            'messages', '{0}_job.json'.format(self.service)
        )
        with open(template_file, 'r') as service_json:
            service_template = json.load(service_json)

        # credentials job
        template_file = os.path.join(
            'messages', '{0}_job.json'.format('credentials')
        )
        with open(template_file, 'r') as service_json:
            credentials_template = json.load(service_json)

        if self.prev_service:
            # listener message
            template_file = os.path.join(
                'messages', '{0}_result.json'.format(self.prev_service)
            )
            with open(template_file, 'r') as service_json:
                listener_template = json.load(service_json)

        for num in range(1, count):
            msg_key = '{}_job'.format(self.service)
            service_template[msg_key]['id'] = str(num)
            # Send service event job
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

            credentials_template['credentials_job']['id'] = str(num)

            # Send credentials job
            self.channel.basic.publish(
                json.dumps(credentials_template),
                'job_document',
                'credentials',
                properties=self.msg_properties,
                mandatory=True
            )

            if self.prev_service:
                msg_key = '{}_result'.format(self.prev_service)
                listener_template[msg_key]['id'] = str(num)
                listener_template[msg_key]['status'] = status
                # Send listener message
                self.channel.basic.publish(
                    json.dumps(listener_template),
                    listener_key,
                    self.service,
                    properties=self.msg_properties,
                    mandatory=True
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
        '--status', type=str, default='success',
        help='Status of incoming listener events.'
    )

    args = parser.parse_args()
    Test(args.service, args.jobs, args.status)
