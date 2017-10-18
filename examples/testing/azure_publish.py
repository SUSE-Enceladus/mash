import json
import time

from random import randint

from base_publish import BasePublisherService


class AzurePublisherService(BasePublisherService):
    name = 'azure publisher'

    def publish_image(self, ch, method, properties, body):
        job_id = json.loads(body)['id']

        # Do some work
        self.logger.info('Publishing Azure image for job %s...' % job_id)
        time.sleep(randint(1, 5))

        # Done, pass job to queue for consumption by publisher
        self.event_publish(body)
        self.logger.info('Azure image published for job %s...' % job_id)


if __name__ == '__main__':
    # Initiate publisher service with RabbitMQ connection
    publisher = AzurePublisherService()

    # Bind to obs events queue
    queue = publisher.queue_bind(exchange='obs', routing_key='azure')

    # Set callback for obs events
    publisher.queue_consume('publish_image', queue=queue)

    # Start consuming forever (until error or KeyboardInterrupt.)
    publisher.start_consuming()
