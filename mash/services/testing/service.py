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
from mash.services.status_levels import EXCEPTION
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
        self.set_logfile(self.config.get_log_file())

        self.jobs = {}

        # Bind and consume job_events from jobcreator
        self.consume_queue(
            self._process_message,
            self.bind_service_queue()
        )

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_listener(
            self._process_test_result,
            events.EVENT_JOB_EXECUTED | events.EVENT_JOB_ERROR
        )

        try:
            self.start()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.stop()

    def _add_job(self, job):
        """
        Add job to jobs dict and bind new listener queue to uploader exchange.

        Job description is validated and converted to dict from json.
        """
        if job.job_id not in self.jobs:
            self.jobs[job.job_id] = job

            self.consume_queue(
                self._process_message,
                self.bind_listener_queue(job.job_id)
            )

            self.log.info(
                'Job queued, awaiting uploader result.',
                extra=job._get_metadata()
            )
        else:
            self.log.warning(
                'Job already queued.',
                extra=job._get_metadata()
            )

    def _cleanup_job(self, job_id, status):
        """
        Job failed upstream.

        Delete job if not set to always and notify the publisher.
        """
        job = self.jobs[job_id]
        job.status = status
        self.log.warning('Failed upstream.', extra=job._get_metadata())

        # TODO: The flow of job errors, and dropping of jobs is TBD
        if job.utctime != 'always':
            self._delete_job(job_id)
        self._publish_message(job)

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
                extra=job._get_metadata()
            )

            del self.jobs[job_id]
            self.delete_listener_queue(job_id)
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
        data = {
            'testing_result': {
                'job_id': job.job_id,
                'status': job.status,
                'image_id': job.image_id
            }
        }

        return json.dumps(data, sort_keys=True)

    def _handle_jobs(self, message):
        """
        Callback for events from jobcreator.

        job_config example:
        {
            "testing_job_add": {
                "account": "account",
                "job_id": "1",
                "provider": "EC2",
                "tests": "test_stuff",
                "utctime": "now"
            }
        }
        """
        message.ack()

        try:
            job_desc = json.loads(message.body)
        except ValueError as e:
            self.log.error('Invalid job config file: {}.'.format(e))
            self._notify_invalid_config(message.body)
        else:
            if 'testing_job_add' in job_desc:
                self._validate_job(job_desc['testing_job_add'])
            elif 'testing_job_delete' in job_desc and \
                    job_desc['testing_job_delete']:
                self._delete_job(job_desc['testing_job_delete'])
            else:
                self.log.error(
                    'Invalid testing job: Desc must contain either'
                    'testing_job_add or testing_job_delete key.'
                )
                self._notify_invalid_config(message.body)

    def _log_job_message(self, msg, metadata):
        """
        Callback for job instance to log given message.
        """
        self.log.info(msg, extra=metadata)

    def _notify_invalid_config(self, message):
        try:
            self._publish('jobcreator', 'invalid_config', message)
        except AMQPError:
            self.log.warning('Message not received: {0}'.format(message))

    def _process_message(self, message):
        """
        Channel callback, handles incoming messages in queues.

        Send message to proper method based on routing_key.
        """
        if message.method['routing_key'] == 'service_event':
            self._handle_jobs(message)
        else:
            self._test_image(message)

    def _process_test_result(self, event):
        """
        Callback when testing background process finishes.

        Handle exceptions and errors that occur during testing and
        logs info to job log.
        """
        job_id = event.job_id
        job = self.jobs[job_id]
        metata = job._get_metadata()

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
        elif job.status:
            self.log.error(
                'Pass[{0}]: Error occurred testing image with IPA.'.format(
                    job.iteration_count
                ),
                extra=metata
            )
        else:
            self.log.info(
                'Pass[{0}]: Testing successful.'.format(job.iteration_count),
                extra=metata
            )

        # TODO: The flow of job errors, and dropping of jobs is TBD
        self._publish_message(job)

    def _publish_message(self, job):
        """
        Publish status message to provided service exchange.
        """
        exchange = 'publisher'
        key = 'listener_{0}'.format(job.job_id)
        message = self._get_status_message(job)

        try:
            self._bind_queue(exchange, key)
            self._publish(exchange, key, message)
        except AMQPError:
            self.log.warning(
                'Message not received: {0}'.format(message),
                extra=job._get_metadata()
            )

    def _run_test(self, job_id):
        """
        Test image with IPA based on job id.
        """
        job = self.jobs[job_id]
        job.test_image(host=self.host)

    def _test_image(self, message):
        """
        Callback for image testing:

        {
            "uploader_result": {
                "job_id": "1",
                "image_id": "ami-2c40774c",
                "status": 0
            }
        }

        1. Create IPA testing instance and launch tests on given
           image in the cloud provider.
        3. Process and log results.

        TODO: The flow of job errors, and dropping of jobs is TBD
        """
        message.ack()

        job_id = None
        try:
            job = json.loads(message.body)['uploader_result']
            job_id = job['job_id']
            image_id = job['image_id']
            status = job['status']
        except Exception:
            self.log.error(
                'Invalid uploader result file: {0}'.format(message.body)
            )
            status = EXCEPTION

        if not job_id:
            self.log.error('No job_id in uploader result file.')
        elif not self.jobs.get(job_id):
            self.log.error(
                'Invalid job from uploader with id: {0}.'.format(job_id)
            )
        elif status == 0:
            self.jobs[job_id].image_id = image_id
            self.scheduler.add_job(
                self._run_test,
                args=(job_id,),
                id=job_id,
                max_instances=1,
                misfire_grace_time=None,
                coalesce=True
            )
        else:
            self._cleanup_job(job_id, status)

    def _validate_job(self, job_config):
        """
        Validate the job has the required attributes.
        """
        try:
            provider = job_config['provider']
            assert provider in ('EC2',)

            if provider == 'EC2':
                job = EC2TestingJob(**job_config)

            job.set_log_callback(self._log_job_message)
        except AssertionError:
            self.log.exception(
                'Provider {0} is not supported for testing.'.format(provider)
            )
        except KeyError:
            self.log.exception(
                'No provider: Provider must be in job config.'
            )
        except Exception as e:
            self.log.exception(
                'Invalid job configuration: {0}'.format(e)
            )
        else:
            self._add_job(job)

    def start(self):
        """
        Start testing service.
        """
        self.scheduler.start()

        while True:
            try:
                self.channel.start_consuming()
                if not self.channel.consumer_tags:
                    break
            except AMQPError as error:
                self.log.warning(str(error))
                self._open_connection()

    def stop(self):
        """
        Stop testing service.

        Stop consuming queues and close rabbitmq connections.
        """
        self.scheduler.shutdown()
        self.channel.stop_consuming()
        self.close_connection()
