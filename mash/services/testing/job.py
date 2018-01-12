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

import dateutil.parser
import time

from amqpstorm import AMQPError, Connection

from mash.mash_exceptions import MashTestingException
from mash.services.status_levels import UNKOWN
from mash.services.testing.constants import NOT_IMPLEMENTED


class TestingJob(object):
    """
    Class for an individual testing job.
    """
    __test__ = False

    def __init__(self,
                 distro,
                 id,
                 provider,
                 tests,
                 utctime,
                 config_file=None,
                 desc=None,
                 instance_type=None,
                 region=None):
        self.channel = None
        self.config_file = config_file
        self.connection = None
        self.credential_queue = 'credentials.testing.{0}'.format(id)
        self.desc = desc
        self.distro = self.validate_distro(distro)
        self.image_id = None
        self.instance_type = instance_type
        self.iteration_count = 0
        self.id = id
        self.log_callback = None
        self.provider = self.validate_provider(provider)
        self.region = region
        self.results = None
        self.status = UNKOWN
        self.tests = self.validate_tests(tests)
        self.utctime = self.validate_timestamp(utctime)

    def _bind_credential_queue(self):
        """
        Declare and bind listener queue to retrieve credentials.

        Credentials service will respond to credentials request by publishing
        a JWT to the queue.
        """
        self.channel.queue.declare(queue=self.credential_queue, durable=True)
        self.channel.queue.bind(
            queue=self.credential_queue,
            exchange='testing',
            routing_key=self.credential_queue
        )

    def _close_connection(self):
        """
        Close connection and channel.
        """
        if self.channel and self.channel.is_open:
            self.channel.close()

        if self.connection and self.connection.is_open:
            self.connection.close()

    def _get_credential_request(self):
        """
        Return json dictionary with credentials request message.
        """
        raise NotImplementedError(NOT_IMPLEMENTED)

    def _get_credentials(self, host):
        """
        Setup rabbitmq channel and queues to collect credentials.

        Published a credential request to credential service. Awaits
        response on queue with credentials JWT.
        """
        self._open_connection(host)
        self._bind_credential_queue()

        exchange = 'credentials'
        key = 'request'
        queue = '{0}.{1}'.format(exchange, key)
        try:
            self.channel.queue.declare(queue=queue, durable=True)
            self.channel.queue.bind(
                exchange=exchange,
                queue=queue,
                routing_key=key
            )
            self.channel.basic.publish(
                self._get_credential_request(),
                key,
                exchange=exchange
            )
        except AMQPError:
            raise MashTestingException(
                'Credentials message not received by RabbitMQ.'
            )

        credentials = self._wait_for_credentials()

        self.channel.queue.delete(queue=self.credential_queue)
        self._close_connection()

        self._process_credentials(credentials)

    def _get_metadata(self):
        """
        Return dictionary of metadata based on job.
        """
        return {'job_id': self.id}

    def _open_connection(self, host):
        """
        Open rabbitmq connection and channel.
        """
        self.connection = Connection(
            host,
            'guest',
            'guest',
            kwargs={'heartbeat': 600}
        )

        self.channel = self.connection.channel()
        self.channel.confirm_deliveries()

    def _process_credentials(self, credentials):
        """
        Verify credential request successful and update self.

        Update instance attrs with credentials.
        """
        raise NotImplementedError(NOT_IMPLEMENTED)

    def _run_tests(self):
        """
        Tests image with IPA and update status and results.
        """
        raise NotImplementedError(NOT_IMPLEMENTED)

    def _wait_for_credentials(self):
        """
        Waits in a while loop for message with credentials to be received.
        """
        timeout = 6
        message = None

        while not message and timeout:
            message = self.channel.basic.get(
                queue=self.credential_queue
            )

            if message:
                message.ack()
                return message.body

            time.sleep(10)
            timeout -= 1

        raise MashTestingException(
            'Credentials message not received from credential service.'
        )

    def send_log(self, message):
        if self.log_callback:
            self.log_callback(
                'Pass[{0}]: {1}'.format(
                    self.iteration_count,
                    message
                ),
                self._get_metadata()
            )

    def set_log_callback(self, callback):
        """
        Set log_callback function to callback.
        """
        self.log_callback = callback

    def test_image(self, host):
        """
        Get credentials and run image tests with IPA.
        """
        self.iteration_count += 1
        self.send_log('Running IPA tests against image.')

        self._get_credentials(host)
        self._run_tests()

    def validate_distro(self, distro):
        """
        Validate the distro is supported for testing.
        """
        if distro not in ('openSUSE_Leap', 'SLES'):
            raise MashTestingException(
                'Distro: {0} not supported.'.format(distro)
            )
        return distro

    def validate_provider(self, provider):
        """
        Validate the provider is supported for testing.
        """
        if provider not in ('EC2', 'Azure', 'GCE'):
            raise MashTestingException(
                'Provider: {0} not supported.'.format(provider)
            )
        return provider

    def validate_tests(self, tests):
        """
        Validate the tests attr is a comma separated list of tests.

        There must be at least one test provided.
        """
        try:
            tests = [test for test in filter(None, tests.split(','))]
        except Exception:
            raise MashTestingException(
                'Invalid tests format, must be a comma seperated list.'
            )

        if len(tests) < 1:
            raise MashTestingException(
                'Must provide at least one test.'
            )

        return tests

    def validate_timestamp(self, utctime):
        """
        Validate the utctime is always, now or valid utc time format.
        """
        if utctime not in ('always', 'now'):
            try:
                utctime = dateutil.parser.parse(utctime)
            except Exception as e:
                raise MashTestingException(
                    'Invalid utctime format: {0}'.format(e)
                )
        return utctime
