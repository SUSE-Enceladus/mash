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

from cryptography.fernet import MultiFernet
from datetime import datetime, timedelta

# project
from mash.services.base_service import BaseService
from mash.services.credentials.config import CredentialsConfig


class CredentialsService(BaseService):
    """
    Implements CredentialsService based on web token technology
    """
    def post_init(self):
        self.config = CredentialsConfig()

        self.set_logfile(self.config.get_log_file(self.service_exchange))
        self.services = self.config.get_service_names(
            credentials_required=True
        )

        encryption_keys_file = self.config.get_encryption_keys_file()
        self.encryption_keys = self.get_encryption_keys_from_file(
            encryption_keys_file
        )

        self.credentials_directory = self.config.get_credentials_dir()

        self.jobs = {}

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
                job_document['job_file'] = self.persist_job_config(
                    job_document
                )

            self._send_control_response(
                'Job queued, awaiting credentials requests.', job_id=job_id
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
        path = os.path.join(
            self.credentials_directory, user, provider, account
        )
        return os.path.exists(path)

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

    def _encrypt_credentials(self, credentials):
        """
        Encrypt credentials json string.

        Returns: Encrypted and decoded string.
        """
        fernet = MultiFernet(self.encryption_keys)

        try:
            # Ensure creds string is encoded as bytes
            credentials = credentials.encode()
        except Exception:
            pass

        return fernet.encrypt(credentials).decode()

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
        path = os.path.join(
            self.credentials_directory, user, provider, account
        )
        with open(path, 'r') as credentials_file:
            credentials = credentials_file.read()

        return credentials.strip()

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
        except ValueError as error:
            self._send_control_response(
                'Invalid job config file: {0}.'.format(error), success=False
            )
            self.notify_invalid_config(message.body)
        else:
            if not self._validate_job_doc(job_document):
                self.notify_invalid_config(message.body)
            elif 'credentials_job_delete' in job_document:
                self._delete_job(job_document['credentials_job_delete'])
            else:
                self._add_job(job_document['credentials_job'])

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

    def _retrieve_credentials(self, job_id):
        """
        Retrieve the credentials for the requested job_id.

        credentials description example:
        {
            "test-aws": {
                "access_key_id": "123456",
                "secret_access_key": "654321",
                "ssh_key_name": "my-key",
                "ssh_private_key": "my-key.pem"
            }
        }

        TODO: Implement method with access to DB.
        """
        job = self.jobs[job_id]

        # For testing purposes a 'test_credentials' key can be passed
        # in the job document to load valid testing credentials.
        # TODO: Remove code when credential storage is implemented.
        if job.get('test_credentials'):
            access_key_id = job['test_credentials']['access_key_id']
            secret_access_key = job['test_credentials']['secret_access_key']
            ssh_key_name = job['test_credentials']['ssh_key_name']
            ssh_private_key = job['test_credentials']['ssh_private_key']
        else:
            access_key_id = None
            secret_access_key = None
            ssh_key_name = None
            ssh_private_key = None

        credentials = {}
        for account in job['provider_accounts']:
            credentials[account] = {
                'access_key_id': access_key_id,
                'secret_access_key': secret_access_key,
                'ssh_key_name': ssh_key_name,
                'ssh_private_key': ssh_private_key
            }
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
        job = self.jobs.get(payload['id'])

        if job:
            credentials_response = self._get_credentials_response(
                payload['id'], payload['iss']
            )
            message = json.dumps({'jwt_token': credentials_response.decode()})
            self._publish_credentials_response(message, payload['iss'])

            if job['utctime'] != 'always' and \
                    job['last_service'] == payload['iss']:
                self._delete_job(job['id'])
        else:
            self._send_control_response(
                'Credentials job {0} does not exist.'.format(payload['id']),
                success=False
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
        path = os.path.join(
            self.credentials_directory, user, provider, account
        )

        credentials_dir = os.path.dirname(path)
        if not os.path.isdir(credentials_dir):
            os.makedirs(credentials_dir)

        encrypted_creds = self._encrypt_credentials(credentials)
        try:
            with open(path, 'w') as creds_file:
                creds_file.write(encrypted_creds)
        except Exception as error:
            self.log.error(
                'Unable to store credentials: {0}.'.format(error)
            )

    def _validate_job_doc(self, job_document):
        """
        Validate the job has the required attributes.
        """
        if 'credentials_job_delete' in job_document:
            return True

        if 'credentials_job' not in job_document:
            self._send_control_response(
                'Invalid credentials job: Job document must contain '
                'the credentials_job key.', success=False
            )
            return False

        data = job_document['credentials_job']
        required = [
            'id', 'provider', 'provider_accounts',
            'requesting_user', 'last_service'
        ]

        for attr in required:
            if attr not in data:
                self._send_control_response(
                    '{0} is required in credentials job doc.'.format(attr),
                    success=False
                )
                return False
        return True

    def start(self):
        """
        Start credentials service.
        """
        self.consume_queue(self._handle_job_documents)
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
        self.channel.stop_consuming()
        self.close_connection()
