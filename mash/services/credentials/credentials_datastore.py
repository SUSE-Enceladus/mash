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

from apscheduler import events
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import suppress
from cryptography.fernet import Fernet, MultiFernet
from pytz import utc

from mash.mash_exceptions import MashCredentialsDatastoreException
from mash.services.credentials.accounts import accounts_template
from mash.utils.json_format import JsonFormat


class CredentialsDatastore(object):
    """Class for handling account data store and credentials files."""

    def __init__(
        self, accounts_file, credentials_directory,
        encryption_keys_file, log_callback
    ):
        self.accounts_file = accounts_file
        self.credentials_directory = credentials_directory
        self.encryption_keys_file = encryption_keys_file
        self.log_callback = log_callback

        if not os.path.exists(self.encryption_keys_file):
            self._create_encryption_keys_file()

        if not os.path.exists(self.accounts_file):
            self._write_accounts_to_file(accounts_template)

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

    def add_account(
        self, account_info, cloud, account_name, requesting_user,
        credentials, group_name=None
    ):
        """
        Add new cloud account to datastore.
        """
        self._add_account_to_datastore(
            account_info, cloud, account_name, requesting_user, group_name
        )

        credentials = self._encrypt_credentials(
            json.dumps(credentials)
        )

        self._store_encrypted_credentials(
            account_name, credentials, cloud, requesting_user
        )

    def _add_account_to_datastore(
        self, account_info, cloud, account_name, requesting_user,
        group_name=None
    ):
        """
        Add account to accounts database based on message data.
        """
        accounts = self._get_accounts_from_file()
        user_data = accounts[cloud]['accounts'].get(requesting_user)

        if user_data:
            user_data[account_name] = account_info
        else:
            accounts[cloud]['accounts'][requesting_user] = {
                account_name: account_info
            }

        # Add group if necessary
        if group_name:
            accounts = self._add_account_to_group(
                accounts, cloud, requesting_user, group_name, account_name
            )

        self._write_accounts_to_file(accounts)

    def _add_account_to_group(
        self, accounts, cloud, requesting_user, group_name, account_name
    ):
        """
        Add the account to the group for the requesting user.

        If the group does not exist create it with the new account.
        """
        groups = accounts[cloud]['groups'].get(requesting_user)

        if groups:
            group = groups.get(group_name)

            if not group:
                groups[group_name] = [account_name]
            elif account_name not in group:
                # Allow for account updates, don't append multiple times.
                group.append(account_name)
        else:
            accounts[cloud]['groups'][requesting_user] = {
                group_name: [account_name]
            }

        return accounts

    def _check_credentials_exist(self, account, cloud, user):
        """
        Return True if the credentials file exists.
        """
        path = self._get_credentials_file_path(account, cloud, user)
        return os.path.exists(path)

    def check_job_accounts(
        self, cloud, cloud_accounts, cloud_groups, requesting_user
    ):
        """
        Confirm all the accounts for the given user have credentials.
        """
        accounts = self._get_accounts_from_file(cloud)
        account_names = [account['name'] for account in cloud_accounts]
        accounts_info = {}

        for group in cloud_groups:
            account_names += self._get_accounts_in_group(
                group, requesting_user, accounts
            )

        for account in set(account_names):
            info = self._get_account_info(
                account, requesting_user, accounts
            )
            if info.get('testing_account'):
                # If testing account does not exist raise exception
                # and prevent job from entering queue.
                self._get_account_info(
                    info['testing_account'], requesting_user, accounts
                )

        for account in set(account_names):
            accounts_info[account] = self._get_account_info(
                account, requesting_user, accounts
            )

            exists = self._check_credentials_exist(
                account, cloud, requesting_user
            )

            if not exists:
                raise MashCredentialsDatastoreException(
                    'The requesting user {0}, does not have '
                    'the following account: {1}'.format(
                        requesting_user, account
                    )
                )

        return accounts_info

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
            self.log_callback(
                'Unable to clean old keys from {0}: {1}.'.format(
                    self.encryption_keys_file, error
                ),
                success=False
            )

    def _create_encryption_keys_file(self):
        """
        Creates the keys file and stores a new key for use in encryption.
        """
        key = self._generate_encryption_key()
        with open(self.encryption_keys_file, 'w') as keys_file:
            keys_file.write(key)

    def delete_account(self, requesting_user, account_name, cloud):
        """Delete account for requesting user."""
        self._remove_credentials_file(
            account_name, cloud, requesting_user
        )

        accounts = self._get_accounts_from_file()

        try:
            del accounts[cloud]['accounts'][requesting_user][account_name]
        except KeyError:
            self.log_callback(
                'Account {0} does not exist for {1}.'.format(
                    account_name, requesting_user
                ),
                success=False
            )
        else:
            accounts = self._remove_account_from_groups(
                accounts, account_name, cloud, requesting_user
            )
            self._write_accounts_to_file(accounts)

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

    def _generate_encryption_key(self):
        """
        Generates and returns a new Fernet key for encryption.
        """
        return Fernet.generate_key().decode()

    def _get_account_info(self, account, user, accounts):
        """
        Return info for the requested account.
        """
        try:
            account_info = accounts['accounts'][user][account]
        except KeyError:
            raise MashCredentialsDatastoreException(
                'The requesting user {0}, does not have '
                'the following account: {1}'.format(
                    user, account
                )
            )

        return account_info

    def _get_accounts_from_file(self, cloud=None):
        """
        Return a dictionary of account information from accounts json file.
        """
        with open(self.accounts_file, 'r') as acnt_file:
            accounts = json.load(acnt_file)

        if cloud:
            return accounts[cloud]
        else:
            return accounts

    def _get_accounts_in_group(self, group, user, accounts_info):
        """
        Return a list of account names given the group name.
        """
        try:
            accounts = accounts_info['groups'][user][group]
        except KeyError:
            raise MashCredentialsDatastoreException(
                'The requesting user: {0}, does not have the '
                'following group: {1}'.format(
                    user, group
                )
            )

        return accounts

    def _get_credentials_file_path(self, account, cloud, user):
        """
        Return the string path to the credentials file.

        Based on user, cloud and account name.
        """
        path = os.path.join(
            self.credentials_directory, user, cloud, account
        )
        return path

    def _get_encrypted_credentials(self, account, cloud, user):
        """
        Return encrypted credentials string from file.
        """
        path = self._get_credentials_file_path(account, cloud, user)
        with open(path, 'r') as credentials_file:
            credentials = credentials_file.read()

        return credentials.strip()

    def _get_encryption_keys_from_file(self, encryption_keys_file):
        """
        Returns a list of Fernet keys based on the provided keys file.
        """
        with open(encryption_keys_file, 'r') as keys_file:
            keys = keys_file.readlines()

        return [Fernet(key.strip()) for key in keys if key]

    def get_testing_accounts(self, cloud, cloud_accounts, requesting_user):
        """
        Return a list of testing accounts based on cloud accounts.

        Only add an account to the list if it does not already exist.
        """
        accounts = self._get_accounts_from_file(cloud)
        testing_accounts = []

        for account in cloud_accounts:
            info = self._get_account_info(
                account, requesting_user, accounts
            )

            if info.get('testing_account') and \
                    info['testing_account'] not in cloud_accounts and \
                    info['testing_account'] not in testing_accounts:
                testing_accounts.append(
                    info['testing_account']
                )

        return testing_accounts

    def _handle_key_rotation_result(self, event):
        """
        Callback when key rotation cron finishes.

        If the rotation does not finish successfully the old key
        is left in key file.

        Once a successful rotation happens all old keys are purged.
        """
        if event.exception:
            self.log_callback(
                'Key rotation did not finish successfully.'
                ' Old key will remain in key file.',
                success=False
            )
        else:
            self._clean_old_keys()
            self.log_callback('Key rotation finished.')

    def _remove_account_from_groups(
        self, accounts, account_name, cloud, requesting_user
    ):
        """Remove account from any groups it currently exists for user."""
        if accounts[cloud].get('groups'):
            groups = accounts[cloud]['groups'].get(requesting_user, {})

            for group, account_names in groups.items():
                if account_name in account_names:
                    account_names.remove(account_name)

        return accounts

    def _remove_credentials_file(self, account_name, cloud, user):
        """
        Attempt to remove the credentials file for account.
        """
        self.log_callback(
            'Deleting credentials for account: '
            '{0}, cloud: {1}, user: {2}.'.format(
                account_name, cloud, user
            )
        )

        path = self._get_credentials_file_path(account_name, cloud, user)

        with suppress(Exception):
            os.remove(path)

    def retrieve_credentials(self, cloud_accounts, cloud, requesting_user):
        """
        Retrieve the encrypted credentials strings for the requested accounts.
        """
        credentials = {}

        for account in cloud_accounts:
            credentials[account] = self._get_encrypted_credentials(
                account, cloud, requesting_user
            )

        return credentials

    def _rotate_key(self):
        """
        create a new encryption key and rotate all credentials files.

        Will attempt to rotate credentials files to the new key . If
        any fail an exception is raised prior to return.
        """
        self.log_callback(
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
                path = os.path.join(root, credentials_file)

                with open(path, 'r+b') as f:
                    credentials = f.read().strip()

                    try:
                        credentials = fernet.rotate(credentials)
                    except Exception as error:
                        self.log_callback(
                            'Failed key rotation on credential file {0}:'
                            ' {1}: {2}'.format(
                                path, type(error).__name__, error
                            ),
                            success=False
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
        self.log_callback(
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
            self.log_callback(
                'Unable to store credentials: {0}.'.format(error),
                success=False
            )

    def _write_accounts_to_file(self, accounts):
        """
        Update accounts file with provided accounts dictionary.
        """
        account_info = JsonFormat.json_message(accounts)

        with open(self.accounts_file, 'w') as account_file:
            account_file.write(account_info)

    def shutdown(self):
        """Shutdown scheduler."""
        self.scheduler.shutdown()
