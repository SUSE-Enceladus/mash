import json

from mash.services.credentials.azure_account import AzureAccount


class TestAzureAccount(object):
    def setup(self):
        message = {
            'account_name': 'acnt123',
            'group': 'group123',
            'provider': 'azure',
            'region': 'southcentralus',
            'requesting_user': 'user2',
            'source_resource_group': 'rg-1',
            'source_container': 'container1',
            'source_storage_account': 'sa1',
            'destination_resource_group': 'rg-2',
            'destination_container': 'container2',
            'destination_storage_account': 'sa2'
        }
        self.azure_account = AzureAccount(message)

    def test_add_multiple_accounts(self):
        with open('../data/accounts.json') as f:
            accounts = json.load(f)

        self.azure_account.add_account(accounts)

        account = accounts['azure']['accounts']['user2']['acnt123']
        assert account['region'] == 'southcentralus'
        assert account['source_container'] == 'container1'
        assert account['source_resource_group'] == 'rg-1'
        assert account['source_storage_account'] == 'sa1'
        assert account['destination_container'] == 'container2'
        assert account['destination_resource_group'] == 'rg-2'
        assert account['destination_storage_account'] == 'sa2'

        group = accounts['azure']['groups']['user2']['group123']
        assert 'acnt123' in group
