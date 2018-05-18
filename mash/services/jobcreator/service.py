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
from mash.services.jobcreator import schema
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

        self.encryption_keys_file = self.config.get_encryption_keys_file()

        self.bind_queue(
            self.service_exchange, self.add_account_key, self.listener_queue
        )

        self.start()

    def _get_accounts_from_file(self):
        """
        Return a dictionary of account information from accounts json file.
        """
        with open(self.accounts_file, 'r') as account_file:
            accounts = json.load(account_file)

        return accounts

    def _handle_listener_message(self, message):
        """
        Process add account messages.
        """
        try:
            account_message = json.loads(message.body)
        except Exception:
            self.log.warning(
                'Invalid message received: {0}.'.format(message.body)
            )
        else:
            if message.method['routing_key'] == 'add_account':
                self.add_account(account_message)
            else:
                self.log.warning(
                    'Received unknown message type: {0}. Message: {1}'.format(
                        message.method['routing_key'],
                        message.body
                    )
                )

        message.ack()

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

    def add_account(self, message):
        """
        Add new provider account to MASH.
        Notify credentials service of new account with encrypted credentials.
        """
        try:
            self.validate_message(message, schema.add_account_ec2)
        except Exception as error:
            self.log.info(
                'Invalid add account message received: {0}.'.format(
                    error
                )
            )
            return

        self.log.info(
            'Received add account message for account {0}.'.format(
                message['account_name']
            )
        )

        accounts = self._get_accounts_from_file()
        provider = message['provider']
        account_name = message['account_name']
        requesting_user = message['requesting_user']
        account = accounts[provider]['accounts'].get(account_name)

        if account and requesting_user != account['requesting_user']:
            self.log.warning(
                'Failed to add account for {0} with the name {1}. Account is '
                'owned by a different user.'.format(
                    requesting_user, account_name
                )
            )
        else:
            # Add account
            accounts[provider]['accounts'][account_name] = {
                'partition': message['partition'],
                'requesting_user': requesting_user
            }

            # Add group if necessary
            group_name = message.get('group')
            if group_name:
                self._add_account_to_group(
                    accounts, account_name, group_name,
                    provider, requesting_user
                )

            self._write_accounts_to_file(accounts)

            message['credentials'] = self.encrypt_credentials(
                json.dumps(message['credentials'])
            )

            self._publish('credentials', self.add_account_key, json.dumps(message))

    def _add_account_to_group(
            self, accounts, account_name, group_name, provider, requesting_user
    ):
        """
        Add the account to the group if it is owned by the same user.
        If the group does not exist create it with the new account.
        """
        if group_name in accounts[provider]['groups']:
            group = accounts[provider]['groups'][group_name]
            if group['requesting_user'] != requesting_user:
                self.log.warning(
                    'Unable to add account to group {0} for {1}. '
                    'Group owned by a different user.'.format(
                        group_name, requesting_user
                    )
                )
            elif account_name not in group['accounts']:
                # Allow for account updates, don't append multiple times.
                group['accounts'].append(account_name)
        else:
            accounts[provider]['groups'][group_name] = {
                'accounts': [account_name],
                'requesting_user': requesting_user
            }

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
