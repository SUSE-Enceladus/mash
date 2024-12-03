
from mash.services.test.ec2_test_utils import (
    get_instance_feature_combinations
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
