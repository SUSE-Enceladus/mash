# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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

import json

from mash.services.status_levels import FAILED, SUCCESS


def get_testing_account(account_info):
    return account_info.get('testing_account', account_info['account'])


def process_test_result(status, result, log_callback, region, status_msg):
    if 'tests' in result:
        status_msg['test_results'] = json.dumps({
            'tests': result['tests'],
            'summary': result['summary']
        })

    if 'results_file' in result.get('info', {}):
        log_callback.info(
            'Results file for {0} region: {1}'.format(
                region,
                result['info']['results_file']
            )
        )

    if status != 0:
        log_callback.warning(
            'Image tests failed in region: {0}.'.format(region)
        )
        if result.get('msg'):
            log_callback.error(result['msg'])

        return FAILED

    return SUCCESS
