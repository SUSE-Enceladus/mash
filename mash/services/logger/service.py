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

import os
import json

from mash.exceptions import MashLoggerException
from mash.services.logger.config import LoggerConfig
from mash.services.base_service import BaseService


class LoggerService(BaseService):
    """
    Implementation of logger service. Consumes logs from all
    services and persists to files based on job id.

    * :attr:`custom_args`
    """
    def post_init(self, custom_args=None):
        """
        Initialize logger class.

        Bind to logger exchange and consume with callback
        method to process log.
        """
        self.config = LoggerConfig()

        queue = self._bind_logger_queue()
        self.consume_queue(self._process_log, queue)

    def _bind_logger_queue(self):
        """
        Declare logger exchange and bind queue with routing
        key for logs.
        """
        self._declare_topic_exchange(self.service_exchange)
        routing_key = '{0}.{1}'.format('mash', '*')
        declared_queue = self._declare_queue(
            routing_key
        )
        self.channel.queue_bind(
            exchange=self.service_exchange,
            queue=declared_queue.method.queue,
            routing_key=routing_key
        )
        return declared_queue.method.queue

    def _process_log(self, channel, method, properties, message):
        """
        Callback for logger queue.

        1. Attempt to de-serialize the log message.
        2. Determine log file name based on job_id or class name.
        3. Write or append to log file.
        """
        channel.basic_ack(method.delivery_tag)

        try:
            data = json.loads(message.decode())
        except Exception:
            raise MashLoggerException(
                'Could not de-serialize log message.'
            )

        if 'job_id' in data:
            file_name = data.get('job_id')
        else:
            file_name = data.get('name', 'Mash')

        # Append log dir to file_name
        log_file = self.config.get_log_file(file_name)

        if os.path.exists(log_file):
            mode = 'a'
        else:
            mode = 'w'

        try:
            with open(log_file, mode) as job_log:
                job_log.write(
                    ' '.join([
                        data['levelname'],
                        data['timestamp'],
                        data['name'],
                        os.linesep,
                        data['msg'],
                        os.linesep
                    ])
                )
        except Exception as e:
            raise MashLoggerException(
                'Could not write to log file: {0}'.format(e)
            )
