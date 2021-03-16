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

from unittest.mock import patch, Mock

from mash.services.api.utils.jobs.aliyun import validate_aliyun_job

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.utils.jobs.aliyun.get_aliyun_account')
def test_update_aliyun_job_accounts(
    mock_get_aliyun_account, mock_get_current_obj
):
    account = {
        'name': 'acnt1',
        'region': 'cn-beijing',
        'bucket': 'images',
        'security_group_id': 'sg1',
        'vswitch_id': 'vs1'
    }
    mock_get_aliyun_account.return_value = account

    app = Mock()
    app.config = {
        'SERVICE_NAMES': [
            'obs',
            'upload',
            'create',
            'test',
            'raw_image_upload',
            'replicate',
            'publish',
            'deprecate'
        ]
    }
    mock_get_current_obj.return_value = app

    job_doc = {
        'last_service': 'test',
        'requesting_user': '1',
        'cloud_account': 'acnt1',
        'bucket': 'images2',
        'cloud_image_name': 'Test OEM Image',
        'image_description': 'Description of an image',
        'platform': 'SUSE'
    }

    result = validate_aliyun_job(job_doc)

    assert result['region'] == 'cn-beijing'
    assert result['bucket'] == 'images2'
    assert result['security_group_id'] == 'sg1'
    assert result['vswitch_id'] == 'vs1'
