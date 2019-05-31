import json
import pytest
import yaml

from mash.mash_exceptions import MashJobCreatorException
from mash.services.jobcreator.ec2_job import EC2Job


def test_ec2_job_missing_root_swap_ami():
    with open('../data/mash_config.yaml') as f:
        cloud_data = yaml.load(f)['cloud']['ec2']

    with open('../data/accounts.json') as f:
        account = json.load(f)['ec2']['accounts']['user2']['test-aws']

    accounts_info = {'test-aws': account}

    with pytest.raises(MashJobCreatorException):
        EC2Job(
            accounts_info, cloud_data, {
                'job_id': '123',
                'cloud': 'ec2',
                'cloud_accounts': [{'name': 'test-aws'}],
                'requesting_user': 'user2',
                'last_service': 'deprecation',
                'utctime': 'now',
                'image': 'test-image',
                'cloud_image_name': 'test-cloud-image',
                'image_description': 'image description',
                'distro': 'sles',
                'download_url': 'https://download.here',
                'use_root_swap': True
            }
        )

    EC2Job(
        accounts_info, cloud_data, {
            'job_id': '123',
            'cloud': 'ec2',
            'cloud_accounts': [{
                'name': 'test-aws',
                'root_swap_ami': 'ami-1234567890'
            }],
            'requesting_user': 'user2',
            'last_service': 'deprecation',
            'utctime': 'now',
            'image': 'test-image',
            'cloud_image_name': 'test-cloud-image',
            'image_description': 'image description',
            'distro': 'sles',
            'download_url': 'https://download.here',
            'use_root_swap': True
        }
    )
