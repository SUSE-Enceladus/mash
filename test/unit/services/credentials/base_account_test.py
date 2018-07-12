import json

from mash.services.credentials.base_account import BaseAccount


class TestBaseAccount(object):
    def setup(self):
        self.account = BaseAccount(
            'acnt123', 'ec2', 'user3', group_name='group123'
        )

    def test_add_account(self):
        self.account.add_account({'test': 'data'})

    def test_add_multiple_accounts(self):
        with open('../data/accounts.json') as accounts_file:
            accounts = json.load(accounts_file)

        # Test user with no groups
        self.account.add_account_to_group(accounts)
        assert accounts['ec2']['groups']['user3']['group123'] == ['acnt123']

        # Test user with existing group
        self.account.requesting_user = 'user2'
        self.account.group_name = 'test'
        self.account.add_account_to_group(accounts)
        assert accounts['ec2']['groups']['user2']['test'] == [
            'test-aws-gov', 'test-aws', 'acnt123'
        ]
