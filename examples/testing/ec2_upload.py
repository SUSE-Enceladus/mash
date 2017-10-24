import json
import time

from random import randint

from base_service import BaseService


class EC2UploadService(BaseService):
    name = 'ec2_upload'

    def upload_image(self, channel, method, properties, body):
        """
        - Perform upload when a job is received from obs.
        - Unbind the key once the upload has finished.
        - Clean up local info on job from dict/queue etc.
        - Send a publish event to the ec2_upload exchange.
        - Acknowledge the message from ec2_upload queue on obs exchange.
        """
        job_id = json.loads(body)['id']

        # Do some work
        self.logger.info('Publishing Azure image for job %s...' % job_id)
        time.sleep(randint(1, 5))
        self.logger.info('Azure image published for job %s...' % job_id)

        self.channel.queue_unbind(
            exchange='obs',
            queue='obs.ec2_upload',
            routing_key='mash.obs.%s' % job_id
        )
        del self.jobs[job_id]

        self.event_publish(body, job_id)
        self.message_ack(method.delivery_tag)

    def queue_job(self, ch, method, properties, body):
        """
        - Save the job in a local dict or queue.
        - Bind a new key to obs service using ec2_upload queue.
        - Acknowledge message received and queued locally.
        """
        job = json.loads(body)
        self.jobs[job['id']] = job

        # Bind a new key to the ec2_upload queue.
        # The callback will always be upload_image thus it was
        # already set to consume in the main method below.
        self.channel.queue_bind(
            exchange='obs',
            queue='obs.ec2_upload',
            routing_key='mash.obs.%s' % job['id']
        )

        self.logger.info('Azure publish service queued job: %s' % job['id'])
        self.message_ack(method.delivery_tag)


if __name__ == '__main__':
    # Initiate upload service with RabbitMQ connection
    upload = EC2UploadService()

    # Bind to orchestrator events queue to receive new jobs
    queue = upload.declare_queue('orchestrator.ec2_upload')
    upload.channel.queue_bind(
        exchange='orchestrator',
        queue=queue,
        routing_key='mash.orchestrator.ec2_upload'
    )
    # Set callback for orchestrator events
    upload.queue_consume('queue_job', queue=queue)

    # Declare the ec2_upload queue and consume.
    # At this point ec2 queue exists to get obs events but it's not
    # bound to an exchange. When a message comes in from orchestrator
    # the queue_job callback is triggered which binds a key on this
    # queue to the obs exchange.
    queue = upload.declare_queue('obs.ec2_upload')
    upload.queue_consume('upload_image', queue=queue)

    # Start consuming forever (until error or KeyboardInterrupt.)
    upload.start_consuming()
