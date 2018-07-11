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

import jwt
import json
import os

from apscheduler import events
from apscheduler.schedulers.background import BackgroundScheduler

from contextlib import suppress
from cryptography.fernet import Fernet
from datetime import datetime, timedelta

# project
from mash.csp import CSP
from mash.services.base_service import BaseService
from mash.services.credentials.ec2_account import EC2Account
from mash.services.credentials.key_rotate import clean_old_keys, rotate_key
from mash.services.jobcreator.accounts import accounts_template


class CredentialsService(BaseService):
    """
    Implements CredentialsService based on web token technology
    """
    def post_init(self):
        self.set_logfile(self.config.get_log_file(self.service_exchange))

        self.services = self.config.get_service_names(
            credentials_required=True
        )
        self.accounts_file = self.config.get_accounts_file()
        self.credentials_directory = self.config.get_credentials_dir()
        self.jobs = {}

        if not os.path.exists(self.encryption_keys_file):
            self._create_encryption_keys_file()

        if not os.path.exists(self.accounts_file):
            self._write_accounts_to_file(accounts_template)

        self.bind_queue(
            self.service_exchange, self.add_account_key, self.listener_queue
        )
        self.bind_queue(
            self.service_exchange, self.delete_account_key, self.listener_queue
        )
        self._bind_credential_request_keys()

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_listener(
            self._handle_key_rotation_result,
            events.EVENT_JOB_EXECUTED | events.EVENT_JOB_ERROR
        )

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
                job_document['job_file'] = self.persist_job_config(
                    job_document
                )

            self._send_control_response(
                'Job queued, awaiting credentials requests: {0}'.format(
                    json.dumps(job_document, indent=2, sort_keys=True)
                ),
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

    def _check_credentials_exist(self, account, provider, user):
        """
        Return True if the credentials file exists.
        """
        path = self._get_credentials_file_path(account, provider, user)
        return os.path.exists(path)

    def _check_job_accounts(
        self, provider, provider_accounts,
        provider_groups, requesting_user
    ):
        """
        Confirm all the accounts for the given user have credentials.
        """
        accounts = [account['name'] for account in provider_accounts]
        for group in provider_groups:
            accounts += self._get_accounts_in_group(
                group, provider, requesting_user
            )

        for account in set(accounts):
            exists = self._check_credentials_exist(
                account, provider, requesting_user
            )

            if not exists:
                return False
        return True

    def _confirm_job(self, job_document):
        """
        Check the user for a given job has access to the requested accounts.

        If the user has access to all accounts respond with the accounts
        info for the given provider.
        """
        job_id = job_document['id']
        provider = job_document['provider']
        provider_accounts = job_document['provider_accounts']
        provider_groups = job_document['provider_groups']
        requesting_user = job_document['requesting_user']

        valid = self._check_job_accounts(
            provider, provider_accounts, provider_groups, requesting_user
        )

        if valid:
            job_response = {
                'start_job': {
                    'id': job_id,
                    'accounts_info': self._get_accounts_from_file(provider)
                }
            }
            self._publish(
                'jobcreator', self.job_document_key,
                json.dumps(job_response, sort_keys=True)
            )
        else:
            self._send_control_response(
                'User does not own requested accounts.', success=False
            )
            job_response = {'invalid_job': job_id}
            self._publish(
                'jobcreator', self.job_document_key,
                json.dumps(job_response, sort_keys=True)
            )

    def _create_encryption_keys_file(self):
        """
        Creates the keys file and stores a new key for use in encryption.
        """
        key = self._generate_encryption_key()
        with open(self.encryption_keys_file, 'w') as keys_file:
            keys_file.write(key)

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

    def _generate_encryption_key(self):
        """
        Generates and returns a new Fernet key for encryption.
        """
        return Fernet.generate_key().decode()

    def _get_accounts_from_file(self, provider=None):
        """
        Return a dictionary of account information from accounts json file.
        """
        with open(self.accounts_file, 'r') as acnt_file:
            accounts = json.load(acnt_file)

        if provider:
            return accounts[provider]
        else:
            return accounts

    def _get_accounts_in_group(self, group, provider, user):
        """
        Return a list of account names given the group name.
        """
        accounts_info = self._get_accounts_from_file(provider)
        return accounts_info['groups'][user][group]

    def _get_credentials_file_path(self, account, provider, user):
        """
        Return the string path to the credentials file.

        Based on user, provider and account name.
        """
        path = os.path.join(
            self.credentials_directory, user, provider, account
        )
        return path

    def _get_credentials_response(self, job_id, issuer):
        """
        Return jwt encoded credentials response message.
        """
        response = {
            'exp': datetime.utcnow() + timedelta(minutes=5),  # Expiration time
            'iat': datetime.utcnow(),  # Issued at time
            'sub': 'credentials_response',  # Subject
            'iss': self.service_exchange,  # Issuer
            'aud': issuer,  # audience
            'id': job_id,
            'credentials': self._retrieve_credentials(job_id)
        }
        return jwt.encode(
            response, self.jwt_secret, algorithm=self.jwt_algorithm
        )

    def _get_encrypted_credentials(self, account, provider, user):
        """
        Return encrypted credentials string from file.
        """
        path = self._get_credentials_file_path(account, provider, user)
        with open(path, 'r') as credentials_file:
            credentials = credentials_file.read()

        return credentials.strip()

    def _handle_account_request(self, message):
        """
        Handle account add messages.

        Example message:
        {
            "account_name": "test-aws",
            "credentials": "encrypted_creds",
            "provider": "ec2",
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
                self._remove_credentials_file(
                    account_msg['account_name'], account_msg['provider'],
                    account_msg['requesting_user']
                )

        message.ack()

    def _handle_job_documents(self, message):
        """
        Handle credentials job documents.

        Example job document:
        {
            "credentials_job": {
                "id": "123",
                "provider": "EC2",
                "provider_accounts": ["test-aws", "test-aws-cn"],
                "requesting_user": "test-aws",
                "last_service": "pint"
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

    def _handle_key_rotation_result(self, event):
        """
        Callback when key rotation cron finishes.

        If the rotation does not finish successfully the old key
        is left in key file.

        Once a successful rotation happens all old keys are purged.
        """
        if event.exception:
            self.log.error(
                'Key rotation did not finish successfully.'
                ' Old key will remain in key file.'
            )
        else:
            clean_old_keys(
                self.encryption_keys_file, self._send_control_response
            )
            self.log.info('Key rotation finished.')

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

    def _remove_credentials_file(self, account_name, provider, user):
        """
        Attempt to remove the credentials file for account.
        """
        self.log.info(
            'Deleting credentials for account: '
            '{0}, provider: {1}, user: {2}.'.format(
                account_name, provider, user
            )
        )

        path = self._get_credentials_file_path(account_name, provider, user)

        with suppress(Exception):
            os.remove(path)

    def _retrieve_credentials(self, job_id):
        """
        Retrieve the encrypted credentials strings for the requested job_id.
        """
        job = self.jobs[job_id]

        credentials = {}
        for account in job['provider_accounts']:
            credentials[account] = self._get_encrypted_credentials(
                account, job['provider'], job['requesting_user']
            )
        return credentials

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
            message = json.dumps({'jwt_token': credentials_response.decode()})

            self.log.info(
                'Received credentials request from {0} for job: {1}.'.format(
                    issuer, job_id
                )
            )

            self._publish_credentials_response(message, issuer)

            if job['utctime'] != 'always' and \
                    job['last_service'] == issuer:
                self._delete_job(job_id)
        else:
            self._send_control_response(
                'Credentials job {0} does not exist.'.format(job_id),
                success=False
            )

    def _start_rotation_job(self):
        """
        Schedule new key rotation cron job in background scheduler.

        Job is run once a month on the first Saturday at 0000.
        """
        self.scheduler.add_job(
            rotate_key,
            'cron',
            args=(
                self.credentials_directory,
                self.encryption_keys_file,
                self._send_control_response
            ),
            day='1st sat,3rd sat',
            hour='0',
            minute='0'
        )

    def _store_encrypted_credentials(
        self, account, credentials, provider, user
    ):
        """
        Store the provided credentials encrypted on disk.

        Expected credentials as a json string.

        Example: {"access_key_id": "key123", "secret_access_key": "123456"}

        Path is based on the user, provider and account.
        """
        self.log.info(
            'Storing credentials for account: '
            '{0}, provider: {1}, user: {2}.'.format(
                account, provider, user
            )
        )

        path = self._get_credentials_file_path(account, provider, user)

        credentials_dir = os.path.dirname(path)
        if not os.path.isdir(credentials_dir):
            os.makedirs(credentials_dir)

        try:
            with open(path, 'w') as creds_file:
                creds_file.write(credentials)
        except Exception as error:
            self.log.error(
                'Unable to store credentials: {0}.'.format(error)
            )

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
        """
        self.log.info(
            'Received add account message for account {0}.'.format(
                message['account_name']
            )
        )

        provider = message['provider']
        account_name = message['account_name']
        requesting_user = message['requesting_user']

        if provider == CSP.ec2:
            account = EC2Account(message)
        else:
            self.log.warning(
                'Invalid provider for account: {0}.'.format(provider)
            )
            return

        accounts = self._get_accounts_from_file()
        account.add_account(accounts)
        self._write_accounts_to_file(accounts)

        credentials = self.encrypt_credentials(
            json.dumps(message['credentials'])
        )

        self._store_encrypted_credentials(
            account_name, credentials, provider, requesting_user
        )

    def start(self):
        """
        Start credentials service.
        """
        self.scheduler.start()
        self._start_rotation_job()

        self.consume_queue(self._handle_job_documents)
        self.consume_queue(
            self._handle_account_request, queue_name=self.listener_queue
        )
        self.consume_credentials_queue(
            self._handle_credential_request, queue_name='request'
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
        Stop credentials service.

        Stop consuming queues and close pika connections.
        """
        self.scheduler.shutdown()
        self.channel.stop_consuming()
        self.close_connection()
