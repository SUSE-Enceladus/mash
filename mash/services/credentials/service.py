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

import jwt
import json

from datetime import datetime, timedelta

# project
from mash.services.mash_service import MashService
from mash.services.credentials import get_account_info
from mash.services.credentials.account_datastore import AccountDatastore
from mash.utils.json_format import JsonFormat


class CredentialsService(MashService):
    """
    Implements CredentialsService based on web token technology
    """
    def post_init(self):
        self.listener_queue = 'listener'
        self.job_document_key = 'job_document'

        self.set_logfile(self.config.get_log_file(self.service_exchange))

        self.encryption_keys_file = self.config.get_encryption_keys_file()
        self.jwt_secret = self.config.get_jwt_secret()
        self.jwt_algorithm = self.config.get_jwt_algorithm()
        self.credentials_queue = 'credentials'
        self.credentials_response_key = 'response'

        self.services = self.config.get_service_names(
            credentials_required=True
        )
        self.accounts_file = self.config.get_accounts_file()
        self.credentials_directory = self.config.get_credentials_dir()
        self.account_datastore = AccountDatastore(
            self.accounts_file, self.credentials_directory,
            self.encryption_keys_file, self._send_control_response
        )

        self.jobs = {}

        self.add_account_key = 'add_account'
        self.delete_account_key = 'delete_account'

        self.bind_queue(
            self.service_exchange, self.add_account_key, self.listener_queue
        )
        self.bind_queue(
            self.service_exchange, self.delete_account_key, self.listener_queue
        )
        self.bind_queue(
            self.service_exchange, self.job_document_key, self.service_queue
        )
        self._bind_credential_request_keys()

        self.restart_jobs(self._add_job)
        self.start()

    def _add_job(self, job_document):
        """
        Add new job to credentials queue from job_document.
        """
        job_id = job_document['id']

        if job_id in self.jobs:
            self._send_control_response(
                'Job already queued.', success=False, job_id=job_id
            )
        else:
            self.jobs[job_id] = job_document

            if 'job_file' not in job_document:
                testing_accounts = \
                    self.account_datastore.get_testing_accounts(
                        job_document['cloud'], job_document['cloud_accounts'],
                        job_document['requesting_user']
                    )

                job_document['cloud_accounts'] += testing_accounts

                job_document['job_file'] = self.persist_job_config(
                    job_document
                )

            self._send_control_response(
                'Job queued, awaiting credentials requests.',
                job_id=job_id
            )

    def _bind_credential_request_keys(self):
        """
        Bind routing keys for all valid credential service requests.
        """
        for service in self.services:
            self.bind_queue(
                self.service_exchange, 'request.{0}'.format(service), 'request'
            )

    def _confirm_job(self, job_document):
        """
        Check the user for a given job has access to the requested accounts.

        If the user has access to all accounts respond with the accounts
        info for the given cloud.
        """
        job_id = job_document['id']
        cloud = job_document['cloud']
        cloud_accounts = job_document['cloud_accounts']
        cloud_groups = job_document['cloud_groups']
        requesting_user = job_document['requesting_user']

        try:
            accounts_info = self.account_datastore.check_job_accounts(
                cloud, cloud_accounts, cloud_groups, requesting_user
            )
        except Exception as error:
            self._send_control_response(
                'Invalid job: {0}.'.format(error), success=False,
                job_id=job_id
            )
            job_response = {
                'invalid_job': job_id,
                'error_msg': str(error)
            }
            self._publish(
                'jobcreator', self.job_document_key,
                JsonFormat.json_message(job_response)
            )
        else:
            job_response = {
                'start_job': {
                    'id': job_id,
                    'accounts_info': accounts_info
                }
            }
            self._publish(
                'jobcreator', self.job_document_key,
                JsonFormat.json_message(job_response)
            )

    def _delete_job(self, job_id):
        """
        Remove job from dictionary.
        """
        if job_id in self.jobs:
            job = self.jobs[job_id]
            self._send_control_response(
                'Deleting job.',
                job_id=job_id
            )

            del self.jobs[job_id]
            self.remove_file(job['job_file'])
        else:
            self._send_control_response(
                'Job deletion failed, job is not queued.',
                success=False,
                job_id=job_id
            )

    def _get_credentials_response(self, job_id, issuer):
        """
        Return jwt encoded credentials response message.
        """
        job = self.jobs[job_id]

        response = {
            'exp': datetime.utcnow() + timedelta(minutes=5),  # Expiration time
            'iat': datetime.utcnow(),  # Issued at time
            'sub': 'credentials_response',  # Subject
            'iss': self.service_exchange,  # Issuer
            'aud': issuer,  # audience
            'id': job_id,
            'credentials': self.account_datastore.retrieve_credentials(
                job['cloud_accounts'], job['cloud'], job['requesting_user']
            )
        }
        return jwt.encode(
            response, self.jwt_secret, algorithm=self.jwt_algorithm
        )

    def _handle_account_request(self, message):
        """
        Handle account add messages.

        Example message:
        {
            "account_name": "test-aws",
            "credentials": "encrypted_creds",
            "cloud": "ec2",
            "requesting_user": "user1"
        }
        """
        try:
            account_msg = json.loads(message.body)
        except ValueError as error:
            self._send_control_response(
                'Invalid account request: {0}.'.format(error), success=False
            )
        else:
            if message.method['routing_key'] == self.add_account_key:
                self.add_account(account_msg)
            elif message.method['routing_key'] == self.delete_account_key:
                self.delete_account(account_msg)

        message.ack()

    def _handle_job_documents(self, message):
        """
        Handle credentials job documents.

        Example job document:
        {
            "credentials_job": {
                "id": "123",
                "cloud": "EC2",
                "cloud_accounts": ["test-aws", "test-aws-cn"],
                "requesting_user": "test-aws",
                "last_service": "deprecation"
            }
        }
        """
        try:
            job_document = json.loads(message.body)

            if 'credentials_job_delete' in job_document:
                self._delete_job(job_document['credentials_job_delete'])
            elif 'credentials_job_check' in job_document:
                self._confirm_job(job_document['credentials_job_check'])
            else:
                self._add_job(job_document['credentials_job'])
        except ValueError as error:
            self._send_control_response(
                'Error adding job: {0}.'.format(error), success=False
            )

        message.ack()

    def _handle_credential_request(self, message):
        """
        Handle credentials request messages.

        Example credentials request:
        {
            "exp": "utc_timestamp",
            "iat": "utc_timestamp",
            "sub": "credentials_request",
            "iss": "uploader",
            "aud": "credentials",
            "job_id": "0815",
        }
        """
        try:
            issuer = message.method['routing_key'].split('.')[1]
            request_msg = json.loads(message.body)
            payload = jwt.decode(
                request_msg['jwt_token'], self.jwt_secret,
                algorithm=self.jwt_algorithm, issuer=issuer,
                audience=self.service_exchange
            )
        except Exception as error:
            self._send_control_response(
                'Invalid token request received from {0} service: {1}'.format(
                    issuer, error
                ),
                success=False
            )
        else:
            self._send_credential_response(payload)

        message.ack()

    def _publish_credentials_response(self, credentials_response, issuer):
        """
        Publish the encoded JWT with secrets to the calling service.
        """
        self.bind_queue(
            issuer, self.credentials_response_key, self.credentials_queue
        )
        self._publish(
            issuer, self.credentials_response_key, credentials_response
        )

    def _send_control_response(self, message, success=True, job_id=None):
        job_metadata = {}
        if job_id:
            job_metadata['job_id'] = job_id

        if success:
            self.log.info(message, extra=job_metadata)
        else:
            self.log.error(message, extra=job_metadata)

    def _send_credential_response(self, payload):
        """
        Publish the credentials result JWT token to the issuer service.
        """
        job_id = payload['id']
        job = self.jobs.get(job_id)

        if job:
            issuer = payload['iss']

            credentials_response = self._get_credentials_response(
                job_id, issuer
            )
            message = JsonFormat.json_message(
                {'jwt_token': credentials_response.decode()}
            )

            self.log.info(
                'Received credentials request from {0} for job: {1}.'.format(
                    issuer, job_id
                )
            )

            self._publish_credentials_response(message, issuer)
        else:
            self._send_control_response(
                'Credentials job {0} does not exist.'.format(job_id),
                success=False, job_id=job_id
            )

    def add_account(self, message):
        """
        Add new cloud account to MASH.
        """
        self.log.info(
            'Received add account message for account {0}.'.format(
                message['account_name']
            )
        )

        try:
            account_info = get_account_info(message)
        except Exception as error:
            self.log.warning(
                'Failed to add account to database: {0}'.format(error)
            )
            return

        cloud = message['cloud']
        credentials = message['credentials']
        account_name = message['account_name']
        requesting_user = message['requesting_user']
        group_name = message.get('group')

        try:
            self.account_datastore.add_account(
                account_info, cloud, account_name, requesting_user, credentials,
                group_name
            )
        except Exception as error:
            self.log.warning(
                'Unable to add account: {0}'.format(error)
            )

    def delete_account(self, message):
        """
        Delete cloud account from MASH.
        """
        account_name = message['account_name']
        cloud = message['cloud']
        requesting_user = message['requesting_user']

        try:
            self.account_datastore.delete_account(
                requesting_user, account_name, cloud
            )
        except Exception as error:
            self.log.warning(
                'Unable to delete account: {0}'.format(error)
            )

    def start(self):
        """
        Start credentials service.
        """
        self.consume_queue(self._handle_job_documents)
        self.consume_queue(
            self._handle_account_request, queue_name=self.listener_queue
        )
        self.consume_queue(
            self._handle_credential_request,
            queue_name='request'
        )

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.account_datastore.shutdown()
            self.close_connection()
