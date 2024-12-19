import pytest

from unittest.mock import Mock

from mash.mash_exceptions import MashTestException
from mash.services.test.ec2_test_utils import (
    get_instance_feature_combinations,
    select_instances_for_tests
)


class TestEC2TestUtils(object):

    def test_get_instance_feature_combinations(self):
        """tests get_instance_feature_combinations function"""
        test_cases = [
            (
                (
                    'x86_64',
                    ['uefi-preferred'],
                    {
                        'AmdSevSnp': 'enabled'
                    }
                ),
                [
                    ('x86_64', 'bios', 'AmdSevSnp_disabled'),
                    ('x86_64', 'uefi-preferred', 'AmdSevSnp_disabled'),
                    ('x86_64', 'uefi-preferred', 'AmdSevSnp_enabled'),
                ]
            ),
            (
                (
                    'aarch64',
                    ['uefi'],
                    {}
                ),
                [
                    ('aarch64', 'uefi', 'AmdSevSnp_disabled')
                ]
            )
        ]

        for features, expected_combinations in test_cases:
            (arch, boot_types, cpu_options) = features
            assert sorted(expected_combinations) == \
                sorted(get_instance_feature_combinations(
                    arch=arch,
                    boot_types=boot_types,
                    cpu_options=cpu_options
                ))

    def test_select_instances_for_tests(self):
        """tests the select_instances_for_tests"""

        instance_catalog = [
            {
                "region": "us-east-1",
                "arch": "x86_64",
                "instance_names": [
                        "c5.large"
                ],
                "boot_types": [
                    "uefi-preferred",
                    "uefi"
                ],
                "cpu_options": []
            },
            {
                "region": "us-east-1",
                "arch": "x86_64",
                "instance_names": [
                    "i3.large"
                ],
                "boot_types": [
                    "bios"
                ],
                "cpu_options": []
            },
            {
                "region": "us-east-2",
                "arch": "x86_64",
                "instance_names": [
                    "m6a.large"
                ],
                "boot_types": [
                    "uefi-preferred",
                    "uefi"
                ],
                "cpu_options": [
                    "AmdSevSnp_enabled"
                ]
            },
            {
                "region": "us-east-1",
                "arch": "aarch64",
                "instance_names": [
                    "t4g.small",
                    "m6g.medium"
                ],
                "boot_types": [],
                "cpu_options": []
            }
        ]

        test_cases = [
            (
                [('x86_64', 'bios', 'AmdSevSnp_disabled')],
                [
                    {
                        'region': 'us-east-1',
                        'instance_name': 'i3.large',
                        'boot_type': 'bios',
                        'cpu_option': 'AmdSevSnp_disabled',
                        'arch': 'x86_64'
                    }
                ]
            ),
            (
                [
                    ('x86_64', 'bios', 'AmdSevSnp_disabled'),
                    ('x86_64', 'uefi-preferred', 'AmdSevSnp_enabled')],
                [
                    {
                        'region': 'us-east-1',
                        'instance_name': 'i3.large',
                        'boot_type': 'bios',
                        'cpu_option': 'AmdSevSnp_disabled',
                        'arch': 'x86_64'
                    },
                    {
                        'region': 'us-east-2',
                        'instance_name': 'm6a.large',
                        'boot_type': 'uefi-preferred',
                        'cpu_option': 'AmdSevSnp_enabled',
                        'arch': 'x86_64'
                    }
                ]

            )
        ]
        logger = Mock()
        for feature_combinations, expected_instances in test_cases:
            selected_instances = select_instances_for_tests(
                feature_combinations=feature_combinations,
                instance_catalog=instance_catalog,
                logger=logger
            )
            for instance in selected_instances:
                assert instance in expected_instances

        # error case
        logger.reset_mock()
        feature_combination = (
            'non_existing_arch',
            'bios',
            'AmdSevSnp_disabled'
        )
        msg = (
            'Unable to find instance to test this feature combination: '
            f'{feature_combination}'
        )
        with pytest.raises(MashTestException) as error:
            select_instances_for_tests(
                feature_combinations=[feature_combination],
                instance_catalog=instance_catalog,
                logger=logger
            )
            assert msg in str(error)
        logger.error.assert_called_once_with(msg)