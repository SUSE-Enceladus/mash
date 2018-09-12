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

import logging
import os
import threading

from ipa.ipa_controller import test_image
from tempfile import NamedTemporaryFile

from mash.csp import CSP
from mash.services.status_levels import EXCEPTION, FAILED, SUCCESS
from mash.utils.ec2 import get_client
from mash.utils.mash_utils import generate_name, get_key_from_file


def ipa_test(
    results, provider=None, access_key_id=None, description=None, distro=None,
    image_id=None, instance_type=None, region=None, secret_access_key=None,
    service_account_credentials=None, ssh_private_key_file=None, ssh_user=None,
    tests=None
):
    name = threading.current_thread().getName()
    service_account_file = None
    key_name = None

    try:
        if provider == CSP.ec2:
            key_name = generate_name()
            client = get_client(
                'ec2', access_key_id, secret_access_key, region
            )
            ssh_public_key = get_key_from_file(ssh_private_key_file + '.pub')
            client.import_key_pair(
                KeyName=key_name, PublicKeyMaterial=ssh_public_key
            )
        else:
            temp_file = NamedTemporaryFile(delete=False, mode='w+')
            temp_file.write(service_account_credentials)
            temp_file.close()
            service_account_file = temp_file.name

        status, result = test_image(
            provider,
            access_key_id=access_key_id,
            cleanup=True,
            description=description,
            distro=distro,
            image_id=image_id,
            instance_type=instance_type,
            log_level=logging.WARNING,
            region=region,
            secret_access_key=secret_access_key,
            service_account_file=service_account_file,
            ssh_key_name=key_name,
            ssh_private_key_file=ssh_private_key_file,
            ssh_user=ssh_user,
            tests=tests
        )
    except Exception as error:
        results[name] = {'status': EXCEPTION, 'msg': str(error)}
    else:
        status = SUCCESS if status == 0 else FAILED
        results[name] = {
            'status': status,
            'results_file': result['info']['results_file']
        }
    finally:
        try:
            if provider == CSP.ec2:
                client.delete_key_pair(KeyName=key_name)
            else:
                os.remove(service_account_file)
        except Exception:
            pass
