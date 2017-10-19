import json
import logging
import logging.config
import pika
import sys
import time

LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'rabbit': {
            'level': 'DEBUG',
            'class': 'python_logging_rabbitmq.RabbitMQHandler',
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest',
            'exchange': 'logger',
            'declare_exchange': False,
            'connection_params': {
                'virtual_host': '/',
                'connection_attempts': 3,
                'socket_timeout': 5000
            },
            'fields': {
                'env': 'production'
            },
            'fields_under_root': True
        }
    },
    'loggers': {
        'mash': {
            'handlers': ['rabbit'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}


class BaseService(object):
    channel = None
    connection = None
    jobs = {}
    queues = {}

    def __init__(self):
        if not self.name:
            raise Exception('Service name is required in child class.')

        if not self.exchange:
            raise Exception('Exchange is required in child class.')

        # Create logger from log config and add service name
        LOG_CONFIG['handlers']['rabbit']['fields']['source'] = self.name
        logging.config.dictConfig(LOG_CONFIG)
        self.logger = logging.getLogger('mash')

        # Connect to RabbitMQ instance (using connection parameters
        # probably from config)
        params = pika.ConnectionParameters(
            host='localhost',
            port=5672
        )
        self.open_connection(params)

        # Declare service exchange exist
        self.exchange_declare(self.exchange)

    def bind_service_queue(self, service):
        key = 'mash.{}.{}'.format(service, self.name)
        self.channel.queue_bind(
            exchange=service,
            queue=key,
            routing_key=key
        )
        return key

    def close_connection(self):
        if self.channel:
            self.channel.close()

        if self.connection:
            self.connection.close()

        self.connection, self.channel = None, None

    def exchange_declare(self, exchange):
        self.channel.exchange_declare(
            exchange=exchange,
            exchange_type='topic',
            durable=True
        )

    def event_publish(self, body, key, wait=1, timeout=5):
        received = False
        while not received and timeout:
            received = self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.get_routing_key(key),
                body=body,
                properties=pika.BasicProperties(
                    content_type='application/json',
                    delivery_mode=1
                ),
                mandatory=True
            )
            timeout -= 1
            time.sleep(wait)

        if not received:
            self.logger.error(
                'Job was not received by a queue: %s' % json.loads(body)['id']
            )

    def get_queue(self, service):
        if service not in self.queues:
            result = self.channel.queue_declare(durable=True)
            queue_name = result.method.queue
            self.queues[service] = queue_name

        return self.queues[service]

    def get_routing_key(self, key, exchange=None):
        return '{}.{}.{}'.format('mash', exchange or self.exchange, key)

    def message_ack(self, tag):
        self.channel.basic_ack(tag)

    def open_connection(self, params):
        if not self.connection or self.connection.is_closed:
            self.connection = pika.BlockingConnection(params)

        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()
            self.channel.confirm_delivery()

    def queue_bind(self, exchange, routing_key):
        queue = self.get_routing_key(routing_key, exchange)

        self.exchange_declare(exchange)
        self.queue_declare(queue)
        self.channel.queue_bind(exchange=exchange,
                                queue=queue,
                                routing_key=queue)
        return queue

    def queue_consume(self, callback, queue):
        self.channel.basic_consume(
            getattr(self, callback),
            queue=queue
        )

    def queue_declare(self, queue):
        self.channel.queue_declare(queue=queue)

    def start_consuming(self):
        try:
            print(
                ' [*] Starting {} service. To exit press CTRL+C'.format(
                    self.name
                )
            )
            self.channel.start_consuming()
        except KeyboardInterrupt:
            print('See you later!')
        finally:
            for queue in self.queues.values():
                self.channel.queue_delete(queue=queue)

            self.close_connection()
            sys.exit(0)
