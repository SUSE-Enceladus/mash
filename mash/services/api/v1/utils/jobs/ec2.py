# Copyright (c) 2019 SUSE LLC.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#

import copy

from flask import current_app

from mash.mash_exceptions import MashJobException
from mash.services.api.v1.utils.accounts.ec2 import (
    get_accounts_in_ec2_group,
    get_ec2_account
)
from mash.services.api.v1.utils.jobs import validate_job


def get_ec2_regions_by_partition(partition):
    """
    Get EC2 regions from config file based on partition.
    """
    regions = copy.deepcopy(
        current_app.config['CLOUD_DATA']['ec2']['regions'][partition]
    )
    return regions


def get_ec2_helper_images():
    """
    Get helper image data for EC2 from config file.
    """
    helper_images = copy.deepcopy(
        current_app.config['CLOUD_DATA']['ec2']['helper_images']
    )
    return helper_images


def add_target_ec2_account(
    account,
    accounts,
    cloud_accounts,
    helper_images,
    use_root_swap=None,
    skip_replication=False
):
    """
    Update job with account information.

    - Append any additional regions
    - Update ami for root swap if use_root_swap set
    """
    job_doc_data = cloud_accounts.get(account['name'], {})
    region_name = job_doc_data.get('region') or account.get('region')
    subnet = job_doc_data.get('subnet') or account.get('subnet')

    if skip_replication:
        regions = [region_name]
        if account.get('additional_regions'):  # In case an additional region is used
            for region in account['additional_regions']:
                helper_images[region['name']] = region['helper_image']
    else:
        regions = get_ec2_regions_by_partition(account['partition'])
        if account.get('additional_regions'):
            for region in account['additional_regions']:
                helper_images[region['name']] = region['helper_image']
                regions.append(region['name'])

    if use_root_swap:
        try:
            helper_image = job_doc_data['root_swap_ami']
        except KeyError:
            raise MashJobException(
                'root_swap_ami is required for account {0},'
                ' when using root swap.'.format(account['name'])
            )
    else:
        helper_image = helper_images[region_name]

    accounts[region_name] = {
        'account': account['name'],
        'partition': account['partition'],
        'target_regions': list(set(regions)),  # Remove any duplicates
        'helper_image': helper_image,
        'subnet': subnet
    }


def convert_account_dict(accounts):
    """
    Create a dictionary of accounts by account name.
    """
    cloud_accounts = {}

    for account in accounts:
        cloud_accounts[account['name']] = account

    return cloud_accounts


def validate_mp_fields(job_doc):
    mp_fields = [
        'entity_id',
        'version_title',
        'release_notes',
        'access_role_arn',
        'os_name',
        'os_version',
        'usage_instructions',
        'recommended_instance_type'
    ]
    missing_mp_fields = []

    for field in mp_fields:
        if not job_doc.get(field):
            missing_mp_fields.append(field)

    if missing_mp_fields:
        raise MashJobException(
            'The following fields are required to publish a marketplace '
            'image and are missing in the job doc: {fields}'.format(
                fields=', '.join(missing_mp_fields)
            )
        )


def validate_ec2_job(job_doc):
    """
    Validate job.

    Update target_account_info for given job doc.

    Once accounts dictionary is built remove cloud_groups
    and cloud_accounts keys from job_doc.
    """
    if job_doc.get('publish_in_marketplace'):
        job_doc['last_service'] = 'publish'  # No deprecation for MP images
        job_doc['skip_replication'] = True  # No replication for MP images
        validate_mp_fields(job_doc)

    job_doc = validate_job(job_doc)

    user_id = job_doc['requesting_user']

    helper_images = get_ec2_helper_images()
    cloud_accounts = convert_account_dict(job_doc.get('cloud_accounts', []))

    accounts = {}
    target_accounts = []

    if job_doc.get('cloud_account'):
        account_name = job_doc['cloud_account']
        cloud_account = get_ec2_account(account_name, user_id)
        target_accounts.append(cloud_account)

    for group_name in job_doc.get('cloud_groups', []):
        group_accounts = get_accounts_in_ec2_group(group_name, user_id)
        target_accounts += group_accounts

    for account_name in cloud_accounts:
        cloud_account = get_ec2_account(account_name, user_id)
        target_accounts.append(cloud_account)

    for account in target_accounts:
        if account['name'] not in accounts:
            add_target_ec2_account(
                account,
                accounts,
                cloud_accounts,
                helper_images,
                job_doc.get('use_root_swap'),
                job_doc.get('skip_replication', False)
            )

    if 'cloud_groups' in job_doc:
        del job_doc['cloud_groups']

    if 'cloud_account' in job_doc:
        del job_doc['cloud_account']

    if 'cloud_accounts' in job_doc:
        del job_doc['cloud_accounts']

    job_doc['target_account_info'] = accounts

    return job_doc
