# Copyright (c) 2025 SUSE LLC.  All rights reserved.
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

import itertools
import logging
import random


def get_instance_feature_combinations(
    arch: str,
    boot_types: list,
    guest_os_features: list
):
    """
    Provides a list of tuples containing the instance feature combinations
    that will be used for the tests.
    """
    archs = [arch]
    shielded_vm_features = extract_shielded_features(guest_os_features)
    nic_features = extract_nic_features(guest_os_features)
    confidential_comp_features = extract_confidential_comp_features(
        guest_os_features
    )

    feature_combinations = list(
        itertools.product(
            archs,
            boot_types,
            shielded_vm_features,
            nic_features,
            confidential_comp_features
        )
    )
    compatible_combinations = remove_incompatible_feature_combinations(
        feature_combinations
    )
    return list(set(compatible_combinations))


def extract_shielded_features(guest_os_features: list) -> list:
    """
    Extracts the different configurations for shielded vm feature that will be
     tested. Deppending on the supported boot features.
    """
    shielded_features = []
    if 'UEFI_COMPATIBLE' in guest_os_features:
        shielded_features.append('securevm_enabled')
        # Omitting for now:
        #   - Virtual Trusted Platform Module (vTPM): enabled by default
        #   - Integrity monitoring: enabled by default
        # Those will be active in the tests always
    shielded_features.append('securevm_disabled')
    return shielded_features


def extract_nic_features(guest_os_features: list) -> list:
    """
    Extracts the different nic configurations that will be tested
    Deppending on the supported nic features, the different nic configurations
    are provided.
    """
    nic_features = []
    if 'GVNIC' in guest_os_features:
        nic_features.append('gvnic_enabled')
    nic_features.append('gvnic_disabled')
    return nic_features


def extract_confidential_comp_features(guest_os_features: list) -> list:
    """
    Extracts the Confidential Compute configurations that will be tested
    Deppending on the supported coco features, the different configurations
    are provided.
    """
    conf_comp_features = []

    if 'SEV_SNP_CAPABLE' in guest_os_features:
        conf_comp_features.append('AmdSevSnp_enabled')
    if 'SEV_CAPABLE' in guest_os_features:
        conf_comp_features.append('AmdSev_enabled')
    if 'TDX_CAPABLE' in guest_os_features:
        conf_comp_features.append('IntelTdx_enabled')
    conf_comp_features.append('confidentialcompute_disabled')

    return conf_comp_features


def remove_incompatible_feature_combinations(feature_combinations):
    incompatible_combinations = []
    # Only allowing 1 combination for:
    #  - gvnic_disabled
    #  - securevm_disabled
    # Not to try a lot of combinations
    gvnic_disabled_already_included = False
    shieldedvm_disabled_already_included = False
    for feature_combination in feature_combinations:
        arch = feature_combination[0]
        boot_type = feature_combination[1]
        shielded_vm = feature_combination[2]
        nic = feature_combination[3]
        conf_compute = feature_combination[4]

        if any([
            # aarch64 requires UEFI boot
            (arch == 'aarch64' and boot_type == 'bios'),
            # aarch64 images don't support secure boot
            (arch == 'aarch64' and shielded_vm == 'securevm_enabled'),
            # AmdSev is not a aarch64 feature
            (arch == 'aarch64' and conf_compute == 'AmdSev_enabled'),
            # AmdSevSnp is not a aarch64 feature
            (arch == 'aarch64' and conf_compute == 'AmdSevSnp_enabled'),
            # IntelTdx is not a aarch64 feature
            (arch == 'aarch64' and conf_compute == 'IntelTdx_enabled'),
            # AmdSevSnp enabled requires UEFI boot
            (boot_type == 'bios' and conf_compute == 'AmdSevSnp_enabled'),
            # AmdSev enabled requires UEFI boot
            (boot_type == 'bios' and conf_compute == 'AmdSev_enabled'),
            # Only include one combination with gvnic_disabled
            (nic == 'gvnic_disabled' and gvnic_disabled_already_included),
            # Only include one combination with securevm_disabled
            (
                all([
                    shielded_vm == 'securevm_disabled',
                    shieldedvm_disabled_already_included
                ])
            )
        ]):
            incompatible_combinations.append(feature_combination)
        else:
            if nic == 'gvnic_disabled':
                # one test with gvnic_disabled has been included already
                gvnic_disabled_already_included = True
            if shielded_vm == 'securevm_disabled':
                # one test with securevm_disabled has been included already
                shieldedvm_disabled_already_included = True

    for incompatible_combination in incompatible_combinations:
        feature_combinations.remove(incompatible_combination)
    return feature_combinations


def select_instance_configs_for_tests(
    instance_catalog: list,
    feature_combinations: list,
    logger: logging.Logger = None
) -> list:
    """
    Selects the instance types and configurations used in the tests
    Taking as input the instance catalog configured and the
    feature_combinations that are required to be tested, chooses some intances
    to cover the provided feature combinations.
    Raises a MashTestException if there's some feature_combination that is not
    possible to test with the instance_catalog.
    """
    instance_configs = []
    for feature_combination in feature_combinations:
        instance_config = select_instance_config_for_feature_combination(
            feature_combination=feature_combination,
            instance_catalog=instance_catalog,
            logger=logger
        )
        if instance_config:
            instance_configs.append(instance_config)
            if logger:
                logger.debug(
                    f'Selected instance {instance_config} for '
                    f'{feature_combination}'
                )
        else:
            # Just writing in the log the issue for now
            msg = (
                'Unable to find instance to test this feature combination: '
                f'{feature_combination}'
            )
            if logger:
                logger.error(msg)
    return instance_configs


def select_instance_config_for_feature_combination(
    feature_combination: tuple,
    instance_catalog: list,
    logger: logging.Logger = None
):
    """
    selects from the instance_catalog for GCE one instance that covers the
    feature_combination provided.
    Returns None if there's is no instance in the catalog to test that
    feature combination.
    """

    candidate_groups = []

    arch = feature_combination[0].upper()
    boot_type = feature_combination[1]
    shielded_vm = feature_combination[2]
    nic = feature_combination[3]
    confidential_compute = feature_combination[4]

    for instance_group in instance_catalog:
        if arch != instance_group.get('arch'):
            # arch not matching the group
            continue

        if boot_type not in instance_group.get('boot_types', []):
            # required boot type not supported
            continue

        if 'enabled' in shielded_vm and shielded_vm not in instance_group.get(
            'shielded_vm', []
        ):
            # required shielded_vm feature not supported
            continue

        if 'enabled' in nic and nic not in instance_group.get('nic', []):
            # required nic feature not supported
            continue

        if (
            'enabled' in confidential_compute and confidential_compute not in
            instance_group.get('confidential_compute', [])
        ):
            # required confidential_compute feature not supported
            continue

        candidate_groups.append(instance_group)

    instance_config = None
    if candidate_groups:
        selected_group = random.choice(candidate_groups)
        instance_config = {
            'arch': arch,
            'instance_type': random.choice(selected_group['instance_types']),
            'boot_type': boot_type,
            'region': selected_group['region'],
            'shielded_vm': shielded_vm,
            'nic': nic,
            'confidential_compute': confidential_compute
        }
    return instance_config


def get_additional_tests_for_instance(
    feature_combination,
    additional_tests
):
    """Provides a list of additional tests configured for each instance type"""
    tests = []

    arch = feature_combination[0]
    boot_type = feature_combination[1]
    shielded_vm = feature_combination[2]
    nic = feature_combination[3]
    conf_compute = feature_combination[4]

    tests.extend(additional_tests.get(arch, []))
    tests.extend(additional_tests.get(boot_type, []))
    tests.extend(additional_tests.get(shielded_vm, []))
    tests.extend(additional_tests.get(nic, []))
    tests.extend(additional_tests.get(conf_compute, []))
    return tests
