# Copyright (c) 2023 SUSE LLC.  All rights reserved.
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
from mash.services.test.utils import (
    get_testing_account,
    process_test_result
)
from mash.utils.mash_utils import create_ssh_key_pair
from mash.utils.ec2 import (
    setup_ec2_networking,
    wait_for_instance_termination,
    cleanup_ec2_image
)
from img_proof.ipa_controller import test_image

instance_types = {
    'hybrid': [
        'c5.large',
        'm5.large',
        't3.small'
    ],
    'hybrid-sev': [
    ],
    'bios': [
        'i3.large',
        't2.small'
    ],
    'bios-sev': [
    ],
    'aarch64': [
        't4g.small',
        'm6g.medium'
    ]
}

sev_capable_regions = [
    'us-east-1'
]


class EC2TestJob(MashJob):
    """
    Class for an EC2 test job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.test_regions = self.job_config['test_regions']
            self.tests = self.job_config['tests']
        except KeyError as error:
            raise MashTestException(
                'EC2 test jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.cleanup_images = self.job_config.get('cleanup_images')
        self.description = self.job_config.get('description')
        self.distro = self.job_config.get('distro', 'sles')
        self.instance_type = self.job_config.get('instance_type')
        self.ssh_user = self.job_config.get('ssh_user', 'ec2-user')
        self.cloud_architecture = self.job_config.get(
            'cloud_architecture', 'x86_64'
        )
        self.boot_firmware = self.job_config.get(
            'boot_firmware',
            ['uefi-preferred']
        )[0]

        self.ssh_private_key_file = self.config.get_ssh_private_key_file()
        self.img_proof_timeout = self.config.get_img_proof_timeout()

        if not os.path.exists(self.ssh_private_key_file):
            create_ssh_key_pair(self.ssh_private_key_file)
        self.guest_os_features = self.job_config.get('guest_os_features', [])

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

        # Get all account credentials in one request
        accounts = []
        for region, info in self.test_regions.items():
            accounts.append(get_testing_account(info))

        self.request_credentials(accounts)

        for region, info in self.test_regions.items():

            if info['partition'] in ('aws-cn', 'aws-us-gov') and \
                    self.cloud_architecture == 'aarch64':
                # Skip test aarch64 images in China and GovCloud.
                # There are no aarch64 based instance types available.
                continue

            if all([
                info['partition'] == 'aws',
                'SEV_CAPABLE' in self.guest_os_features,
                region in sev_capable_regions,
                self.cloud_architecture == 'x86_64'
            ]):
                self.sev_capable = True
            else:
                self.sev_capable = False

            test_instance_types = self.select_instance_types(
                cloud_arch=self.cloud_architecture,
                boot_firmware=self.boot_firmware,
                sev_capable=self.sev_capable
            )

            account = get_testing_account(info)
            credentials = self.credentials[account]

            with setup_ec2_networking(
                credentials['access_key_id'],
                region,
                credentials['secret_access_key'],
                self.ssh_private_key_file,
                subnet_id=info.get('subnet')
            ) as network_details:

                for instance_type in test_instance_types:
                    self.log_callback.info(
                        'Running img-proof tests in {region} against image '
                        'with type: {inst_type}.'.format(
                            region=region,
                            inst_type=instance_type
                        )
                    )

                    status = self.run_tests(
                        access_key_id=credentials['access_key_id'],
                        secret_access_key=credentials['secret_access_key'],
                        region=region,
                        ssh_private_key_file=self.ssh_private_key_file,
                        subnet=info.get('subnet'),
                        cloud=self.cloud,
                        description=self.description,
                        distro=self.distro,
                        image_id=self.status_msg['source_regions'][region],
                        instance_type=instance_type,
                        img_proof_timeout=self.img_proof_timeout,
                        ssh_user=self.ssh_user,
                        tests=self.tests,
                        log_callback=self.log_callback,
                        network_details=network_details,
                        sev_capable=self.sev_capable
                    )

                    if status != SUCCESS:
                        self.status = status
                        self.add_error_msg(
                            'Image failed img-proof test suite. '
                            'See "mash job test-results --job-id {GUID} -v" '
                            'for details on the failing tests.'
                        )
                        break  # Fail eagerly, if the image fails in any partition.

        if self.cleanup_images or (self.status != SUCCESS and self.cleanup_images is not False):  # noqa
            for region, info in self.test_regions.items():
                credentials = self.credentials[info['account']]

                cleanup_ec2_image(
                    credentials['access_key_id'],
                    credentials['secret_access_key'],
                    self.log_callback,
                    region,
                    image_id=self.status_msg['source_regions'][region]
                )

    def run_tests(
        self,
        access_key_id,
        secret_access_key,
        region,
        ssh_private_key_file,
        subnet,
        cloud,
        description,
        distro,
        image_id,
        instance_type,
        img_proof_timeout,
        ssh_user,
        tests,
        log_callback,
        network_details,
        sev_capable
    ):
        # set cpu_options if image is sev_capable
        cpu_options = {}
        if sev_capable:
            cpu_options = {
                'AmdSevSnp': 'enabled'
            }

        try:
            exit_status, result = test_image(
                cloud,
                access_key_id=access_key_id,
                cleanup=True,
                description=description,
                distro=distro,
                image_id=image_id,
                instance_type=instance_type,
                timeout=img_proof_timeout,
                log_level=logging.DEBUG,
                region=region,
                secret_access_key=secret_access_key,
                security_group_id=network_details['security_group_id'],
                ssh_key_name=network_details['ssh_key_name'],
                ssh_private_key_file=ssh_private_key_file,
                ssh_user=ssh_user,
                subnet_id=network_details['subnet_id'],
                tests=tests,
                log_callback=log_callback,
                prefix_name='mash',
                cpu_options=cpu_options
            )
        except Exception as error:
            self.add_error_msg(str(error))
            exit_status = 1
            result = {
                'status': EXCEPTION,
                'msg': str(traceback.format_exc())
            }

        status = process_test_result(
            exit_status,
            result,
            log_callback,
            region,
            self.status_msg
        )

        instance_id = result.get('info', {}).get('instance', None)
        if instance_id:
            # Wait until instance is terminated to exit
            # context manager and cleanup resources.
            wait_for_instance_termination(
                access_key_id,
                instance_id,
                region,
                secret_access_key
            )

        return status

    def select_instance_types(
        self,
        cloud_arch,
        boot_firmware,
        sev_capable
    ) -> list:
        '''Selects the instance_types array for the tests'''

        if self.cloud_architecture == 'aarch64':
            return [random.choice(instance_types['aarch64'])]

        if self.instance_type:
            return [self.instance_type]

        if not sev_capable:
            if self.boot_firmware == 'uefi-preferred':
                return [
                    random.choice(instance_types['bios']),
                    random.choice(instance_types['hybrid'])
                ]
            else:
                return [
                    random.choice(instance_types['hybrid'])
                ]
        else:
            if self.boot_firmware == 'uefi-preferred':
                return [
                    random.choice(instance_types['bios-sev']),
                    random.choice(instance_types['hybrid-sev'])
                ]
            else:
                return [
                    random.choice(instance_types['hybrid-sev'])
                ]
