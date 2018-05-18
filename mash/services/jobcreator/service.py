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

from mash.services.base_service import BaseService
from mash.services.jobcreator.config import JobCreatorConfig
from mash.services.jobcreator.accounts import accounts_template


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
        self.set_logfile(self.config.get_log_file(self.service_exchange))
        self.accounts_file = self.config.get_accounts_file()

        if not os.path.exists(self.accounts_file):
            self._write_accounts_to_file(accounts_template)

        self.bind_queue(
            self.service_exchange, self.add_account_key, self.listener_queue
        )

        self.start()

    def _handle_listener_message(self, message):
        """
        Process add account messages.
        """

    def _handle_service_message(self, message):
        """
        Handle new and delete job messages.
        """
        job_doc = json.loads(message.body)

        if 'job_delete' in job_doc:
            self.publish_delete_job_message(job_doc['job_delete'])

        message.ack()

    def _write_accounts_to_file(self, accounts):
        """
        Update accounts file with provided accounts dictionary.
        """
        account_info = json.dumps(accounts, indent=4)

        with open(self.accounts_file, 'w') as account_file:
            account_file.write(account_info)

    def publish_delete_job_message(self, job_id):
        """
        Publish delete job message to obs and credentials services.

        This will flush the job with the given id out of the pipeline.
        """
        self.log.info(
            'Deleting job with ID: {0}.'.format(job_id)
        )

        delete_message = {
            "obs_job_delete": job_id
        }
        self._publish(
            'obs', self.job_document_key, json.dumps(delete_message)
        )

        delete_message = {
            "credentials_job_delete": job_id
        }
        self._publish(
            'credentials', self.job_document_key, json.dumps(delete_message)
        )

    def start(self):
        """
        Start job creator service.
        """
        self.consume_queue(self._handle_service_message)
        self.consume_queue(
            self._handle_listener_message, queue_name=self.listener_queue
        )
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
        Stop job creator service.
        Stop consuming queues and close pika connections.
        """
        self.channel.stop_consuming()
        self.close_connection()
