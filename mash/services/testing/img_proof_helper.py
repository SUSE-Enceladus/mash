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

import logging
import traceback
import random

from img_proof.ipa_controller import test_image
from img_proof.ipa_exceptions import IpaRetryableError

from mash.services.status_levels import EXCEPTION, FAILED, SUCCESS


def img_proof_test(
    results, cloud=None, access_key_id=None, description=None, distro=None,
    image_id=None, instance_type=None, img_proof_timeout=None, region=None,
    secret_access_key=None, security_group_id=None, service_account_file=None,
    ssh_key_name=None, ssh_private_key_file=None, ssh_user=None, subnet_id=None,
    tests=None, fallback_regions=None
):
    saved_args = locals()
    result = {}
    retry_region = None

    try:
        status, result = test_image(
            cloud,
            access_key_id=access_key_id,
            cleanup=True,
            description=description,
            distro=distro,
            image_id=image_id,
            instance_type=instance_type,
            log_level=logging.WARNING,
            region=region,
            secret_access_key=secret_access_key,
            security_group_id=security_group_id,
            service_account_file=service_account_file,
            ssh_key_name=ssh_key_name,
            ssh_private_key_file=ssh_private_key_file,
            ssh_user=ssh_user,
            subnet_id=subnet_id,
            tests=tests,
            timeout=img_proof_timeout
        )
    except IpaRetryableError as error:
        if fallback_regions:
            retry_region = random.choice(fallback_regions)
            fallback_regions.remove(retry_region)
        else:
            status = FAILED
            results[region] = {
                'status': EXCEPTION, 'msg': str(error)
            }
    except Exception:
        results[region] = {
            'status': EXCEPTION, 'msg': str(traceback.format_exc())
        }
    else:
        status = SUCCESS if status == 0 else FAILED
        results[region] = {
            'status': status,
            'results_file': result['info']['results_file'],
            'instance_id': result['info']['instance']
        }
    finally:
        if retry_region:
            saved_args['region'] = retry_region
            img_proof_test(**saved_args)
            return
