from unittest.mock import Mock

from mash.services.test.gce_test_utils import (
    get_instance_feature_combinations,
    select_instance_configs_for_tests,
    get_additional_tests_for_instance
)


class TestGCETestUtils(object):

    def test_get_instance_feature_combinations(self):
        """tests get_instance_feature_combinations function"""
        test_cases = [
            (
                (
                    'x86_64',
                    ['uefi'],
                    [
                        'GVNIC',
                        'UEFI_COMPATIBLE',
                        'SEV_SNP_CAPABLE'
                    ]
                ),
                [
                    (
                        'x86_64',
                        'uefi',
                        'securevm_disabled',
                        'gvnic_enabled',
                        'AmdSevSnp_enabled',
                    ),
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_disabled',
                        'AmdSevSnp_enabled',
                    ),
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_enabled',
                        'AmdSevSnp_enabled',
                    ),
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_enabled',
                        'confidentialcompute_disabled',
                    ),
                ]
            ),
            (
                (
                    'x86_64',
                    ['uefi'],
                    [
                        'GVNIC',
                        'UEFI_COMPATIBLE',
                        'SEV_SNP_CAPABLE',
                        'SEV_CAPABLE',
                        'SEV_LIVE_MIGRATABLE',
                        'SEV_LIVE_MIGRATABLE_V2',
                        'SEV_SNP_CAPABLE',
                        'TDX_CAPABLE',
                    ]
                ),
                [
                    (
                        'x86_64',
                        'uefi',
                        'securevm_disabled',
                        'gvnic_enabled',
                        'AmdSevSnp_enabled',
                    ),
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_disabled',
                        'AmdSevSnp_enabled',
                    ),
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_enabled',
                        'AmdSevSnp_enabled',
                    ),
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_enabled',
                        'AmdSev_enabled',
                    ),
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_enabled',
                        'IntelTdx_enabled',
                    ),
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_enabled',
                        'confidentialcompute_disabled',
                    ),
                ]
            )
        ]

        for features, expected_combinations in test_cases:
            (arch, boot_types, guest_os_features) = features
            assert sorted(expected_combinations) == \
                sorted(get_instance_feature_combinations(
                    arch=arch,
                    boot_types=boot_types,
                    guest_os_features=guest_os_features
                ))

    def test_select_instance_configs_for_tests(self):
        """tests the select_instance_configs_for_tests"""

        instance_catalog = [
            {
                "region": "us-east1-b",
                "arch": "X86_64",
                "instance_types": [
                    "n1-standard-1",
                ],
                "boot_types": [
                    "uefi"
                ],
                "shielded_vm": [
                    "securevm_enabled"
                ],
                "nic": [
                    "gvnic_enabled"
                ],
                "confidential_compute": []
            },
            {
                "region": "us-east1-b",
                "arch": "X86_64",
                "instance_types": [
                    "n2d-standard-2"
                ],
                "boot_types": [
                    "uefi"
                ],
                "shielded_vm": [
                    "securevm_enabled"
                ],
                "nic": [
                    "gvnic_enabled"
                ],
                "confidential_compute": [
                    "AmdSevSnp_enabled",
                    "AmdSev_enabled"
                ]
            },
            {
                "region": "us-east1-b",
                "arch": "X86_64",
                "instance_types": [
                    "c3-standard-4"
                ],
                "boot_types": [
                    "uefi"
                ],
                "shielded_vm": [
                    "securevm_enabled"
                ],
                "nic": [
                    "gvnic_enabled"
                ],
                "confidential_compute": [
                    "IntelTdx_enabled"
                ],
            },
            {
                "region": "us-east1-b",
                "arch": "ARM64",
                "instance_types": [
                    "t2a-standard-2"
                ],
                "boot_types": [
                    "uefi"
                ],
                "shielded_vm": [
                    "securevm_enabled"
                ],
                "nic": [
                    "gvnic_enabled"
                ],
                "confidential_compute": [],
            },

        ]

        test_cases = [
            (
                [
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_disabled',
                        'AmdSev_enabled'
                    )
                ],
                [
                    {
                        'arch': 'X86_64',
                        'instance_type': 'n2d-standard-2',
                        'region': 'us-east1-b',
                        'boot_type': 'uefi',
                        'shielded_vm': 'securevm_enabled',
                        'nic': 'gvnic_disabled',
                        'confidential_compute': 'AmdSev_enabled'
                    }
                ]
            ),
            (
                [
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_enabled',
                        'AmdSevSnp_enabled'
                    )
                ],
                [
                    {
                        'arch': 'X86_64',
                        'instance_type': 'n2d-standard-2',
                        'region': 'us-east1-b',
                        'boot_type': 'uefi',
                        'shielded_vm': 'securevm_enabled',
                        'nic': 'gvnic_enabled',
                        'confidential_compute': 'AmdSevSnp_enabled'
                    }
                ]
            ),
            (
                [
                    (
                        'x86_64',
                        'uefi',
                        'securevm_enabled',
                        'gvnic_enabled',
                        'IntelTdx_enabled'
                    )
                ],
                [
                    {
                        'arch': 'X86_64',
                        'instance_type': 'c3-standard-4',
                        'region': 'us-east1-b',
                        'boot_type': 'uefi',
                        'shielded_vm': 'securevm_enabled',
                        'nic': 'gvnic_enabled',
                        'confidential_compute': 'IntelTdx_enabled'
                    }
                ]
            ),
            (
                [
                    (
                        'ARM64',
                        'uefi',
                        'securevm_disabled',
                        'gvnic_disabled',
                        'confidentialcompute_disabled'
                    )
                ],
                [
                    {
                        'arch': 'ARM64',
                        'instance_type': 't2a-standard-2',
                        'region': 'us-east1-b',
                        'boot_type': 'uefi',
                        'shielded_vm': 'securevm_disabled',
                        'nic': 'gvnic_disabled',
                        'confidential_compute': 'confidentialcompute_disabled'
                    }
                ]
            )
        ]
        logger = Mock()
        for (
            feature_combinations,
            expected_instance_configs
        ) in test_cases:
            selected_instance_configs = select_instance_configs_for_tests(
                feature_combinations=feature_combinations,
                instance_catalog=instance_catalog,
                logger=logger
            )
            for instance_config in selected_instance_configs:
                assert instance_config in expected_instance_configs

        # error case
        logger.reset_mock()
        feature_combination = (
            'ARM64',
            'uefi',
            'securevm_enabled',
            'gvnic_disabled',
            'AmdSev_enabled'
        )
        msg = (
            'Unable to find instance to test this feature combination: '
            f'{feature_combination}'
        )
        instance_configs = select_instance_configs_for_tests(
            feature_combinations=[feature_combination],
            instance_catalog=instance_catalog,
            logger=logger
        )
        assert instance_configs == []
        logger.error.assert_called_once_with(msg)

    def test_get_additional_tests_for_instance(self):
        """tests the select_instance_configs_for_tests"""

        additional_tests = {
            'AmdSev_enabled': [
                'AmdSev_enabled_test_1',
                'AmdSev_enabled_test_2',
            ],
            'AmdSevSnp_enabled': [
                'AmdSevSnp_enabled_test_1'
            ],
            'IntelTdx_enabled': [],
            'gvnic_enabled': [
                'gvnic_enabled_test_1'
            ]
        }

        test_cases = [
            (
                (
                    'X86_64',
                    'uefi',
                    'securevm_disabled',
                    'gvnic_enabled',
                    'IntelTdx_enabled'
                ),
                [
                    'gvnic_enabled_test_1'
                ]
            ),
            (
                (
                    'X86_64',
                    'uefi',
                    'securevm_disabled',
                    'gvnic_enabled',
                    'AmdSev_enabled'
                ),
                [
                    'gvnic_enabled_test_1',
                    'AmdSev_enabled_test_1',
                    'AmdSev_enabled_test_2',
                ]
            ),
            (
                (
                    'X86_64',
                    'uefi',
                    'securevm_disabled',
                    'gvnic_disabled',
                    'confidentialcompute_disabled'
                ),
                []
            )
        ]

        for feature_combination, expected_additional_tests in test_cases:
            assert expected_additional_tests == \
                get_additional_tests_for_instance(
                    feature_combination=feature_combination,
                    additional_tests=additional_tests
                )
