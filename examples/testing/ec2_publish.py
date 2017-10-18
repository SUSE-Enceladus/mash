import json
import time

from random import randint

from base_publish import BasePublisherService


class EC2PublisherService(BasePublisherService):
    name = 'ec2 publisher'

    def publish_image(self, ch, method, properties, body):
        job_id = json.loads(body)['id']

        # Do some work
        self.logger.info('Publishing EC2 image for job %s...' % job_id)
        time.sleep(randint(1, 5))

        # Done, pass job to queue for consumption by publisher
        self.event_publish(body)
        self.logger.info('EC2 image published for job %s...' % job_id)


if __name__ == '__main__':
    # Initiate publisher service with RabbitMQ connection
    publisher = EC2PublisherService()

    # Bind to obs events queue
    queue = publisher.queue_bind(exchange='obs', routing_key='ec2')

    # Set callback for obs events
    publisher.queue_consume('publish_image', queue=queue)

    # Start consuming forever (until error or KeyboardInterrupt.)
    publisher.start_consuming()
