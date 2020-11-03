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
import os
import shutil

from apscheduler import events
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import suppress
from cryptography.fernet import Fernet, MultiFernet
from pytz import utc

from mash.mash_exceptions import MashCredentialsDatastoreException


class CredentialsDatastore(object):
    """Class for handling credentials files."""

    def __init__(
        self, credentials_directory,
        encryption_keys_file, log_callback
    ):
        self.credentials_directory = credentials_directory
        self.encryption_keys_file = encryption_keys_file
        self.log_callback = log_callback

        if not os.path.exists(self.encryption_keys_file):
            self._create_encryption_keys_file()

        self.scheduler = BackgroundScheduler(timezone=utc)
        self.scheduler.add_listener(
            self._handle_key_rotation_result,
            events.EVENT_JOB_EXECUTED | events.EVENT_JOB_ERROR
        )

        self.scheduler.start()
        self.scheduler.add_job(
            self._rotate_key,
            'cron',
            day='1st sat,3rd sat',
            hour='0',
            minute='0'
        )

    def save_credentials(
        self, cloud, account_name, requesting_user, credentials
    ):
        """
        Add new cloud account credentials.
        """
        credentials = self._encrypt_credentials(
            json.dumps(credentials)
        )

        self._store_encrypted_credentials(
            account_name, credentials, cloud, requesting_user
        )

    def _check_credentials_exist(self, account, cloud, user):
        """
        Return True if the credentials file exists.
        """
        path = self._get_credentials_file_path(account, cloud, user)
        return os.path.exists(path)

    def _clean_old_keys(self):
        """
        Purge old keys from encryption keys file.

        If there's an error send a message to log callback.
        """
        try:
            with open(self.encryption_keys_file, 'r+') as f:
                f.readline()
                f.truncate(f.tell())
        except Exception as error:
            self.log_callback.error(
                'Unable to clean old keys from {0}: {1}.'.format(
                    self.encryption_keys_file, error
                )
            )

    def _create_encryption_keys_file(self):
        """
        Creates the keys file and stores a new key for use in encryption.
        """
        key = self._generate_encryption_key()
        with open(self.encryption_keys_file, 'w') as keys_file:
            keys_file.write(key)

    def delete_credentials(self, requesting_user, account_name, cloud):
        """Delete account for requesting user."""
        self._remove_credentials_file(
            account_name, cloud, requesting_user
        )

    def _encrypt_credentials(self, credentials):
        """
        Encrypt credentials json string.

        Returns: Encrypted and decoded string.
        """
        encryption_keys = self._get_encryption_keys_from_file(
            self.encryption_keys_file
        )
        fernet = MultiFernet(encryption_keys)

        try:
            # Ensure creds string is encoded as bytes
            credentials = credentials.encode()
        except Exception:
            pass

        return fernet.encrypt(credentials).decode()

    def _decrypt_credentials(self, credentials):
        """
        Decrypt credentials string.
        """
        encryption_keys = self._get_encryption_keys_from_file(
            self.encryption_keys_file
        )
        fernet = MultiFernet(encryption_keys)

        try:
            # Ensure string is encoded as bytes before decrypting.
            credentials = credentials.encode()
        except Exception:
            pass

        return fernet.decrypt(credentials).decode()

    def _generate_encryption_key(self):
        """
        Generates and returns a new Fernet key for encryption.
        """
        return Fernet.generate_key().decode()

    def _get_credentials_file_path(self, account, cloud, user):
        """
        Return the string path to the credentials file.

        Based on user, cloud and account name.
        """
        path = os.path.join(
            self.credentials_directory, str(user), cloud, account
        )
        return path

    def _get_user_credentials_path(self, user):
        """
        Return the string path to the user's credentials dir.
        """
        return os.path.join(self.credentials_directory, user)

    def _get_decrypted_credentials(self, account, cloud, user):
        """
        Return decrypted credentials string from file.
        """
        path = self._get_credentials_file_path(account, cloud, user)
        with open(path, 'r') as credentials_file:
            credentials = credentials_file.read()

        return json.loads(self._decrypt_credentials(credentials.strip()))

    def _get_encryption_keys_from_file(self, encryption_keys_file):
        """
        Returns a list of Fernet keys based on the provided keys file.
        """
        with open(encryption_keys_file, 'r') as keys_file:
            keys = keys_file.readlines()

        return [Fernet(key.strip()) for key in keys if key]

    def _handle_key_rotation_result(self, event):
        """
        Callback when key rotation cron finishes.

        If the rotation does not finish successfully the old key
        is left in key file.

        Once a successful rotation happens all old keys are purged.
        """
        if event.exception:
            self.log_callback.error(
                'Key rotation did not finish successfully.'
                ' Old key will remain in key file.'
            )
        else:
            self._clean_old_keys()
            self.log_callback.info('Key rotation finished.')

    def _remove_credentials_file(self, account_name, cloud, user):
        """
        Attempt to remove the credentials file for account.
        """
        self.log_callback.info(
            'Deleting credentials for account: '
            '{0}, cloud: {1}, user: {2}.'.format(
                account_name, cloud, user
            )
        )

        path = self._get_credentials_file_path(account_name, cloud, user)

        with suppress(Exception):
            os.remove(path)

    def remove_user(self, user):
        """
        Attempt to remove the user's credentials dir.
        """
        self.log_callback.info(
            'Deleting credentials for user: {0}'.format(user)
        )

        path = self._get_user_credentials_path(user)

        with suppress(Exception):
            shutil.rmtree(path)

    def retrieve_credentials(self, cloud_accounts, cloud, requesting_user):
        """
        Retrieve the encrypted credentials strings for the requested accounts.
        """
        credentials = {}

        for account in cloud_accounts:
            credentials[account] = self._get_decrypted_credentials(
                account, cloud, requesting_user
            )

        return credentials

    def _rotate_key(self):
        """
        create a new encryption key and rotate all credentials files.

        Will attempt to rotate credentials files to the new key . If
        any fail an exception is raised prior to return.
        """
        self.log_callback.info(
            'Starting key rotation with keys file {0} in directory {1}.'.format(
                self.encryption_keys_file, self.credentials_directory
            )
        )

        success = True

        # Create new key
        keys = [Fernet.generate_key().decode()]

        # Write both keys to file, new key is first
        with open(self.encryption_keys_file, 'r+') as f:
            keys += [key.strip() for key in f.readlines()]
            f.seek(0)
            f.write('\n'.join(keys))

        fernet_keys = [Fernet(key) for key in keys]
        fernet = MultiFernet(fernet_keys)

        # Rotate all credentials files
        for root, dirs, files in os.walk(self.credentials_directory):
            for credentials_file in files:
                if credentials_file == 'wsgi.py':
                    continue

                path = os.path.join(root, credentials_file)
                with open(path, 'r+b') as f:
                    credentials = f.read().strip()

                    try:
                        credentials = fernet.rotate(credentials)
                    except Exception as error:
                        self.log_callback.error(
                            'Failed key rotation on credential file {0}:'
                            ' {1}: {2}'.format(
                                path, type(error).__name__, error
                            )
                        )
                        success = False
                    else:
                        f.seek(0)
                        f.write(credentials)

        if not success:
            raise MashCredentialsDatastoreException(
                'All credentials files have not been rotated.'
            )

    def _store_encrypted_credentials(
        self, account, credentials, cloud, user
    ):
        """
        Store the provided credentials encrypted on disk.

        Expected credentials as a json string.

        Example: {"access_key_id": "key123", "secret_access_key": "123456"}

        Path is based on the user, cloud and account.
        """
        self.log_callback.info(
            'Storing credentials for account: '
            '{0}, cloud: {1}, user: {2}.'.format(
                account, cloud, user
            )
        )

        path = self._get_credentials_file_path(account, cloud, user)

        credentials_dir = os.path.dirname(path)
        if not os.path.isdir(credentials_dir):
            os.makedirs(credentials_dir)

        try:
            with open(path, 'w') as creds_file:
                creds_file.write(credentials)
        except Exception as error:
            self.log_callback.error(
                'Unable to store credentials: {0}.'.format(error)
            )
            raise

    def shutdown(self):
        """Shutdown scheduler."""
        self.scheduler.shutdown()
