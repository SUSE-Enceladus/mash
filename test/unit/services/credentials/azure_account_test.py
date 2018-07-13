import json

from mash.services.credentials.azure_account import AzureAccount


class TestAzureAccount(object):
    def setup(self):
        message = {
            'account_name': 'acnt123',
            'container_name': 'container1',
            'group': 'group123',
            'provider': 'azure',
            'region': 'southcentralus',
            'requesting_user': 'user2',
            'resource_group': 'rgroup1',
            'storage_account': 'sa_12'
        }
        self.azure_account = AzureAccount(message)

    def test_add_multiple_accounts(self):
        with open('../data/accounts.json') as f:
            accounts = json.load(f)

        self.azure_account.add_account(accounts)

        account = accounts['azure']['accounts']['user2']['acnt123']
        assert account['container_name'] == 'container1'
        assert account['region'] == 'southcentralus'
        assert account['resource_group'] == 'rgroup1'
        assert account['storage_account'] == 'sa_12'

        group = accounts['azure']['groups']['user2']['group123']
        assert 'acnt123' in group
