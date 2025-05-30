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

import logging
import os
import random
import traceback

from mash.mash_exceptions import MashTestException
from mash.services.mash_job import MashJob
from mash.services.status_levels import EXCEPTION, SUCCESS
from mash.services.test.utils import process_test_result
from mash.utils.mash_utils import create_ssh_key_pair, create_json_file
from gceimgutils.gceutils import (
    get_region_list,
    get_regions_client
)
from gceimgutils.gceremoveblob import GCERemoveBlob
from gceimgutils.gceremoveimg import GCERemoveImage

from img_proof.ipa_controller import test_image
from img_proof.ipa_exceptions import IpaRetryableError

instance_types = {
    'X86_64': [
        'n1-standard-1',
        'n1-highmem-2',
        'n1-highcpu-2',
        'f1-micro',
    ],
    'ARM64': [
        't2a-standard-2'
    ]
}


class GCETestJob(MashJob):
    """
    Class for an GCE test job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.bucket = self.job_config['bucket']
            self.testing_account = self.job_config['testing_account']
            self.tests = self.job_config['tests']
        except KeyError as error:
            raise MashTestException(
                'GCE test jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.description = self.job_config.get('description')
        self.distro = self.job_config.get('distro', 'sles')
        self.instance_type = self.job_config.get('instance_type')
        self.ssh_user = self.job_config.get('ssh_user', 'root')
        self.cleanup_images = self.job_config.get('cleanup_images')
        self.test_fallback_regions = self.job_config.get('test_fallback_regions')
        self.boot_firmware = self.job_config.get('boot_firmware', ['bios'])
        self.image_project = self.job_config.get('image_project')
        self.guest_os_features = self.job_config.get('guest_os_features', [])
        self.cloud_architecture = self.job_config.get(
            'cloud_architecture',
            'x86_64'
        ).replace('aarch64', 'arm64').upper()

        if 'SEV_CAPABLE' in self.guest_os_features:
            self.sev_capable = True
            self.instance_type = 'n2d-standard-2'
            self.region = 'us-east1-b'
            self.test_fallback_regions = [
                'us-central1-a',
                'us-west1-b'
            ]
        else:
            self.sev_capable = False

        if 'GVNIC' in self.guest_os_features:
            self.test_gvnic_with = random.choice(self.boot_firmware)
        else:
            self.test_gvnic_with = None

        if not self.instance_type:
            self.instance_type = random.choice(
                instance_types[self.cloud_architecture]
            )

        self.ssh_private_key_file = self.config.get_ssh_private_key_file()
        self.img_proof_timeout = self.config.get_img_proof_timeout()

        if not os.path.exists(self.ssh_private_key_file):
            create_ssh_key_pair(self.ssh_private_key_file)

    def run_job(self):
        """
        Tests image with img-proof and update status and results.
        """
        self.status = SUCCESS

        if not self.tests:
            self.log_callback.info(
                'Skipping test service, no tests provided.'
            )
            return

        accounts = [self.account]
        if self.testing_account:
            # Get both sets of credentials in case cleanup method is run.
            accounts.append(self.testing_account)

        self.request_credentials(accounts)
        credentials = self.credentials[self.testing_account or self.account]
        project = credentials.get('project_id')
        regions_client = get_regions_client(credentials)

        if self.test_fallback_regions == []:
            # fallback testing explicitly disabled
            fallback_regions = set()
        elif self.test_fallback_regions is None:
            try:
                fallback_regions = get_region_list(regions_client, project)
            except Exception:
                fallback_regions = set()  # Unable to retrieve region list
        else:
            fallback_regions = set(self.test_fallback_regions)

        fallback_regions.add(self.region)

        self.cloud_image_name = self.status_msg['cloud_image_name']

        with create_json_file(credentials) as auth_file:
            for firmware in self.boot_firmware:
                self.log_callback.info(
                    'Running img-proof tests against image with '
                    'type: {inst_type}. Using boot firmware setting: '
                    '{firmware}.'.format(
                        inst_type=self.instance_type,
                        firmware=firmware
                    )
                )

                if self.test_gvnic_with == firmware:
                    test_gvnic = True
                else:
                    test_gvnic = False

                enable_secure_boot = True if firmware == 'uefi' else False

                retry_region = self.region
                while fallback_regions:
                    try:
                        exit_status, result = test_image(
                            self.cloud,
                            cleanup=True,
                            description=self.description,
                            distro=self.distro,
                            image_id=self.cloud_image_name,
                            instance_type=self.instance_type,
                            timeout=self.img_proof_timeout,
                            log_level=logging.DEBUG,
                            region=retry_region,
                            service_account_file=auth_file,
                            ssh_private_key_file=self.ssh_private_key_file,
                            ssh_user=self.ssh_user,
                            tests=self.tests,
                            enable_secure_boot=enable_secure_boot,
                            image_project=self.image_project,
                            log_callback=self.log_callback,
                            prefix_name='mash',
                            sev_capable=self.sev_capable,
                            use_gvnic=test_gvnic,
                            architecture=self.cloud_architecture
                        )
                    except IpaRetryableError as error:
                        exit_status = 1
                        result = {
                            'status': EXCEPTION,
                            'msg': str(error)
                        }
                        fallback_regions.remove(retry_region)

                        if fallback_regions:
                            retry_region = random.choice(list(fallback_regions))
                    except Exception as error:
                        self.add_error_msg(str(error))
                        exit_status = 1
                        result = {
                            'status': EXCEPTION,
                            'msg': str(traceback.format_exc())
                        }
                        break
                    else:
                        break

                self.status = process_test_result(
                    exit_status,
                    result,
                    self.log_callback,
                    self.region,
                    self.status_msg
                )

                if self.status != SUCCESS:
                    self.add_error_msg(
                        'Image failed img-proof test suite. '
                        'See "mash job test-results --job-id {GUID} -v" '
                        'for details on the failing tests.'
                    )
                    break

        if self.cleanup_images or \
                (self.status != SUCCESS and self.cleanup_images is not False):
            self.cleanup_image()

    def cleanup_image(self):
        credentials = self.credentials[self.account]
        project = credentials.get('project_id')
        object_name = self.status_msg['object_name']

        self.log_callback.info(
            'Cleaning up image: {0} in region: {1}.'.format(
                self.cloud_image_name,
                self.region
            )
        )

        try:
            remover = GCERemoveImage(
                image_name=self.cloud_image_name,
                credentials_info=credentials,
                project=project,
                log_callback=self.log_callback
            )
            remover.remove_image(self.cloud_image_name)
            remover = GCERemoveBlob(
                object_name,
                self.bucket,
                credentials_info=credentials,
                project=project,
                log_callback=self.log_callback
            )
            remover.remove_blob()
        except Exception as error:
            msg = 'Failed to cleanup image: {0}'.format(error)
            self.log_callback.warning(msg)
            self.add_error_msg(msg)
