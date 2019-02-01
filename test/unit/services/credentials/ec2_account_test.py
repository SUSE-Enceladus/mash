import json

from mash.services.credentials.ec2_account import EC2Account


class TestEC2Account(object):
    def setup(self):
        message = {
            'account_name': 'acnt123',
            'partition': 'aws',
            'cloud': 'ec2',
            'requesting_user': 'user2'
        }
        self.account = EC2Account(message)

    def test_add_multiple_accounts(self):
        with open('../data/accounts.json') as f:
            accounts = json.load(f)

        self.account.add_account(accounts)

        ec2_account = accounts['ec2']['accounts']['user2']['acnt123']
        assert ec2_account['partition'] == 'aws'
        assert ec2_account['additional_regions'] is None
