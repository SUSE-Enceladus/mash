import io

from apscheduler.schedulers.background import BackgroundScheduler
from unittest.mock import call, MagicMock, Mock, patch

from mash.services.credentials.account_datastore import AccountDatastore
from mash.utils.json_format import JsonFormat


class TestAccountDatastore(object):

    @patch('mash.services.credentials.account_datastore.BackgroundScheduler')
    @patch('mash.services.credentials.account_datastore.os')
    def setup(self, mock_os, mock_scheduler):
        log_callback = Mock()
        scheduler = MagicMock(BackgroundScheduler)

        mock_os.path.exists.return_value = False
        mock_scheduler.return_value = scheduler

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.datastore = AccountDatastore(
                '../data/accounts.json', '/var/lib/mash/credentials/',
                '../data/encryption_keys', log_callback
            )
            file_handle = mock_open.return_value.__enter__.return_value
            assert file_handle.write.call_count == 2

    @patch('mash.services.credentials.account_datastore.os')
    def test_datastore_add_account(self, mock_os):
        mock_os.path.isdir.return_value = False

        account_info = {
            'partition': 'aws',
            'region': 'us-east-1',
            'additional_regions': None,
            'group': 'group1'
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
                account_info, 'ec2', 'acnt123', 'user1', {'creds': 'data'}
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
