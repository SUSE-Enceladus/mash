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

from mash.mash_exceptions import MashLoggerException
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
        self.set_logfile(self.config.get_log_file(self.service_exchange))

        self.bind_queue(self.service_exchange, 'mash.logger', 'logging')
        self.start()

    def _process_log(self, message):
        """
        Callback for logger queue.

        1. Attempt to de-serialize the log message.
        2. Determine log file name based on job_id.
        3. Write or append to log file.
        """
        message.ack()

        try:
            data = json.loads(message.body)
        except Exception:
            raise MashLoggerException(
                'Could not de-serialize log message.'
            )

        if 'job_id' in data:
            file_name = data.get('job_id')
            log_file = self.config.get_job_log_file(file_name)

            try:
                with open(log_file, 'a') as job_log:
                    job_log.write(
                        data['msg'].replace(
                            'Job[{0}]: '.format(data['job_id']), ''
                        )
                    )
            except Exception as e:
                raise MashLoggerException(
                    'Could not write to log file: {0}'.format(e)
                )

    def start(self):
        """
        Start logger service.
        """
        self.consume_queue(self._process_log, 'logging')
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
        Stop logger service.
        """
        self.channel.stop_consuming()
        self.close_connection()
