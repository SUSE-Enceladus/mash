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

from amqpstorm import AMQPError

from mash.services.base_service import BaseService
from mash.services.jobcreator.config import JobCreatorConfig


class JobCreatorService(BaseService):
    """
    Implementation of job creator service.

    Handles the orchestration of jobs for mash.
    """

    def post_init(self):
        """
        Initialize job creator service class.
        """
        self.config = JobCreatorConfig()
        self.set_logfile(self.config.get_log_file())

        self.consume_queue(
            self._process_message,
            self._bind_queue(self.service_exchange, 'invalid_config')
        )

        try:
            self.start()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.stop()

    def _process_message(self, message):
        if message.method['routing_key'] == 'invalid_config':
            self._process_invalid_config(message)
        else:
            message.ack()
            self.log.warning(
                'Received unknown message with key: {0}. Message: {1}'.format(
                    message.method['routing_key'],
                    message.body
                )
            )

    def _process_invalid_config(self, message):
        message.ack()

        # Todo: process invalid config message
        pass

    def start(self):
        """
        Start job creator service.
        """
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
        Stop job creator service.
        Stop consuming queues and close pika connections.
        """
        self.channel.stop_consuming()
        self.close_connection()
