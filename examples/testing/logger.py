import json
import pprint

from base import BaseService

pp = pprint.PrettyPrinter(indent=2)


class LoggerService(BaseService):
    name = 'logger'
    exchange = 'logger'

    def process_log(self, ch, method, properties, body):
        self.message_ack(method.delivery_tag)
        print(
            '{}: {}'.format(
                method.routing_key,
                json.loads(body.decode())['msg']
            )
        )


if __name__ == '__main__':
    # Initiate logger service with RabbitMQ connection
    logger = LoggerService()

    # Bind to logger events queue
    queue = '{}.{}'.format('mash', 'logger')
    logger.queue_declare(queue)
    logger.channel.queue_bind(exchange=logger.name,
                              queue=queue,
                              routing_key='mash.*')

    # Set callback for log events
    logger.queue_consume('process_log', queue=queue)

    # Start consuming forever (until error or KeyboardInterrupt.)
    logger.start_consuming()
