import io
import os
import pytest

from apscheduler.schedulers.background import BackgroundScheduler
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

from mash.mash_exceptions import MashCredentialsDatastoreException
from mash.services.credentials.datastore import CredentialsDatastore


class TestCredentialsDatastore(object):

    @patch('mash.services.credentials.datastore.BackgroundScheduler')
    @patch('mash.services.credentials.datastore.os')
    def setup(self, mock_os, mock_scheduler):
        self.log_callback = Mock()
        self.scheduler = MagicMock(BackgroundScheduler)

        mock_os.path.exists.return_value = False
        mock_scheduler.return_value = self.scheduler

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.datastore = CredentialsDatastore(
                '/var/lib/mash/credentials/',
                '../data/encryption_keys',
                self.log_callback
            )
            file_handle = mock_open.return_value.__enter__.return_value
            assert file_handle.write.call_count == 1

    @patch('mash.services.credentials.datastore.os')
    def test_datastore_save_credentials(self, mock_os):
        mock_os.path.isdir.return_value = False

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.readlines.return_value = [
                b'WPRWDoAakA0NQFeJhJUFofF9O2-OdjyJR_rQP8KnVd4='
            ]

            self.datastore.save_credentials(
                'ec2', 'acnt1', 'user1', {'super': 'secret'}
            )

            assert file_handle.write.call_count == 1

    @patch('mash.services.credentials.datastore.os')
    def test_datastore_delete_credentials(self, mock_os):
        mock_os.path.join.return_value = 'creds_file.path'

        self.datastore.delete_credentials(
            'user1', 'acnt123', 'ec2'
        )
        self.log_callback.info.assert_called_once_with(
            'Deleting credentials for account: acnt123, '
            'cloud: ec2, user: user1.'
        )
        mock_os.remove.assert_called_once_with(
            'creds_file.path'
        )

    def test_shutdown(self):
        self.datastore.shutdown()
        self.scheduler.shutdown.assert_called_once_with()

    @patch.object(CredentialsDatastore, '_get_decrypted_credentials')
    def test_retrieve_credentials(self, mock_get_dec_creds):
        creds = {'super': 'secret'}
        mock_get_dec_creds.return_value = creds

        value = self.datastore.retrieve_credentials(
            ['test123'], 'gce', 'user1'
        )
        assert creds == value['test123']

    def test_encrypt_credentials(self):
        # Test creds as bytes encode error is caught and passed
        self.datastore._encrypt_credentials(b'{"test": "creds"}')

    @patch.object(CredentialsDatastore, '_clean_old_keys')
    def test_handle_key_rotation_result(self, mock_clean_old_keys):
        # Test exception case
        event = MagicMock()
        event.exception = 'Broken!'

        self.datastore._handle_key_rotation_result(event)
        self.log_callback.error.assert_called_once_with(
            'Key rotation did not finish successfully.'
            ' Old key will remain in key file.'
        )

        # Test success
        event.exception = None
        self.log_callback.reset_mock()

        self.datastore._handle_key_rotation_result(event)
        mock_clean_old_keys.assert_called_once_with()
        self.log_callback.info.assert_called_once_with(
            'Key rotation finished.'
        )

    def test_clean_old_keys(self):
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.readline.return_value = 'test-key123'
            file_handle.truncate.side_effect = Exception('unable to remove keys')

            self.datastore._clean_old_keys()

        self.log_callback.error.assert_called_once_with(
            'Unable to clean old keys from ../data/encryption_keys:'
            ' unable to remove keys.'
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

            self.log_callback.info.assert_called_once_with(
                'Starting key rotation with keys file {0} '
                'in directory {1}.'.format(
                    keys_file, creds_dir
                )
            )
            self.log_callback.error.assert_called_once_with(
                'Failed key rotation on credential file {0}:'
                ' InvalidToken: '.format(
                    os.path.join(creds_dir, 'invalid.creds')
                )
            )

    @patch('mash.services.credentials.datastore.os')
    def test_store_encrypted_credentials(self, mock_os):
        mock_os.isdir.return_value = True

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.side_effect = Exception('Cannot write file')

            self.datastore._store_encrypted_credentials(
                'account1', 'encrypted_secrets', 'ec2', 'user1'
            )
            self.log_callback.info.assert_called_once_with(
                'Storing credentials for account: account1, '
                'cloud: ec2, user: user1.'
            )
            self.log_callback.error.assert_called_once_with(
                'Unable to store credentials: Cannot write file.'
            )

    @patch('mash.services.credentials.datastore.os')
    @patch.object(CredentialsDatastore, '_get_credentials_file_path')
    def test_check_credentials_exist(self, mock_get_creds_path, mock_os):
        mock_get_creds_path.return_value = 'creds.path'
        mock_os.path.exists.return_value = True
        assert self.datastore._check_credentials_exist('acnt1', 'aws', 'user1')

    def test_decrypt_credentials(self):
        credentials = (
            'gAAAAABbFapolPqpWrLf5rpEj2xyFLkXlwclSQH-_t3tuJnACyRvOxLdw9qR'
            '3kKMBlz3XIrGH9GJdiA9IJl9y_iQLeCfIAM_4ckDMcYHMLe0WWNnsn4zj9E='
        )

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.readlines.return_value = [
                'XxgkVrKyG9gZqdvbycZgaSZF1Ro0Vr8DBMXjBuc4uRo='
            ]

            result = self.datastore._decrypt_credentials(credentials)

        assert result == 'some fake credentials'

        credentials = (
            b'gAAAAABbFapolPqpWrLf5rpEj2xyFLkXlwclSQH-_t3tuJnACyRvOxLdw9qR'
            b'3kKMBlz3XIrGH9GJdiA9IJl9y_iQLeCfIAM_4ckDMcYHMLe0WWNnsn4zj9E='
        )

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.readlines.return_value = [
                'XxgkVrKyG9gZqdvbycZgaSZF1Ro0Vr8DBMXjBuc4uRo='
            ]

            self.datastore._decrypt_credentials(credentials)

    @patch.object(CredentialsDatastore, '_decrypt_credentials')
    @patch.object(CredentialsDatastore, '_get_credentials_file_path')
    def test_get_decrypted_credentials(self, mock_get_creds_path, mock_dec_creds):
        mock_get_creds_path.return_value = 'creds.path'
        mock_dec_creds.return_value = '{"super": "secret"}'

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.return_value = 'encrypted_creds'

            result = self.datastore._get_decrypted_credentials(
                'acnt1', 'ec2', 'user1'
            )

            assert result['super'] == 'secret'
