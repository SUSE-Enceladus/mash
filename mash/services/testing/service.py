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
import logging

from ipa.ipa_controller import test_image

from apscheduler import events
from apscheduler.schedulers.background import BackgroundScheduler

from mash.services.base_service import BaseService
from mash.services.testing.config import TestingConfig
from mash.services.testing.testing_job import TestingJob


class TestingService(BaseService):
    """
    Implementation of testing service. Launches an instance of the
    image in the given cloud provider and tests image using IPA.

    * :attr:`custom_args`
    """
    __test__ = False

    def post_init(self, custom_args=None):
        """
        Initialize testing service class.

        Setup config and bind to orchestrator queue to receive jobs.
        """
        self.config = TestingConfig()
        self.jobs = {}

        # Bind and consume job_events from orchestrator
        self.consume_queue(
            self._handle_jobs,
            self.bind_service_queue()
        )

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_listener(
            self._process_test_result,
            events.EVENT_JOB_EXECUTED | events.EVENT_JOB_ERROR
        )

    def _add_job(self, job):
        """
        Add job to jobs dict and bind new listener queue to uploader exchange.

        Job description is validated and converted to dict from json.
        """
        if job.job_id not in self.jobs:
            self.jobs[job.job_id] = job

            self.consume_queue(
                self._test_image,
                self.bind_listener_queue(job.job_id)
            )

            self.log.info(
                'Job queued.',
                extra=self._get_job_metadata(job)
            )
        else:
            self.log.warning(
                'Job already queued.',
                extra=self._get_job_metadata(job)
            )

    def _delete_job(self, job_id):
        """
        Remove job from dict and delete listener queue.
        """
        if job_id in self.jobs:
            self.log.info(
                'Deleting job.',
                extra=self._get_job_metadata(self.jobs[job_id])
            )

            del self.jobs[job_id]
            self.delete_listener_queue(job_id)
        else:
            self.log.warning(
                'Job deletion failed, job is not queued.',
                extra={'job_id': job_id}
            )

    def _get_job_metadata(self, job):
        """
        Return dictionary of metadata based on job instance.
        """
        return {'job_id': job.job_id}

    def _handle_jobs(self, channel, method, properties, message):
        """
        Callback for events from orchestrator.

        job_config example:
        {"testing_job_add": {
            "account": "account",
            "job_id": "1",
            "provider": "EC2",
            "tests": "test_stuff",
            "utctime": "now"
        }}
        """
        channel.basic_ack(method.delivery_tag)

        try:
            job_desc = json.loads(message.decode())
        except ValueError as e:
            self.log.error('Invalid job config file: {}.'.format(e))
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

    def _get_status_message(self, job):
        """
        Build and return json message with completion status
        to post to service exchange.
        """
        data = {
            'testing_result': {
                'job_id': job.job_id,
                'status': job.status,
                'image': job.image
            }
        }

        return json.dumps(data)

    def _process_test_result(self, event):
        """
        Callback when testing background process finishes.

        Handle exceptions and errors that occur during testing and
        logs info to job log.
        """
        job_id = event.job_id
        job = self.jobs[job_id]
        metata = self._get_job_metadata(job)

        if job.utctime != 'always':
            self._delete_job(job_id)

        if event.exception:
            self.log.error(
                'Exception testing image: {0}'.format(event.exception),
                extra=metata
            )
        elif job.status:
            self.log.error(
                'Error occurred testing image with IPA.',
                extra=metata
            )
        else:
            self.log.info(
                'Testing successful.',
                extra=metata
            )

        self._publish_message(
            job_id,
            self._get_status_message(job)
        )

    def _publish_message(self, identifier, message):
        """
        Publish status message to publisher service exchange.

        When job finishes send json message with status to next
        service, publisher.
        """
        return self._publish(
            'publisher',
            'listener_{0}'.format(identifier),
            message
        )

    def _run_test(self, job_id):
        """
        Test image with IPA based on job id.
        """
        job = self.jobs[job_id]

        job.status, job.results = test_image(
            job.provider,
            account=job.account,
            distro=job.distro,
            log_level=logging.WARNING,
            image_id=job.image,
            tests=job.tests
        )

    def _test_image(self, channel, method, properties, message):
        """
        Callback for image testing:

        {"uploader_result": {"job_id": "1", "image": "ami-2c40774c"}}

        1. Create IPA testing instance and launch tests on given
           image in the cloud provider.
        3. Process and log results.
        """
        channel.basic_ack(method.delivery_tag)

        try:
            job = json.loads(message)['uploader_result']
            job_id = job['job_id']
            image = job['image']
        except Exception:
            self.log.error(
                'Invalid uploader result file: {0}'.format(message)
            )
        else:
            self.jobs[job_id].image = image
            self.scheduler.add_job(
                self._run_test,
                args=(job_id,),
                id=job_id
            )

    def _validate_job(self, job_config):
        """
        Validate the job has the required attributes.
        """
        try:
            job = TestingJob(**job_config)
        except Exception as e:
            self.log.exception(
                'Invalid job configuration: {}'.format(e)
            )
        else:
            self._add_job(job)

    def start(self):
        """
        Start testing service.
        """
        self.scheduler.start()
        self.channel.start_consuming()

    def stop(self):
        """
        Stop testing service.

        Stop consuming queues and close pika connections.
        """
        self.scheduler.shutdown()
        self.channel.stop_consuming()
        self.close_connection()
