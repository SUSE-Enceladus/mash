import json
import time

from random import randint

from base_publish import BasePublisherService


class AzurePublisherService(BasePublisherService):
    name = 'azure_publish'

    def publish_image(self, ch, method, properties, body):
        self.message_ack(method.delivery_tag)
        job_id = json.loads(body)['id']

        # Do some work
        self.logger.info('Publishing Azure image for job %s...' % job_id)
        time.sleep(randint(1, 5))

        # Done, pass job to queue for consumption by publisher
        self.logger.info('Azure image published for job %s...' % job_id)

        queue = self.get_queue('obs')
        self.channel.queue_unbind(
            exchange='obs',
            queue=queue,
            routing_key='mash.obs.%s' % job_id
        )

        del self.jobs[job_id]

        self.event_publish(body, job_id)

    def queue_job(self, ch, method, properties, body):
        self.message_ack(method.delivery_tag)

        job = json.loads(body)
        self.jobs[job['id']] = job

        self.channel.queue_bind(
            exchange='obs',
            queue=queue,
            routing_key='mash.obs.%s' % job['id']
        )

        # Set callback for obs events
        self.logger.info('Azure publish service queued job: %s' % job['id'])


if __name__ == '__main__':
    # Initiate publisher service with RabbitMQ connection
    publisher = AzurePublisherService()

    # Bind to obs events queue
    queue = publisher.get_queue('orchestrator')
    publisher.channel.queue_bind(
        exchange='orchestrator',
        queue=queue,
        routing_key='mash.orchestrator.azure_publish'
    )

    # Set callback for obs events
    publisher.queue_consume('queue_job', queue=queue)

    queue = publisher.get_queue('obs')
    publisher.queue_consume('publish_image', queue=queue)

    # Start consuming forever (until error or KeyboardInterrupt.)
    publisher.start_consuming()
