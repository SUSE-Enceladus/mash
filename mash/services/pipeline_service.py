# Copyright (c) 2019 SUSE LLC.  All rights reserved.
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
from apscheduler.jobstores.base import ConflictingIdError, JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler

from pytz import utc

from mash.services.mash_service import MashService
from mash.services.status_levels import EXCEPTION, SUCCESS


class PipelineService(MashService):
    """
    Base class for MASH services that live in the image pipeline.
    """
    def post_init(self):
        """Initialize base service class and job scheduler."""
        self.jobs = {}
        self.set_logfile(self.config.get_log_file(self.service_exchange))
        self.service_init()
        self.bind_credentials_queue()

        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.add_listener(
            self._process_job_result,
            events.EVENT_JOB_EXECUTED | events.EVENT_JOB_ERROR
        )

        self.restart_jobs(self._add_job)
        self.start()

    def service_init(self):
        """Initialize child service class."""

    def _add_job(self, job_config):
        """
        Add new job to queue from job_config.
        """
        raise NotImplementedError('Implement in child service.')

    def _cleanup_job(self, job, status):
        """
        Job failed upstream.

        Delete job and notify the next service.
        """
        job.status = status
        self.log.warning('Failed upstream.', extra=job.get_job_id())

        try:
            # Remove job from scheduler if it has
            # not started executing yet.
            self.scheduler.remove_job(job.id)
        except JobLookupError:
            pass

        self._delete_job(job.id)

        if job.last_service != self.service_exchange:
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
            job.log_callback = self.log_job_message

            if 'job_file' not in job_config:
                job_config['job_file'] = self.persist_job_config(
                    job_config
                )
                job.job_file = job_config['job_file']

            self.log.info(
                'Job queued, awaiting listener message.',
                extra=job.get_job_id()
            )

    def _delete_job(self, job_id):
        """
        Remove job from dict and delete listener queue.
        """
        if job_id in self.jobs:
            job = self.jobs[job_id]
            self.log.info(
                'Deleting job.',
                extra=job.get_job_id()
            )

            if job.last_service == self.service_exchange:
                # Send delete message to credentials
                # if this is the last service.
                self.publish_credentials_delete(job_id)

            del self.jobs[job_id]
            self.remove_file(job.job_file)
        else:
            self.log.warning(
                'Job deletion failed, job is not queued.',
                extra={'job_id': job_id}
            )

    def _get_status_message(self, job):
        """
        Build and return json message.

        Message contains completion status to post to next service exchange.
        """
        raise NotImplementedError('Implement in child service.')

    def _handle_credentials_response(self, message):
        """
        Process credentials response JWT tokens.
        """
        try:
            token = json.loads(message.body)
        except Exception:
            self.log.error(
                'Invalid credentials response message: '
                'Must be a json encoded message.'
            )
        else:
            job_id, credentials = self.decode_credentials(token)
            job = self.jobs.get(job_id)

            if job:
                job.credentials = credentials
                self._schedule_job(job.id)
            elif job_id:
                self.log.error(
                    'Credentials received for invalid job with ID:'
                    ' {0}.'.format(job_id)
                )

        message.ack()

    def _handle_listener_message(self, message):
        """
        Callback for listener messages.
        """
        job = self._validate_listener_msg(message.body)

        if job:
            job.listener_msg = message

            if job.credentials:
                self._schedule_job(job.id)
            else:
                self.publish_credentials_request(job.id)
        else:
            message.ack()

    def _handle_service_message(self, message):
        """
        Callback for events from jobcreator.
        """
        job_key = '{0}_job'.format(self.service_exchange)
        try:
            job_desc = json.loads(message.body)
            self._add_job(job_desc[job_key])
        except Exception as e:
            self.log.error('Error adding job: {0}.'.format(e))

        message.ack()

    def _process_job_result(self, event):
        """
        Callback when job background process finishes.

        Handle exceptions and errors that occur and logs info to job log.
        """
        job_id = event.job_id
        job = self.jobs[job_id]
        metadata = job.get_job_id()

        if job.utctime != 'always':
            self._delete_job(job_id)

        if event.exception:
            job.status = EXCEPTION
            self.log.error(
                'Pass[{0}]: Exception in {1}: {2}'.format(
                    job.iteration_count,
                    self.service_exchange,
                    event.exception
                ),
                extra=metadata
            )
        elif job.status == SUCCESS:
            self.log.info(
                'Pass[{0}]: {1} successful.'.format(
                    job.iteration_count,
                    self.service_exchange
                ),
                extra=metadata
            )
        else:
            self.log.error(
                'Pass[{0}]: Error occurred in {1}.'.format(
                    job.iteration_count,
                    self.service_exchange
                ),
                extra=metadata
            )

        # Don't send failure messages for always jobs and
        # don't send message if last service.
        if (job.utctime != 'always' or job.status == SUCCESS) \
                and job.last_service != self.service_exchange:
            self._publish_message(job)
        job.listener_msg.ack()

    def _publish_message(self, job):
        """
        Publish status message to next service exchange.
        """
        message = self._get_status_message(job)
        try:
            self.publish_job_result(self.next_service, message)
        except AMQPError:
            self.log.warning(
                'Message not received: {0}'.format(message),
                extra=job.get_job_id()
            )

    def _schedule_job(self, job_id):
        """
        Schedule new job in background scheduler for job based on id.
        """
        try:
            self.scheduler.add_job(
                self._start_job,
                args=(job_id,),
                id=job_id,
                max_instances=1,
                misfire_grace_time=None,
                coalesce=True
            )
        except ConflictingIdError:
            self.log.warning(
                'Job already running. Received multiple '
                'listener messages.',
                extra={'job_id': job_id}
            )

    def _start_job(self, job_id):
        """
        Run job method.
        """
        raise NotImplementedError('Implement in child service.')

    def _validate_listener_msg(self, message):
        """
        Validate the required keys are in message dictionary.

        If listener message is valid return the job instance.
        """
        args = self._get_listener_msg_args()
        listener_msg = self._get_listener_msg(
            message,
            '{0}_result'.format(self.prev_service)
        )

        if not listener_msg:
            return None

        if self._validate_base_msg(listener_msg, args):
            job = self.jobs[listener_msg['id']]

            for arg in args:
                self._process_msg_arg(listener_msg, arg, job)

            return job
        else:
            return None

    def _get_listener_msg_args(self):
        """Return the required args for the listener message"""
        raise NotImplementedError('Implement in child service.')

    def _get_listener_msg(self, message, key):
        """Load json and attempt to get message by key."""
        try:
            listener_msg = json.loads(message)[key]
        except Exception:
            self.log.error(
                'Invalid listener message: {0}'.format(message)
            )
            listener_msg = None

        return listener_msg

    def _validate_base_msg(self, listener_msg, args):
        """
        Validate the base message.

        - Message should have an id and status.
        - The job should exist.
        - The status should be success.
        """
        for arg in ['id', 'status']:
            if arg not in listener_msg:
                self.log.error('{0} is required in listener message.'.format(arg))
                return False

        if listener_msg['id'] not in self.jobs:
            self.log.error(
                'Invalid listener message with id: {0}.'.format(
                    listener_msg['id']
                )
            )
            return False

        status = listener_msg['status']
        if status != SUCCESS:
            job = self.jobs[listener_msg['id']]
            self._cleanup_job(job, status)
            return False

        for arg in args:
            if arg not in listener_msg:
                self.log.error('{0} is required in listener message.'.format(arg))
                return False

        return True

    def _process_msg_arg(self, listener_msg, arg, job):
        """Set the arg on the job using setter method."""
        setattr(job, arg, listener_msg[arg])

    def start(self):
        """
        Start pipeline service.
        """
        self.scheduler.start()
        self.consume_queue(self._handle_service_message)
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
            self.scheduler.shutdown()
            self.close_connection()
