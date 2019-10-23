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

from threading import Thread

from mash.services.testing.img_proof_helper import img_proof_test
from mash.services.status_levels import FAILED, SUCCESS


def get_testing_account(account_info):
    return account_info.get('testing_account', account_info['account'])


def create_testing_thread(results, img_proof_kwargs):
    process = Thread(
        target=img_proof_test,
        args=(results,),
        kwargs=img_proof_kwargs
    )
    process.start()

    return process


def process_test_result(result, log_callback, region):
    if 'results_file' in result:
        log_callback(
            'Results file for {0} region: {1}'.format(
                region, result['results_file']
            )
        )

    if result['status'] != SUCCESS:
        log_callback(
            'Image tests failed in region: {0}.'.format(region),
            success=False
        )
        if result.get('msg'):
            log_callback(result['msg'], success=False)

        return FAILED

    return SUCCESS
