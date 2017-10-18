import logging
import logging.config
import pika
import sys

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
    def __init__(self):
        if not self.name:
            raise Exception('Service name is required in child class.')

        if not self.exchange:
            raise Exception('Exchange is required in child class.')

        LOG_CONFIG['handlers']['rabbit']['fields']['source'] = self.name
        logging.config.dictConfig(LOG_CONFIG)
        self.logger = logging.getLogger('mash')

        # Connect to RabbitMQ instance
        self.connection = None
        self.channel = None
        self.open_connection()

        # Declare service exchange exist
        self.exchange_declare(self.exchange)

    def close_connection(self):
        if self.channel:
            self.channel.close()

        if self.connection:
            self.connection.close()

        self.connection, self.channel = None, None

    def exchange_declare(self, exchange):
        self.channel.exchange_declare(
            exchange=exchange,
            exchange_type='topic'
        )

    def event_publish(self, body, key='events'):
        self.channel.basic_publish(exchange=self.exchange,
                                   routing_key=self.get_routing_key(key),
                                   body=body)

    def get_routing_key(self, key, exchange=None):
        return '{}.{}.{}'.format('mash', exchange or self.exchange, key)

    def open_connection(self):
        if not self.connection or self.connection.is_closed:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    port=5672
                )
            )

        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()

    def queue_bind(self, exchange, routing_key):
        queue = self.get_routing_key(routing_key, exchange)

        self.exchange_declare(exchange)
        self.queue_declare(queue)
        self.channel.queue_bind(exchange=exchange,
                                queue=queue,
                                routing_key=queue)
        return queue

    def queue_consume(self, callback, queue):
        self.channel.basic_consume(getattr(self, callback),
                                   queue=queue,
                                   no_ack=True)

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
            self.close_connection()
            sys.exit(0)
