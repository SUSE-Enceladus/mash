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
# import random
import traceback

from mash.mash_exceptions import MashTestException
from mash.services.mash_job import MashJob
from mash.services.status_levels import EXCEPTION, SUCCESS
from mash.services.test.utils import (
    get_testing_account,
    process_test_result
)
from mash.services.test.ec2_test_utils import (
    get_instance_feature_combinations,
    select_instances_for_tests,
    get_partition_test_regions
)
from mash.utils.mash_utils import create_ssh_key_pair
from mash.utils.ec2 import (
    # setup_ec2_networking,
    wait_for_instance_termination,
    cleanup_ec2_image
)
from img_proof.ipa_controller import test_image


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

        self.partitions = get_partition_test_regions(self.test_regions)
        if not self.partitions:
            msg = (
                'At least one partition is required for tests.'
                'Please, configure the test_regions for the aws account in'
                'mash database through the mash CLI tool.'
            )
            if self.log_callback:
                self.log_callback.error(msg)
            raise MashTestException(msg)

        self.cloud_architecture = self.job_config.get(
            'cloud_architecture', 'x86_64'
        )
        self.boot_firmware = self.job_config.get(
            'boot_firmware',
            ['uefi-preferred']
        )
        self.cpu_options = self.job_config.get('cpu_options', {})
        self.instance_catalog = self.config.get_test_ec2_instance_catalog()

        # Get all account credentials in one request
        accounts = []
        for region, info in self.test_regions.items():
            account = get_testing_account(info)
            if account not in accounts:
                accounts.append(account)
        self.request_credentials(accounts)

        # Feature combinations are common for all partitions
        self.feature_combinations = get_instance_feature_combinations(
            self.cloud_architecture,
            self.boot_firmware,
            self.cpu_options,
            logger=self.log_callback
        )

        # mash will try to test all the possible features supported in the
        # available test regions for each partition
        for partition, test_regions in self.partitions:

            instance_types = select_instances_for_tests(
                test_regions=test_regions,
                instance_catalog=self.instance_catalog,
                feature_combinations=self.feature_combinations,
                logger=self.log_callback
            )

            if not instance_types:
                # There are no instance types configured in the test regions
                # for the partition that can cover a single feat combination
                msg = (
                    'Configuration error. No instances in the instance '
                    f'catalog for {partition} partition can cover this feature'
                    f'combination: {self.feature_combinations}'
                )
                if self.log_callback:
                    self.log_callback.error(msg)
                raise MashTestException(msg)

            for instance_type in instance_types:
                if self.log_callback:
                    self.log_callback.info(
                        'Running img-proof tests for image in {part} with '
                        'instance type: {inst_type}.'.format(
                            part=partition,
                            inst_type=instance_type
                        )
                    )

            region = instance_type.get('region')
            account = get_testing_account(self.test_regions[region])
            credentials = self.credentials[account]

            # with setup_ec2_networking(
            #    credentials['access_key_id'],
            #    region,
            #    credentials['secret_access_key'],
            #    self.ssh_private_key_file,
            #    subnet_id=info.get('subnet')
            # ) as network_details:
            #     status = self.run_tests(
            #         access_key_id=credentials['access_key_id'],
            #         secret_access_key=credentials['secret_access_key'],
            #         region=region,
            #         ssh_private_key_file=self.ssh_private_key_file,
            #         subnet=info.get('subnet'),
            #         cloud=self.cloud,
            #         description=self.description,
            #         distro=self.distro,
            #         image_id=self.status_msg['source_regions'][region],
            #         instance_type=instance_type,
            #         img_proof_timeout=self.img_proof_timeout,
            #         ssh_user=self.ssh_user,
            #         tests=self.tests,
            #         log_callback=self.log_callback,
            #         network_details=network_details
            #     )
            #     if status != SUCCESS:
            #         self.status = status
            #         self.add_error_msg(
            #             'Image failed img-proof test suite. '
            #             'See "mash job test-results --job-id {GUID} -v" '
            #             'for details on the failing tests.'
            #         )
            #         break  # Fail eagerly, if the image fails in any partition.

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
        network_details
    ):
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
                prefix_name='mash'
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
