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

from img_proof.ipa_controller import test_image

from mash.services.status_levels import FAILED, SUCCESS


def img_proof_test(
    cloud=None, access_key_id=None, description=None, distro=None,
    image_id=None, instance_type=None, img_proof_timeout=None, region=None,
    secret_access_key=None, security_group_id=None, service_account_file=None,
    ssh_key_name=None, ssh_private_key_file=None, ssh_user=None, subnet_id=None,
    tests=None, availability_domain=None, compartment_id=None, tenancy=None,
    oci_user_id=None, signing_key_file=None, signing_key_fingerprint=None,
    boot_firmware=None, image_project=None, log_callback=None, sev_capable=None,
    access_key=None, access_secret=None, vswitch_id=None, use_gvnic=None
):
    if boot_firmware and boot_firmware == 'uefi':
        enable_secure_boot = True
    else:
        enable_secure_boot = False

    status, result = test_image(
        cloud,
        access_key_id=access_key_id,
        availability_domain=availability_domain,
        cleanup=True,
        compartment_id=compartment_id,
        description=description,
        distro=distro,
        image_id=image_id,
        instance_type=instance_type,
        log_level=logging.DEBUG,
        oci_user_id=oci_user_id,
        region=region,
        secret_access_key=secret_access_key,
        security_group_id=security_group_id,
        service_account_file=service_account_file,
        signing_key_file=signing_key_file,
        signing_key_fingerprint=signing_key_fingerprint,
        ssh_key_name=ssh_key_name,
        ssh_private_key_file=ssh_private_key_file,
        ssh_user=ssh_user,
        subnet_id=subnet_id,
        tenancy=tenancy,
        tests=tests,
        timeout=img_proof_timeout,
        enable_secure_boot=enable_secure_boot,
        image_project=image_project,
        log_callback=log_callback,
        prefix_name='mash',
        sev_capable=sev_capable,
        access_key=access_key,
        access_secret=access_secret,
        v_switch_id=vswitch_id,
        use_gvnic=use_gvnic
    )

    status = SUCCESS if status == 0 else FAILED
    return {
        'status': status,
        'results_file': result['info']['results_file'],
        'instance_id': result['info']['instance'],
        'summary': result['summary'],
        'tests': result['tests']
    }
