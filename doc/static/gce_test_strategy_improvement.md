
# Region Flexibility for GCE Instance Testing

## Intro
When GCE introduces new instance types or new features on existing instance
types these are generally not immediately available in all regions. Examples
include confidential compute features.
Therefore it is necessary to support a flexible test approach that allows mash
to run the specified tests with configured instance types in a specific region.

Supporting the configuration of specific instance types to test in specified
regions provides the required felxibility.

## Overview

As the GCE platform performs automatically the replication of the created
images in all the available regions, the 2 new services that were included in
mash with the region flexibility for instance testing in AWS are of no use for
GCE. Thus *test_preparation* and *test_cleanup* services have no tasks for jobs
publishing images to GCE.

There is a configuration with the instance types that will be used for the
tests in the different GCE regions.

## Configuring the Test Instances

```
cloud:
  gce:
    test_instance_catalog:
    - region: us-east1-c
      test_fallback_regions:
      - us-east1-b
      - us-east4-a
      arch: X86_64
      instance_types:
      - n1-standard-1
      - n1-highmem-2
      - n1-highcpu-2
      boot_types:
        - uefi
      shielded_vm:
        - securevm_enabled
      nic:
        - gvnic_enabled
      confidential_compute: []
    - region: us-central1-a
      test_fallback_regions:
      - us-central1-b
      - us-east1-b
      arch: X86_64
      instance_types:
      - n2d-standard-2
      boot_types:
        - uefi
      shielded_vm:
        - securevm_enabled
      nic:
        - gvnic_enabled
      confidential_compute:
        - AmdSevSnp_enabled
        - AmdSev_enabled
    - region: us-east1-d
      test_fallback_regions:
      - us-east1-b
      - us-east1-c
      arch: X86_64
      instance_types:
      - c4d-standard-4
      - c3d-standard-4
      boot_types:
        - uefi
      shielded_vm:
        - securevm_enabled
      nic:
        - gvnic_enabled
      confidential_compute:
        - AmdSev_enabled
```

The `test_instance_catalog` key is the beginning of the section that supports
association of instance types to specific regions as well as specific
features to be configured when teh test instance is launched.

Test scenarios will be generated based on the possible combinations of the
specified features and instance types. Some conditions have been included in
the combination generation for the instances as the number of tests with so
many variables would create an excessive number of combinations.

If the specified instance type does not support the full test matrix
the combination unsupported combinations will be skipped and the
information is logged. In case the configured combination, considered
the primary test case, cannot be tested it is considered an error. For
example configuring bios boot with AMD SEV would trigger such an error as
it is required to use UEFI boot to use the SEV SNP feature. Or if the specified
instance type is an instance type that is based on Intel CPUs.

Note that instances for different architectures have to be added to the
config file if you plan to publish images from different architectures.

The following settings are required for each instance group:
 - *region*: the test region to be used if one of these instances is
 selected.
 - *test_fallback_regions*: Additional GCE regions that would be used in case
 a error is found in the GCE platform when attempting the tests in the
 specified region.
 - *arch*: instance architecture (x86_64 or aarch64)
 - *instance_types*: list of the instance types. One of these will be selected
 randomly if this group is selected.
 - *boot_types*: which boot types do these isntance types support
 (bios/uefi/uefi-preferred).
 - *shielded_vm*: instance type supports the GCE shielded_vm feature.
 - *nic*: instance type supports gvnic feature.
 - *confidential_compute*: Instance features that are supported.
  `AmdSev_enabled` is the value required for AMD's Sev feature.


## Instance feature tests

Additional testing for the feature and instance type testing described above
are invoked using the `cloud->gce->instance_feature_additional_tests`
configuration option.

The following example demonstrates the usage:

```
cloud:
  gce:
  ...
    instance_feature_additional_tests:
      AmdSev_enabled:
        - test_sles_sev
```

The above configuration will instruct mash to test images that have the
`AmdSev_enabled` feature setting using the specified instance type from
the `test_instance_catalog` in the specified region. In addition to the
tests specified for the image the additional test with the name
`test_sles_sev_snp` will be executed.

## GCE account

There's no need to do any modification to the mash GCE account to use this
feature.