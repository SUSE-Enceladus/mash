from mash.services.test.gce_test_utils import (
    get_instance_feature_combinations,
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
