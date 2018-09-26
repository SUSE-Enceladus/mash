import json

from mash.services.credentials.gce_account import GCEAccount


class TestGCEAccount(object):
    def setup(self):
        message = {
            'account_name': 'acnt123',
            'bucket': 'images',
            'group': 'group123',
            'provider': 'gce',
            'region': 'us-west1',
            'requesting_user': 'user2'
        }
        self.gce_account = GCEAccount(message)

    def test_add_multiple_accounts(self):
        with open('../data/accounts.json') as f:
            accounts = json.load(f)

        self.gce_account.add_account(accounts)

        account = accounts['gce']['accounts']['user2']['acnt123']
        assert account['region'] == 'us-west1'
        assert account['bucket'] == 'images'

        group = accounts['gce']['groups']['user2']['group123']
        assert 'acnt123' in group
