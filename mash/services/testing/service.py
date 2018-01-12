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
import os

from amqpstorm import AMQPError

from apscheduler import events
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler

from tempfile import NamedTemporaryFile

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
        self.set_logfile(self.config.get_log_file())
        self.jobs_dir = self.config.get_jobs_dir()

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

        self._restart_jobs()

        try:
            self.start()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.stop()

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
        elif provider == 'EC2':
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
        self.log.warning('Failed upstream.', extra=job._get_metadata())

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

            if 'config_file' not in job_config:
                job_config['config_file'] = self._persist_job_config(
                    job_config
                )
                job.config_file = job_config['config_file']

            self.consume_queue(
                self._process_message,
                self.bind_listener_queue(job.id)
            )
            self.log.info(
                'Job queued, awaiting uploader result.',
                extra=job._get_metadata()
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
                extra=job._get_metadata()
            )

            del self.jobs[job_id]
            self.delete_listener_queue(job_id)
            self._remove_job_config(job.config_file)
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
                    'image_id': job.image_id,
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

    def _handle_jobs(self, message):
        """
        Callback for events from jobcreator.

        job_config example:
        {
            "testing_job": {
                "account": "account",
                "id": "1",
                "provider": "EC2",
                "tests": "test_stuff",
                "utctime": "now"
            }
        }
        """
        try:
            job_desc = json.loads(message.body)
        except ValueError as e:
            self.log.error('Invalid job config file: {}.'.format(e))
            self._notify_invalid_config(message.body)
        else:
            if 'testing_job' in job_desc:
                if not self._validate_job(job_desc['testing_job']):
                    self._notify_invalid_config(message.body)
                else:
                    self._add_job(job_desc['testing_job'])
            else:
                self.log.error(
                    'Invalid testing job: Desc must contain '
                    'testing_job key.'
                )
                self._notify_invalid_config(message.body)

        message.ack()

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

    def _persist_job_config(self, config):
        job_file = NamedTemporaryFile(
            prefix='job-', suffix='.json', dir=self.jobs_dir, delete=False
        )
        config['config_file'] = job_file.name

        with open(job_file.name, 'w') as config_file:
            config_file.write(json.dumps(config, sort_keys=True))

        return job_file.name

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

        if job.utctime != 'always' or job.status == SUCCESS:
            self._publish_message(job)
        job.listener_msg.ack()

    def _publish_message(self, job):
        """
        Publish status message to provided service exchange.
        """
        exchange = 'publisher'
        key = 'listener_{0}'.format(job.id)
        message = self._get_status_message(job)

        try:
            self._bind_queue(exchange, key)
            self._publish(exchange, key, message)
        except AMQPError:
            self.log.warning(
                'Message not received: {0}'.format(message),
                extra=job._get_metadata()
            )

    def _remove_job_config(self, config_file):
        """
        Remove job config file from disk if it exists.
        """
        try:
            os.remove(config_file)
        except Exception:
            pass

    def _restart_jobs(self):
        """
        Restart jobs from config files.

        Recover from service failure with existing jobs.
        """
        for job_file in os.listdir(self.jobs_dir):
            with open(os.path.join(self.jobs_dir, job_file), 'r') as conf_file:
                job_config = json.load(conf_file)

            self._add_job(job_config)

    def _run_test(self, job_id):
        """
        Test image with IPA based on job id.
        """
        job = self.jobs[job_id]
        job.test_image(host=self.host)

    def _test_image(self, message):
        """
        Callback for image testing.

        {
            "uploader_result": {
                "id": "1",
                "image_id": "ami-2c40774c",
                "status": 0
            }
        }

        Create IPA testing instance and launch tests on given
        image in the cloud provider.
        """
        job = self._validate_listener_msg(message.body)

        if job:
            job.listener_msg = message
            self.scheduler.add_job(
                self._run_test,
                args=(job.id,),
                id=job.id,
                max_instances=1,
                misfire_grace_time=None,
                coalesce=True
            )
        else:
            message.ack()

    def _validate_job(self, job_config):
        """
        Validate the job has the required attributes.
        """
        required = ['id', 'provider', 'tests', 'utctime']
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
            self.log.error('id is required in testing in uploader result.')
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
            for attr in ['image_id', 'image_name', 'source_region']:
                if attr not in listener_msg:
                    self.log.error(
                        '{0} is required in uploader result.'.format(attr)
                    )
                    return None
                else:
                    setattr(job, attr, listener_msg[attr])

        return job

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
