import io
import pytest
import os

from tempfile import TemporaryDirectory
from unittest.mock import call, MagicMock, patch

from mash.services.credentials.key_rotate import clean_old_keys, rotate_key
from mash.mash_exceptions import MashCredentialsException


def test_clean_old_keys():
    log_callback = MagicMock()

    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value = MagicMock(spec=io.IOBase)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.readline.return_value = 'test-key123'
        file_handle.truncate.side_effect = Exception('unable to remove keys')

        clean_old_keys('/tmp/keys.file', log_callback)

    log_callback.assert_called_once_with(
        'Unable to clean old keys from /tmp/keys.file:'
        ' unable to remove keys.',
        success=False
    )


def test_rotate_key():
    with TemporaryDirectory() as test_dir:
        creds_dir = os.path.join(test_dir, 'creds')
        keys_file = os.path.join(test_dir, 'keys.file')

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

        log_callback = MagicMock()

        with pytest.raises(MashCredentialsException) as error:
            rotate_key(creds_dir, keys_file, log_callback)

        assert str(error.value) == \
            'All credentials files have not been rotated.'

        log_callback.assert_has_calls([
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
        ]),
