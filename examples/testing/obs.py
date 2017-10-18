import json
import time

from random import choice, randint

from base import BaseService


class ObsService(BaseService):
    name = 'obs'
    exchange = 'obs'

    def download_image(self, ch, method, properties, body):
        data = json.loads(body)
        job_id = data['id']
        provider = data['provider']

        # Do some work
        self.logger.info('Downloading binaries for job %s...' % job_id)
        time.sleep(randint(1, 5))

        # Done, pass job to queue for consumption by publisher if no error
        if choice((True, False)):
            self.event_publish(body, 'error')
        else:
            self.event_publish(body, provider)
            self.logger.info('Binaries downloaded for job %s...' % job_id)


if __name__ == '__main__':
    # Initiate obs service with RabbitMQ connection
    obs = ObsService()

    # Bind to orchestrator events queue
    queue = obs.queue_bind(exchange='orchestrator', routing_key='events')

    # Set callback for orchestrator events
    obs.queue_consume('download_image', queue=queue)

    # Start consuming forever (until error or KeyboardInterrupt.)
    obs.start_consuming()
