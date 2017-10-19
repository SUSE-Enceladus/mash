import json
import time

from random import randint

from base import BaseService


class ObsService(BaseService):
    name = 'obs'
    exchange = 'obs'

    def download_image(self, ch, method, properties, body):
        self.message_ack(method.delivery_tag)
        data = json.loads(body)
        job_id = data['id']

        # Do some work
        self.logger.info('Downloading binaries for job %s...' % job_id)
        time.sleep(randint(1, 5))

        # Done, pass job to queue for consumption by publisher if no error
        self.logger.info('Binaries downloaded for job %s...' % job_id)
        self.event_publish(body, job_id)


if __name__ == '__main__':
    # Initiate obs service with RabbitMQ connection
    obs = ObsService()

    # Bind to orchestrator events queue
    queue = obs.bind_service_queue('orchestrator')

    # Set callback for orchestrator events
    obs.queue_consume('download_image', queue=queue)

    # Start consuming forever (until error or KeyboardInterrupt.)
    obs.start_consuming()
