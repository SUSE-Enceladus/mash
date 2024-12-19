# Copyright (c) 2024 SUSE LLC.  All rights reserved.
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

import itertools
import logging
import random

from mash.mash_exceptions import MashTestException


def get_instance_feature_combinations(
    arch: str,
    boot_types: list,
    cpu_options: dict
):
    """
    Provides a list of tuples containing the instance feature combinations
    that will be used for the tests.
    """
    archs = [arch]
    boot_types = extend_boot_types(boot_types)
    cpu_options = extend_cpu_options(cpu_options)
    feature_combinations = list(
        itertools.product(
            archs,
            boot_types,
            cpu_options
        )
    )
    compatible_combinations = remove_incompatible_feature_combinations(
        feature_combinations
    )
    return list(set(compatible_combinations))


def extend_boot_types(boot_types):
    """Extends the list of boot types with the implicit options"""
    if 'uefi-preferred' in boot_types and 'bios' not in boot_types:
        # If uefi-preferred, add bios option
        boot_types.append('bios')
    return boot_types


def extend_cpu_options(cpu_options):
    """Extends the list of cpu_options with the implicit options"""
    extended_cpu_options = []
    if 'AmdSevSnp' in cpu_options:
        extended_cpu_options.append(
            f'AmdSevSnp_{cpu_options["AmdSevSnp"]}'
        )

    if 'AmdSevSnp_disabled' not in extended_cpu_options:
        # Always add the sev_snp disabled option
        extended_cpu_options.append('AmdSevSnp_disabled')

    return extended_cpu_options


def remove_incompatible_feature_combinations(feature_combinations):
    incompatible_combinations = []
    for feature_combination in feature_combinations:
        arch = feature_combination[0]
        boot_type = feature_combination[1]
        sev_snp = feature_combination[2]
        if any([
            # aarch64 requires UEFI boot
            (arch == 'aarch64' and boot_type == 'bios'),
            # AmdSevSnp is not a aarch64 feature
            (arch == 'aarch64' and sev_snp == 'AmdSevSnp_enabled'),
            # AmdSevSnp enabled requires UEFI boot
            (boot_type == 'bios' and sev_snp == 'AmdSevSnp_enabled')
        ]):
            incompatible_combinations.append(feature_combination)

    for incompatible_combination in incompatible_combinations:
        feature_combinations.remove(incompatible_combination)
    return feature_combinations


def select_instances_for_tests(
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
    instances = []
    for feature_combination in feature_combinations:
        instance = select_instance_for_feature_combination(
            feature_combination=feature_combination,
            instance_catalog=instance_catalog,
            logger=logger
        )
        if instance:
            instances.append(instance)
            if logger:
                logger.debug(
                    f'Selected instance {instance} for {feature_combination}'
                )
        else:
            msg = (
                'Unable to find instance to test this feature combination: '
                f'{feature_combination}'
            )
            if logger:
                logger.error(msg)
            raise MashTestException(msg)
    return instances


def select_instance_for_feature_combination(
    feature_combination: tuple,
    instance_catalog: list,
    logger: logging.Logger = None
):
    """
    selects from the instance_catalog one instance that covers the
    feature_combination provided.
    Returns None if there's is no instance in the catalog to test that
    feature combination.
    """

    candidate_groups = []

    arch = feature_combination[0]
    boot_type = feature_combination[1]
    cpu_option = feature_combination[2]

    for instance_group in instance_catalog:
        if arch != instance_group.get('arch'):
            # arch not matching the group
            continue

        if boot_type not in instance_group.get('boot_types', []):
            # required boot type not supported
            continue

        if 'enabled' in cpu_option and cpu_option not in instance_group.get(
            'cpu_options', []
        ):
            # required cpu_option enabled not supported
            continue
        candidate_groups.append(instance_group)

    instance = None
    if candidate_groups:
        selected_group = random.choice(candidate_groups)
        instance = {
            'arch': arch,
            'instance_name': random.choice(selected_group['instance_names']),
            'boot_type': boot_type,
            'cpu_option': cpu_option,
            'region': selected_group['region']
        }
    return instance