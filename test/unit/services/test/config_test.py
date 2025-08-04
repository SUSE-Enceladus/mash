from mash.services.test.config import TestConfig


class TestTestConfig(object):
    def setup_method(self):
        self.empty_config = TestConfig('test/data/empty_mash_config.yaml')
        self.config = TestConfig('test/data/mash_config.yaml')

    def test_get_log_file(self):
        assert self.empty_config.get_log_file('test') == \
            '/var/log/mash/test_service.log'

    def test_get_img_proof_timeout(self):
        assert self.empty_config.get_img_proof_timeout() == 600

    def test_get_test_ec2_instance_catalog(self):
        expected_catalog = [
            {
                "region": "us-east-1",
                "arch": "x86_64",
                "instance_names": [
                    "c5.large",
                    "m5.large",
                    "t3.small"
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
                    "i3.large",
                    "t2.small"
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
                    "m6a.large",
                    "c6a.large",
                    "r6a.large"
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
        assert self.config.get_test_ec2_instance_catalog() == expected_catalog

    def test_get_ec2_instance_feature_additional_tests(self):
        expected_additional_tests = {
            "AmdSevSnp_enabled": [
                "test_sles_sev_snp"
            ]
        }
        assert self.config.get_ec2_instance_feature_additional_tests() == \
            expected_additional_tests

    def test_get_test_gce_instance_catalog(self):
        expected_catalog = [
            {
                "region": "us-east1-b",
                "arch": "X86_64",
                "instance_names": [
                    "n1-standard-1",
                    "n1-highmem-2",
                    "n1-highcpu-2",
                    "f1-micro"
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
                "instance_names": [
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
                "instance_names": [
                    "c4d-standard-2",
                    "c3d-standard-2"
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
                    "AmdSev_enabled"
                ]
            },
            {
                "region": "us-east1-b",
                "arch": "X86_64",
                "instance_names": [
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
                ]
            },
            {
                "region": "us-east1-b",
                "arch": "ARM64",
                "instance_names": [
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
                "confidential_compute": []
            },
        ]

        assert self.config.get_test_gce_instance_catalog() == expected_catalog
