# Copyright (c) 2018 SUSE LLC.  All rights reserved.
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

from mash.mash_exceptions import MashConfigException
from mash.services.base_config import BaseConfig
from mash.services.test.defaults import Defaults


class TestConfig(BaseConfig):
    """
    Implements reading of test configuration from the mash
    configuration file:

    * /etc/mash/mash_config.yaml

    The mash configuration file is a yaml formatted file containing
    information to control the behavior of the mash services.
    """
    __test__ = False  # Used by pytest to ignore class in auto discovery

    def __init__(self, config_file=None):
        super(TestConfig, self).__init__(config_file)

    def get_img_proof_timeout(self):
        """
        Return the img-proof timeout value in seconds.

        :rtype: int
        """
        img_proof_timeout = self._get_attribute(
            attribute='img_proof_timeout',
            element='test'
        )
        return img_proof_timeout or Defaults.get_img_proof_timeout()

    def get_test_ec2_instance_catalog(self):
        """
        Return the instance catalog configured for ec2 tests
        """

        ec2_cloud_info = self.get_cloud_data().get('ec2', {})
        instance_catalog = ec2_cloud_info.get('test_instance_catalog', [])

        if not instance_catalog:
            raise MashConfigException(
                'Ec2 test instance catalog must be provided in config file.'
            )
        return instance_catalog

    def get_ec2_instance_feature_additional_tests(self):
        """
        Returns the additional tests configured for EC2 and the different
        instance features (if any).
        """
        ec2_cloud_info = self.get_cloud_data().get('ec2', {})
        instance_feat_additional_tests = ec2_cloud_info.get(
            'instance_feature_additional_tests',
            {}
        )
        return instance_feat_additional_tests

    def get_test_gce_instance_catalog(self):
        """
        Return the instance catalog configured for gce tests
        """

        gce_cloud_info = self.get_cloud_data().get('gce', {})
        instance_catalog = gce_cloud_info.get('test_instance_catalog', [])

        if not instance_catalog:
            raise MashConfigException(
                'GCE test instance catalog must be provided in config file.'
            )
        return instance_catalog

    def get_gce_instance_feature_additional_tests(self):
        """
        Returns the additional tests configured for GCP and the different
        instance features (if any).
        """
        gce_cloud_info = self.get_cloud_data().get('gce', {})
        instance_feat_additional_tests = gce_cloud_info.get(
            'instance_feature_additional_tests',
            {}
        )
        return instance_feat_additional_tests
