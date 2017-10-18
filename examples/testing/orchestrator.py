import json
import random
import time

from base import BaseService


class OrchestratorService(BaseService):
    name = 'orchestrator'
    exchange = 'orchestrator'

    def start_image_release(self, body):
        job_id = json.loads(body)['id']

        # Do some work
        self.logger.info('Start job %s...' % job_id)
        self.event_publish(body)


if __name__ == '__main__':
    # Initiate orchestrator service with RabbitMQ connection
    orchestrator = OrchestratorService()

    while True:
        orchestrator.start_image_release(
            json.dumps(
                {'id': random.randint(1, 100)}
            )
        )
        time.sleep(.5)
