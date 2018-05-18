# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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

accounts_template = {
    'ec2': {
        'regions': {
            'aws': [
                'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3', 'ap-south-1',
                'ap-southeast-1', 'ap-southeast-2', 'ca-central-1', 'eu-central-1',
                'eu-west-1', 'eu-west-2', 'eu-west-3', 'sa-east-1', 'us-east-1',
                'us-east-2', 'us-west-1', 'us-west-2'
            ],
            'aws-cn': ['cn-north-1', 'cn-northwest-1'],
            'aws-us-gov': ['us-gov-west-1']
        },
        'groups': {},
        'accounts': {},
        'helper_images': {
            'ap-northeast-1': 'ami-383c1956',
            'ap-northeast-2': 'ami-249b554a',
            'ap-northeast-3': 'ami-82444aff',
            'ap-southeast-1': 'ami-c9b572aa',
            'ap-southeast-2': 'ami-48d38c2b',
            'ap-south-1': 'ami-a6d1bac9',
            'ca-central-1': 'ami-21d76545',
            'cn-north-1': 'ami-bcc45885',
            'cn-northwest-1': 'ami-23978241',
            'eu-central-1': 'ami-bc5b48d0',
            'eu-west-1': 'ami-bff32ccc',
            'eu-west-2': 'ami-2a676d4',
            'eu-west-3': 'ami-7bc17406',
            'sa-east-1': 'ami-6817af04',
            'us-east-1': 'ami-4b814f22',
            'us-east-2': 'ami-71ca9114',
            'us-gov-west-1': 'ami-c2b5d7e1',
            'us-west-1': 'ami-d5ea86b5',
            'us-west-2': 'ami-f0091d91'
        }
    },
    'azure': {},
    'gce': {}
}
