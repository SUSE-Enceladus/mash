import io
import os
import pytest

from apscheduler.schedulers.background import BackgroundScheduler
from tempfile import TemporaryDirectory
from unittest.mock import call, MagicMock, Mock, patch

from mash.mash_exceptions import MashCredentialsDatastoreException
from mash.services.credentials.credentials_datastore import CredentialsDatastore
from mash.utils.json_format import JsonFormat


class TestAccountDatastore(object):

    @patch('mash.services.credentials.credentials_datastore.BackgroundScheduler')
    @patch('mash.services.credentials.credentials_datastore.os')
    def setup(self, mock_os, mock_scheduler):
        self.log_callback = Mock()
        self.scheduler = MagicMock(BackgroundScheduler)

        mock_os.path.exists.return_value = False
        mock_scheduler.return_value = self.scheduler

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.datastore = CredentialsDatastore(
                '../data/accounts.json', '/var/lib/mash/credentials/',
                '../data/encryption_keys', self.log_callback
            )
            file_handle = mock_open.return_value.__enter__.return_value
            assert file_handle.write.call_count == 2

    @patch('mash.services.credentials.credentials_datastore.os')
    def test_datastore_add_account(self, mock_os):
        mock_os.path.isdir.return_value = False

        account_info = {
            'partition': 'aws',
            'region': 'us-east-1',
            'additional_regions': None
        }

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = \
                '{"ec2": {"groups": {}, "accounts": {}}}'
            file_handle.readlines.return_value = [
                b'WPRWDoAakA0NQFeJhJUFofF9O2-OdjyJR_rQP8KnVd4='
            ]

            self.datastore.add_account(
                account_info, 'ec2', 'acnt123', 'user1', {'creds': 'data'},
                'test'
            )

            output = {
                'ec2': {
                    'groups': {
                        'user1': {
                            'group1': [
                                'acnt123'
                            ]
                        }
                    },
                    'accounts': {
                        'user1': {
                            'acnt123': {
                                'additional_regions': None,
                                'partition': 'aws',
                                'region': 'us-east-1'
                            }
                        }
                    }
                }
            }

            file_handle.write.has_calls([
                call(JsonFormat.json_message(output)),
                call(
                    'gAAAAABcq9BZOo_mZIi1T4rXVkGyjFHXpHhI-rlPj4NFSHC27NeesPx'
                    '2kLkxYBy0WwOr8TuaagVoy__0M_S6k7uIuvpnL0NnUXi646dKxmxFWV'
                    'Dj2hkILDg='
                )
            ])

    @patch('mash.services.credentials.credentials_datastore.os')
    def test_datastore_delete_account(self, mock_os):
        mock_os.path.join.return_value = 'creds_file.path'

        accounts = {
            'ec2': {
                'groups': {
                    'user1': {
                        'group1': [
                            'acnt123'
                        ]
                    }
                },
                'accounts': {
                    'user1': {
                        'acnt123': {
                            'additional_regions': None,
                            'partition': 'aws',
                            'region': 'us-east-1'
                        }
                    }
                }
            }
        }

        empty_accounts = {
            'ec2': {
                'groups': {
                    'user1': {
                        'group1': []
                    }
                },
                'accounts': {
                    'user1': {}
                }
            }
        }

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = JsonFormat.json_message(accounts)

            self.datastore.delete_account(
                'user1', 'acnt123', 'ec2'
            )
            file_handle.write.assert_called_once_with(
                JsonFormat.json_message(empty_accounts)
            )
            self.log_callback.assert_called_once_with(
                'Deleting credentials for account: acnt123, '
                'cloud: ec2, user: user1.'
            )
            mock_os.remove.assert_called_once_with(
                'creds_file.path'
            )

            # Test account does not exist
            self.log_callback.reset_mock()
            self.datastore.delete_account(
                'user1', 'fake', 'ec2'
            )
            self.log_callback.assert_has_calls([
                call(
                    'Deleting credentials for account: fake, '
                    'cloud: ec2, user: user1.'
                ),
                call(
                    'Account fake does not exist for user1.',
                    success=False
                )
            ])

    @patch('mash.services.credentials.credentials_datastore.os')
    @patch.object(CredentialsDatastore, '_get_accounts_from_file')
    def test_check_job_accounts(self, mock_get_accounts, mock_os):
        mock_os.path.exists.return_value = True

        mock_get_accounts.return_value = {
            'accounts': {
                'user1': {
                    'test-aws': {
                        'testing_account': 'tester'
                    },
                    'tester': {}
                }
            },
            'groups': {
                'user1': {
                    'test': ['test-aws']
                }
            }
        }

        self.datastore.check_job_accounts(
            'ec2', [{'name': 'test-aws'}], ['test'], 'user1'
        )

        # Account does not exist for user
        mock_os.path.exists.return_value = False

        with pytest.raises(MashCredentialsDatastoreException) as error:
            self.datastore.check_job_accounts(
                'ec2', [{'name': 'test-aws'}], ['test'], 'user1'
            )

        msg = 'The requesting user user1, does not have ' \
              'the following account: test-aws'
        assert str(error.value) == msg

    def test_shutdown(self):
        self.datastore.shutdown()
        self.scheduler.shutdown.assert_called_once_with()

    def test_get_testing_accounts(self):
        accounts = self.datastore.get_testing_accounts(
            'gce', ['test123'], 'user1'
        )
        assert accounts == ['tester']

    @patch.object(CredentialsDatastore, '_get_encrypted_credentials')
    def test_retrieve_credentials(self, mock_get_enc_creds):
        creds = b'gAAAAABbFapolPqpWrLf5rpEj2xyFLkXlwclSQH-' \
            b'_t3tuJnACyRvOxLdw9qR3kKMBlz3XIrGH9GJdiA9IJl9y' \
            b'_iQLeCfIAM_4ckDMcYHMLe0WWNnsn4zj9E='
        mock_get_enc_creds.return_value = creds

        value = self.datastore.retrieve_credentials(
            ['test123'], 'gce', 'user1'
        )
        assert creds == value['test123']

    # Private method tests

    @patch.object(CredentialsDatastore, '_write_accounts_to_file')
    def test_add_account_to_datastore_existing_user(
        self, mock_write_acnts_file
    ):
        account_info = {
            'partition': 'aws',
            'region': 'us-east-1',
            'additional_regions': None
        }

        # Test existing group
        self.datastore._add_account_to_datastore(
            account_info, 'ec2', 'new123', 'user2', 'test'
        )

        # Test new group
        self.datastore._add_account_to_datastore(
            account_info, 'ec2', 'new123', 'user2', 'test2'
        )

    def test_encrypt_credentials(self):
        # Test creds as bytes encode error is caught and passed
        self.datastore._encrypt_credentials(b'{"test": "creds"}')

    def test_get_account_info_error(self):
        accounts = {
            'accounts': {},
            'groups': {}
        }

        with pytest.raises(MashCredentialsDatastoreException) as error:
            self.datastore._get_account_info(
                'test-aws', 'user1', accounts
            )

        msg = 'The requesting user user1, does not have ' \
              'the following account: test-aws'
        assert str(error.value) == msg

    def test_get_accounts_in_group_error(self):
        accounts_info = {
            'groups': {}
        }

        with pytest.raises(MashCredentialsDatastoreException) as error:
            self.datastore._get_accounts_in_group(
                'test', 'user1', accounts_info
            )

        msg = 'The requesting user: user1, does ' \
              'not have the following group: test'
        assert str(error.value) == msg

    def test_get_encrypted_credentials(self):
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = 'secret_stuff'

            result = self.datastore._get_encrypted_credentials(
                'account1', 'ec2', 'user1'
            )

        assert result == 'secret_stuff'

    @patch.object(CredentialsDatastore, '_clean_old_keys')
    def test_handle_key_rotation_result(self, mock_clean_old_keys):
        # Test exception case
        event = MagicMock()
        event.exception = 'Broken!'

        self.datastore._handle_key_rotation_result(event)
        self.log_callback.assert_called_once_with(
            'Key rotation did not finish successfully.'
            ' Old key will remain in key file.',
            success=False
        )

        # Test success
        event.exception = None
        self.log_callback.reset_mock()

        self.datastore._handle_key_rotation_result(event)
        mock_clean_old_keys.assert_called_once_with()
        self.log_callback.assert_called_once_with(
            'Key rotation finished.'
        )

    def test_clean_old_keys(self):
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.readline.return_value = 'test-key123'
            file_handle.truncate.side_effect = Exception('unable to remove keys')

            self.datastore._clean_old_keys()

        self.log_callback.assert_called_once_with(
            'Unable to clean old keys from ../data/encryption_keys:'
            ' unable to remove keys.',
            success=False
        )

    def test_rotate_key(self):
        with TemporaryDirectory() as test_dir:
            creds_dir = os.path.join(test_dir, 'creds')
            keys_file = os.path.join(test_dir, 'keys.file')

            self.datastore.encryption_keys_file = keys_file
            self.datastore.credentials_directory = creds_dir

            os.makedirs(creds_dir)

            with open(keys_file, 'w') as f:
                f.write('XxgkVrKyG9gZqdvbycZgaSZF1Ro0Vr8DBMXjBuc4uRo=')

            # Create an empty invalid cred file
            open(os.path.join(creds_dir, 'invalid.creds'), 'a').close()

            # Create a valid cred file
            with open(os.path.join(creds_dir, 'valid.creds'), 'w') as cred_file:
                cred_file.write(
                    'gAAAAABbFapolPqpWrLf5rpEj2xyFLkXlwclSQH-_t3tuJnACyRvOxLdw9qR'
                    '3kKMBlz3XIrGH9GJdiA9IJl9y_iQLeCfIAM_4ckDMcYHMLe0WWNnsn4zj9E='
                )

            with pytest.raises(MashCredentialsDatastoreException) as error:
                self.datastore._rotate_key()

            assert str(error.value) == \
                'All credentials files have not been rotated.'

            self.log_callback.assert_has_calls([
                call(
                    'Starting key rotation with keys file {0} '
                    'in directory {1}.'.format(
                        keys_file, creds_dir
                    )
                ),
                call(
                    'Failed key rotation on credential file {0}:'
                    ' InvalidToken: '.format(
                        os.path.join(creds_dir, 'invalid.creds')
                    ),
                    success=False
                )
            ])

    @patch('mash.services.credentials.credentials_datastore.os')
    def test_store_encrypted_credentials(self, mock_os):
        mock_os.isdir.return_value = True

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.side_effect = Exception('Cannot write file')

            self.datastore._store_encrypted_credentials(
                'account1', 'encrypted_secrets', 'ec2', 'user1'
            )
            self.log_callback.assert_has_calls([
                call(
                    'Storing credentials for account: account1, '
                    'cloud: ec2, user: user1.'
                ),
                call(
                    'Unable to store credentials: Cannot write file.',
                    success=False
                )
            ])
