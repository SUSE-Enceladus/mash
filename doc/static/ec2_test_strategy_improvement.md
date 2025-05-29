
# Test strategy flexibilization in AWS

## Intro
Cloud providers are constantly adding new features in their instance catalog.
Some of them, for example confidential compute features, are to be tested in
our images as they are supported.It is necessary to improve the testing phase
of image publication in mash to cover the most cases and detect issues before
images are published.

Up to the development of this feature, only the different values in the
`boot_firmware` parameter (bios/uefi/uefi-preferred) was tested and that
approach makes not possible to cover these new instance features.

An additional issue in this area is about the availability of these new
features in the different regions in the cloud provider. At some point in time
a feature can be available in some region but not (yet) in the rest of regions.

## Solution

2 new services have been added to mash:
- *test_preparation*: the image created in the `main` region of the ec2 account
gets replicated to the test regions provided for the ec2 account.
- *test_cleanup*: cleans the image that has been replicated to the test regions
other than the `main` region in the ec2 account profile.

For this feature to work properly there's some configurations to be made:

### Test instance catalog

This new feature will select the instance features that will be tested from a
test instance catalog configured in the mash config file.

Here's an example of a test instance catalog:

```
cloud:
  ec2:
    ...
    test_instance_catalog:
    - region: us-east-1
      partition: aws
      arch: x86_64
      instance_names:
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
      instance_names:
      - i3.large
      - t2.small
      boot_types:
        - bios
      cpu_options: []
    - region: us-east-2
      partition: aws
      arch: x86_64
      instance_names:
      - m6a.large
      - c6a.large
      - r6a.large
      boot_types:
      - uefi-preferred
      - uefi
      cpu_options:
      - AmdSevSnp_enabled
```

Under the `test_instance_catalog` key in the file we have to include the
different instances we want to execute the tests in (including the partition
and the region) and which features are supported in each type.

For example if the instance supports `uefi-preferred` boot type and the
`AmdSevSnp` cpu_option in AWS, the following features will be selected for the
tests:
  - (bios boot + AmdSevSnp disabled)
  - (uefi-preferred boot + AmdSevSnp disabled)
  - (uefi-preferred boot + AmdSevSnp enabled)

Some instance to cover each feature combination is selected from the catalog
if there is some instance that supports the combination.
If there's no instance supporting that combination it will just be logged, but
there has to be at least one test for a feature combination in the list for the
partition.

Note that is required that the instances included in the catalog belong to the
test regions present in the account's `test_regions`. Additionally, instances
for different architectures have to be added to the config file if you plan to
publish images from different architectures.

The format for the each instance group in this config section has to have the
following fields:
 - *region*: which test region will be used if one of these instances is
 selected.
 - *partition*: AWS partition
 - *arch*: instances architecture (x86_64 or aarch64)
 - *instance_names*: name of the instances types. One of these will be selected
 randomly if this group is selected.
 - *boot_types*: which boot types do these isntance types support
 (bios/uefi/uefi-preferred).
 - *cpu_options*: Instance features that are supported. `AmdSevSnp_enabled` is
 the value required for AMD's Sev Snp feature.


### Instance feature tests

In order to check that the image with some feature is OK, a new feature has
been implemented. In the mash configuration file, there's a new key under
`cloud->ec2` that can be used to add additional tests that will be executed
only in the instances that have a feature active. For example, with this config
:

```
cloud:
  ec2:
  ...
    instance_feature_additional_tests:
      AmdSevSnp_enabled:
        - test_sles_sev_snp
```

It's specified that in the images that support `AmdSevSnp_enabled` when the
instance has the feature active, this `test_sles_sev_snp` test will be added on
top of the test suite provided in the mash  job.

The goal for this test is to verify that the feature is active in the instance
and the image is supporting it properly.

### Ec2 account

There's a new entity in the ec2 account object that contains the `test_regions`.
These test regions are the regions where all the test instances will be created.

The `main` region for the ec2 account is automatically added to the test regions.
It's important that the instance catalog and the `test_regions` of the ec2
account are in sync. That is, all the regions in the instance catalog have to
be provisioned in the test_regions for the ec2 accounts.

The configured test regions can be checked with:

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

The subnet has to be set up in aws and it's important that the
`auto assign public ip` flag in the subnet is active so `img-proof` can access
the instances and execute the tests.

