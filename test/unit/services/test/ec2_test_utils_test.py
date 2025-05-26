from unittest.mock import Mock

from mash.services.test.ec2_test_utils import (
    get_instance_feature_combinations,
    select_instances_for_tests,
    get_partition_test_regions,
    get_image_id_for_region,
    get_cpu_options
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
                "partition": "aws",
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
                "partition": "aws",
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
                "partition": "aws",
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
                "partition": "aws",
                "arch": "aarch64",
                "instance_names": [
                    "t4g.small",
                    "m6g.medium"
                ],
                "boot_types": [],
                "cpu_options": []
            },
            {
                "region": "us-gov-west-1",
                "partition": "us-gov",
                "arch": "x86_64",
                "instance_names": [
                    "t4g.small",
                    "m6g.medium"
                ],
                "boot_types": [
                    "bios"
                ],
                "cpu_options": []
            }

        ]

        test_cases = [
            (
                [('x86_64', 'bios', 'AmdSevSnp_disabled')],
                ['us-east-1'],
                [
                    {
                        'region': 'us-east-1',
                        'partition': 'aws',
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
                    ('x86_64', 'uefi-preferred', 'AmdSevSnp_enabled')
                ],
                ['us-east-1', 'us-east-2'],
                [
                    {
                        'region': 'us-east-1',
                        'partition': 'aws',
                        'instance_name': 'i3.large',
                        'boot_type': 'bios',
                        'cpu_option': 'AmdSevSnp_disabled',
                        'arch': 'x86_64'
                    },
                    {
                        'region': 'us-east-2',
                        'instance_name': 'm6a.large',
                        'partition': 'aws',
                        'boot_type': 'uefi-preferred',
                        'cpu_option': 'AmdSevSnp_enabled',
                        'arch': 'x86_64'
                    }
                ]
            )
        ]
        logger = Mock()
        for (
            feature_combinations,
            test_regions,
            expected_instances
        ) in test_cases:
            selected_instances = select_instances_for_tests(
                test_regions=test_regions,
                feature_combinations=feature_combinations,
                instance_catalog=instance_catalog,
                logger=logger
            )
            for instance in selected_instances:
                assert instance in expected_instances

        # error case
        logger.reset_mock()
        feature_combination = (
            'aarch64',
            'bios',
            'AmdSevSnp_disabled'
        )
        msg = (
            'Unable to find instance to test this feature combination: '
            f'{feature_combination}'
        )
        instance_types = select_instances_for_tests(
            test_regions=['us-gov-west-1'],
            feature_combinations=[feature_combination],
            instance_catalog=instance_catalog,
            logger=logger
        )
        assert instance_types == []
        logger.error.assert_called_once_with(msg)

    def test_get_partition_test_regions(self):
        """tests the get_partition_test_regions"""
        test_cases = [
            (
                {
                    'us-east-1': {
                        'partition': 'aws'
                    },
                    'us-east-2': {
                        'partition': 'aws'
                    },
                    'us-east-3': {
                        'partition': 'aws'
                    },
                },
                {
                    'aws': [
                        'us-east-1',
                        'us-east-2',
                        'us-east-3'
                    ]
                }
            )
        ]
        for test_regions, expected_output in test_cases:
            assert expected_output == get_partition_test_regions(test_regions)

    def test_get_image_id_for_region(self):
        """tests the get_image_id_for_region"""

        source_regions = {
            'us-east-1': 'ami-111111',
            'us-east-2': 'ami-222222',
        }
        replicate_regions = {
            'us-east-3': 'ami-333333'
        }

        test_cases = [
            ('us-east-1', 'ami-111111'),
            ('us-east-2', 'ami-222222'),
            ('us-east-3', 'ami-333333'),
            ('us-east-4', '')

        ]
        for region, expected_output in test_cases:
            assert expected_output == get_image_id_for_region(
                region,
                source_regions,
                replicate_regions
            )

    def test_get_cpu_options(self):
        """tests the get_cpu_options"""

        cpu_option = (
            'cpu-option-1_value1,'
            'cpu-option-2_disabled,'
            'cpu-option-3_value3'
        )
        expected_result = {
            'cpu-option-1': 'value1',
            'cpu-option-3': 'value3'
        }
        assert expected_result == get_cpu_options(cpu_option)
