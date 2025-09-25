
# Region Flexibility for AWS Instance Testing

## Intro
When AWS introduces new instance types or new features on existing instance
types these are generally not immediately available in all regions. Examples
include the introduction of Graviton instances and confidential compute
features. Therefore, it is necessary to support a flexible test approach
that allows mash to run the specified tests with configured instance types
in a specific region.

Prior to the introduction of a flexible testing approach it was only possible
to test variations for the boot firmware setting, a feature introduced in all
AWS regions at once.

Supporting the configuration of specific instance types to test in specified
regions provides the required flexibility.

## Overview

2 services handle the flexible test process:
- *test_preparation*: the image created in the `main` region of the EC2 account
gets replicated to the test regions provided for the EC2 account.
- *test_cleanup*: cleans the image that has been replicated to the test regions
by the test_preparation service.

The configuration example below shows how to associate specific test instance
types with a given region.

## Configuring the Test Instances

```
cloud:
  ec2:
    ...
    test_instance_catalog:
    - region: us-east-1
      partition: aws
      arch: x86_64
      instance_types:
      - c5.large
      - m5.large
      - t3.small
      boot_types:
        - uefi-preferred
        - uefi
      cpu_options: []
    - region: us-east-1
      arch: x86_64
      partition: aws
      instance_types:
      - i3.large
      - t2.small
      boot_types:
        - bios
      cpu_options: []
    - region: us-east-2
      partition: aws
      arch: x86_64
      instance_types:
      - m6a.large
      - c6a.large
      - r6a.large
      boot_types:
      - uefi-preferred
      - uefi
      cpu_options:
      - AmdSevSnp_enabled
```

The `test_instance_catalog` key is the beginning of the section that supports
association of instance types to specific regions as well as specific
features to be configured when teh test instance is launched.

Test scenarios will be generated based on the possible combinations of the
specified features and instance types.

For example, if the instance supports `uefi-preferred` boot type and the
`AmdSevSnp` cpu_option in AWS is set to be tested, the following test
matrix will be generated
tests:
  - (bios boot + AmdSevSnp disabled)
  - (uefi-preferred boot + AmdSevSnp disabled)
  - (uefi-preferred boot + AmdSevSnp enabled)

If the specified instance type does not support the full test matrix
the unsupported combinations will be skipped and the information is logged.
In case the configured combination, considered the primary test case, cannot
be tested it is considered an error. For example configuring bios boot with
AMD SEV would trigger such an error as it is required to use UEFI boot to use
the SEV SNP feature. Or if the specified instance type is an instance type
that is based on Intel CPUs.

Note that it is required that the instance types specified in the catalog
are present in the test regions as configured in the account's `test_regions`.
Additionally, instances for different architectures have to be added to the
config file if you plan to publish images from different architectures.

The following settings are required for each instance group:
 - *region*: the test region to be used if one of these instances is
 selected.
 - *partition*: AWS partition
 - *arch*: instance architecture (x86_64 or aarch64)
 - *instance_types*: list of the instance types. One of these will be selected
 randomly if this group is selected.
 - *boot_types*: which boot types do these isntance types support
 (bios/uefi/uefi-preferred).
 - *cpu_options*: Instance features that are supported. `AmdSevSnp_enabled` is
 the value required for AMD's Sev Snp feature.


## Instance feature tests

Additional testing for the feature and instance type testing described above
are invoked using the `cloud->ec2->instance_feature_additional_tests`
configuration option.

The following example demonstrates the usage:

```
cloud:
  ec2:
  ...
    instance_feature_additional_tests:
      AmdSevSnp_enabled:
        - test_sles_sev_snp
```

The above configuration will instruct mash to test images that have the
`AmdSevSnp_enabled` feature setting using the specified instance type from
the `test_instance_catalog` in the specified region. In addition to the
tests specified for the image the additional test with the name
`test_sles_sev_snp` will be executed.

## EC2 account

The final step to tie the `test_instance_catalog` and
`instance_feature_additional_tests` together is the `test_regions` configuration
option for the EC2 account. The `test_regions` setting specifies in which
regions the testing should be executed. This setting has no influence on the
primary region configured for testing.

Regions configured in the `test_instance_catalog` need to match with the
regions in the `test_regions` setting.

Configured test regions can be checked with:

```
$ mash account ec2 info --name database-test-1
{
     "additional_regions":[],
     "id": "31",                  │
     "name": "test-account-1",
     "partition":"aws",
     "region": "us-east-1",
     "subnet": "subnet-1-123456",
     "test_regions": [
        {
           "region": "us-east-1",
           "subnet": "subnet-1-123456"
        },
        {
           "region": "us-east-2",
           "subnet": "subnet-2-123456"
        },
        {
           "region": "us-east-3",
           "subnet": "subnet-3-123456"
        }
    ]
}
```

Each test region entity is composed of 2 fields:
  - *region*: region name
  - *subnet*: subnet that will be used to test the instances in that region.

The subnet has to be set up in AWS and it's important that the
`auto assign public ip` flag in the subnet is active so `img-proof` can access
the instances and execute the tests.

