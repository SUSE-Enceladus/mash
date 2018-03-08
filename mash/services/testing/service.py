# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#

import json

from amqpstorm import AMQPError

from apscheduler import events
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler

from mash.services.base_service import BaseService
from mash.services.status_levels import EXCEPTION, SUCCESS
from mash.services.testing.config import TestingConfig
from mash.services.testing.ec2_job import EC2TestingJob


class TestingService(BaseService):
    """
    Implementation of testing service. Launches an instance of the
    image in the given cloud provider and tests image using IPA.

    * :attr:`custom_args`
    """
    __test__ = False

    def post_init(self):
        """
        Initialize testing service class.

        Setup config and bind to jobcreator queue to receive jobs.
        """
        self.config = TestingConfig()
        self.set_logfile(self.config.get_log_file(self.service_exchange))

        self.jobs = {}

        self.bind_credentials_queue()

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_listener(
            self._process_test_result,
            events.EVENT_JOB_EXECUTED | events.EVENT_JOB_ERROR
        )

        self.restart_jobs(self._add_job)
        self.start()

    def _add_job(self, job_config):
        """
        Add job to jobs dict and bind new listener queue to uploader exchange.

        Job description is validated and converted to dict from json.
        """
        job_id = job_config['id']
        provider = job_config['provider']

        if job_id in self.jobs:
            self.log.warning(
                'Job already queued.',
                extra={'job_id': job_id}
            )
        elif provider == 'ec2':
            self._create_job(EC2TestingJob, job_config)
        else:
            self.log.exception(
                'Provider {0} is not supported.'.format(provider)
            )

    def _cleanup_job(self, job, status):
        """
        Job failed upstream.

        Delete job and notify the publisher.
        """
        job.status = status
        self.log.warning('Failed upstream.', extra=job.get_metadata())

        self._delete_job(job.id)
        self._publish_message(job)

    def _create_job(self, job_class, job_config):
        """
        Create an instance of job_class with the given config.

        If successful:
        1. Add to jobs queue.
        2. Configure the job.
        3. Store config file if not stored already.
        4. Bind to job listener queue.
        """
        try:
            job = job_class(**job_config)
        except Exception as e:
            self.log.exception(
                'Invalid job configuration: {0}'.format(e)
            )
        else:
            self.jobs[job.id] = job
            job.set_log_callback(self._log_job_message)

            if 'job_file' not in job_config:
                job_config['job_file'] = self.persist_job_config(
                    job_config
                )
                job.config_file = job_config['job_file']

            self.bind_listener_queue(job.id)
            self.log.info(
                'Job queued, awaiting uploader result.',
                extra=job.get_metadata()
            )

    def _delete_job(self, job_id):
        """
        Remove job from dict and delete listener queue.
        """
        if job_id in self.jobs:
            try:
                # Remove job from scheduler if it has
                # not started executing yet.
                self.scheduler.remove_job(job_id)
            except JobLookupError:
                pass

            job = self.jobs[job_id]
            self.log.info(
                'Deleting job.',
                extra=job.get_metadata()
            )

            del self.jobs[job_id]
            self.unbind_queue(
                self.listener_queue, self.service_exchange, job_id
            )
            self.remove_file(job.config_file)
        else:
            self.log.warning(
                'Job deletion failed, job is not queued.',
                extra={'job_id': job_id}
            )

    def _get_status_message(self, job):
        """
        Build and return json message with completion status
        to post to service exchange.
        """
        if job.status == SUCCESS:
            data = {
                'testing_result': {
                    'id': job.id,
                    'cloud_image_name': job.cloud_image_name,
                    'source_regions': job.get_source_regions(),
                    'status': job.status,
                }
            }
        else:
            data = {
                'testing_result': {
                    'id': job.id,
                    'status': job.status,
                }
            }

        return json.dumps(data, sort_keys=True)

    def _handle_credentials_response(self, message):
        """
        Process credentials response JWT tokens.
        """
        token = json.loads(message.body)
        payload = self.decode_credentials(token['jwt_token'])
        job = self.jobs.get(payload['id'])

        job.credentials = payload['credentials']
        self._schedule_job(job.id)

        message.ack()

    def _handle_jobs(self, message):
        """
        Callback for events from jobcreator.

        job_config example:
        {
            "testing_job": {
                "id": "123",
                "provider": "ec2",
                "tests": "test_stuff",
                "utctime": "now",
                "test_regions": {
                    "us-east-1": "test-aws",
                    "cn-north-1": "test-aws-cn"
                }
            }
        }
        """
        try:
            job_desc = json.loads(message.body)
        except ValueError as e:
            self.log.error('Invalid job config file: {}.'.format(e))
            self.notify_invalid_config(message.body)
        else:
            if 'testing_job' in job_desc:
                if not self._validate_job(job_desc['testing_job']):
                    self.notify_invalid_config(message.body)
                else:
                    self._add_job(job_desc['testing_job'])
            else:
                self.log.error(
                    'Invalid testing job: Job config must contain '
                    'testing_job key.'
                )
                self.notify_invalid_config(message.body)

        message.ack()

    def _handle_listener_message(self, message):
        """
        Callback for image testing.

        {
            "uploader_result": {
                "id": "123",
                "cloud_image_name": "image_123",
                "source_regions": {
                    "us-east-1": "ami-bc5b48d0",
                    "cn-north-1": "ami-bc5b4853"
                },
                "status": "success"
            }
        }

        Create IPA testing instance and launch tests on given
        image in the cloud provider.
        """
        job = self._validate_listener_msg(message.body)

        if job:
            job.listener_msg = message

            if job.credentials:
                # Always jobs will have credentials after first iteration
                self._schedule_job(job.id)
            else:
                self.publish_credentials_request(job.id)
        else:
            message.ack()

    def _log_job_message(self, msg, metadata, success=True):
        """
        Callback for job instance to log given message.
        """
        if success:
            self.log.info(msg, extra=metadata)
        else:
            self.log.error(msg, extra=metadata)

    def _process_test_result(self, event):
        """
        Callback when testing background process finishes.

        Handle exceptions and errors that occur during testing and
        logs info to job log.
        """
        job_id = event.job_id
        job = self.jobs[job_id]
        metata = job.get_metadata()

        if job.utctime != 'always':
            self._delete_job(job_id)

        if event.exception:
            job.status = EXCEPTION
            self.log.error(
                'Pass[{0}]: Exception testing image: {1}'.format(
                    job.iteration_count,
                    event.exception
                ),
                extra=metata
            )
        elif job.status == SUCCESS:
            self.log.info(
                'Pass[{0}]: Testing successful.'.format(job.iteration_count),
                extra=metata
            )
        else:
            self.log.error(
                'Pass[{0}]: Error occurred testing image with IPA.'.format(
                    job.iteration_count
                ),
                extra=metata
            )

        # Don't send failure messages for always jobs.
        if job.utctime != 'always' or job.status == SUCCESS:
            self._publish_message(job)
        job.listener_msg.ack()

    def _publish_message(self, job):
        """
        Publish status message to provided service exchange.
        """
        message = self._get_status_message(job)
        try:
            self.publish_job_result('publisher', job.id, message)
        except AMQPError:
            self.log.warning(
                'Message not received: {0}'.format(message),
                extra=job.get_metadata()
            )

    def _run_test(self, job_id):
        """
        Test image with IPA based on job id.
        """
        job = self.jobs[job_id]
        job.test_image(host=self.host)

    def _schedule_job(self, job_id):
        """
        Schedule new job in background scheduler for job based on id.
        """
        self.scheduler.add_job(
            self._run_test,
            args=(job_id,),
            id=job_id,
            max_instances=1,
            misfire_grace_time=None,
            coalesce=True
        )

    def _validate_job(self, job_config):
        """
        Validate the job has the required attributes.
        """
        required = ['id', 'provider', 'tests', 'utctime', 'test_regions']
        for attr in required:
            if attr not in job_config:
                self.log.error(
                    '{0} is required in testing job config.'.format(attr)
                )
                return False
        return True

    def _validate_listener_msg(self, message):
        """
        Validate the required keys are in message dictionary.

        If listener message is valid return the job instance.
        """
        try:
            listener_msg = json.loads(message).get('uploader_result')
        except Exception:
            self.log.error(
                'Invalid uploader result file: {0}'.format(message)
            )
            return None

        job_id = listener_msg.get('id')
        status = listener_msg.get('status')

        if not job_id:
            self.log.error('id is required in uploader result.')
            return None

        job = self.jobs.get(job_id)
        if not job:
            self.log.error(
                'Invalid testing service job with id: {0}.'.format(job_id)
            )
            return None
        elif status != SUCCESS:
            self._cleanup_job(job, status)
            return None
        else:
            if 'cloud_image_name' not in listener_msg:
                    self.log.error(
                        'cloud_image_name is required in uploader result.'
                    )
                    return None
            else:
                job.cloud_image_name = listener_msg['cloud_image_name']

            if 'source_regions' not in listener_msg:
                    self.log.error(
                        'source_regions is required in uploader result.'
                    )
                    return None
            else:
                job.update_test_regions(listener_msg['source_regions'])

        return job

    def start(self):
        """
        Start testing service.
        """
        self.scheduler.start()
        self.consume_queue(self._handle_jobs)
        self.consume_queue(
            self._handle_listener_message, queue_name=self.listener_queue
        )
        self.consume_credentials_queue(self._handle_credentials_response)

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.stop()

    def stop(self):
        """
        Stop testing service.

        Stop consuming queues and close rabbitmq connections.
        """
        self.scheduler.shutdown()
        self.channel.stop_consuming()
        self.close_connection()
