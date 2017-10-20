import json

from base import BaseService


class OrchestratorService(BaseService):
    name = 'orchestrator'
    exchange = 'orchestrator'

    def start_image_release(self, body):
        job_id = json.loads(body)['id']

        # Do some work
        self.logger.info(
            'Start job %s...' % job_id,
            extra=self.get_log_extra(job_id)
        )

        for service in ['obs', 'azure_publish']:
            self.event_publish(body, service)

    def process_error(self, ch, method, properties, body):
        self.message_ack(method.delivery_tag)
        print(
            'Orchestrator, do something with job error!: %s' % json.loads(
                body.decode()
            )['msg']
        )


if __name__ == '__main__':
    # Initiate orchestrator service with RabbitMQ connection
    orchestrator = OrchestratorService()

    queue = orchestrator.get_queue('logger')
    orchestrator.channel.queue_bind(
        exchange='logger',
        queue=queue,
        routing_key='mash.ERROR'
    )
    orchestrator.queue_consume('process_error', queue=queue)

    # Start consuming forever (until error or KeyboardInterrupt.)
    orchestrator.start_consuming()
