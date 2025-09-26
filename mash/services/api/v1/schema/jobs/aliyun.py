# Copyright (c) 2021 SUSE LLC.  All rights reserved.
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

from mash.services.api.v1.schema import string_with_example
from mash.services.api.v1.schema.jobs import base_job_message

aliyun_job_message = copy.deepcopy(base_job_message)
aliyun_job_message['properties']['platform'] = string_with_example(
    'OpenSUSE',
    description='The distribution of the image operating system.'
)
aliyun_job_message['properties']['launch_permission'] = string_with_example(
    'EXAMPLE',
    description='The launch permission to set for the published image.'
)
aliyun_job_message['properties']['cloud_account'] = string_with_example(
    'account1',
    description='The name of the cloud account to use for image '
                'publishing.'
)
aliyun_job_message['properties']['bucket'] = string_with_example(
    'images',
    description='The name of the storage bucket to use for uploading the '
                'qcow2 image.'
)
aliyun_job_message['properties']['region'] = string_with_example(
    'cn-beijing',
    description='The region to use for launching and testing an instance '
                'of the image.'
)
aliyun_job_message['properties']['security_group_id'] = string_with_example(
    'sg1',
    description='The security group to use when launching the test instance.'
)
aliyun_job_message['properties']['vswitch_id'] = string_with_example(
    'vs1',
    description='The vswitch to use when launching the test instance.'
)
aliyun_job_message['properties']['disk_size'] = {
    'type': 'integer',
    'minimum': 5,
    'example': 20,
    'description': 'Size root disk in GB. Default is 20GB. '
}
aliyun_job_message['properties']['nvme_support'] = {
    'type': 'boolean',
    'description': 'Whether the image supports nvme storage or not.'
}
aliyun_job_message['required'].append('cloud_account')
aliyun_job_message['required'].append('platform')
aliyun_job_message['required'].append('launch_permission')
aliyun_job_message['properties']['image']['example'] = 'openSUSE-Leap-15.0-GCE'
aliyun_job_message['properties']['cloud_image_name']['example'] = \
    'opensuse-leap-15-v{date}'
aliyun_job_message['properties']['old_cloud_image_name']['example'] = \
    'opensuse-leap-15-v20190520'
aliyun_job_message['properties']['image_description']['example'] = \
    'openSUSE Leap 15'
aliyun_job_message['properties']['instance_type']['example'] = 'ecs.t5-lc1m1.small'
