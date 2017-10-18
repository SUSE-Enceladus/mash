import json

from base import BaseService


class OrchestratorService(BaseService):
    name = 'orchestrator'
    exchange = 'orchestrator'

    def start_image_release(self, body):
        job_id = json.loads(body)['id']

        # Do some work
        self.logger.info('Start job %s...' % job_id)
        self.event_publish(body)

    def process_error(self, ch, method, properties, body):
        job_id = json.loads(body)['id']

        self.logger.info('Error occured processing job %s...' % job_id)


if __name__ == '__main__':
    # Initiate orchestrator service with RabbitMQ connection
    orchestrator = OrchestratorService()

    queue = orchestrator.queue_bind(exchange='obs', routing_key='error')
    orchestrator.queue_consume('process_error', queue=queue)

    # Start consuming forever (until error or KeyboardInterrupt.)
    orchestrator.start_consuming()
