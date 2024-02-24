![Continuous testing & Linting](https://github.com/SUSE-Enceladus/mash/workflows/Continuous%20testing%20&%20Linting/badge.svg?branch=master)

# Mash - Public Cloud Image Release Tool

MASH is an automated image testing & publishing tool for Public Cloud images.
It is written in Python3 and designed to run as a set of Systemd & HTTP
services. Mash currently supports a number of Public Cloud Frameworks; such
as Amazon EC2, Google Compute Engine and Microsoft Azure.

## Quick Start

For a quick start into mash and its service pipeline, an OCI container
image is provided. The container can be used as a mash development
environment as well as a server instance for integration testing of
the mash pipeline. The following steps are needed to get started:

```bash
podman pull registry.opensuse.org/virtualization/appliances/images/images_tw/opensuse/mash:latest
podman run -ti mash
```

The mash instance starts up and a login prompt to the system appears.
From here the following setup steps are required:

1. Login to the instance

   ```bash
   login: masher
   password: linux
   ```

2. Create a user for mash:

   ```bash
   mash user create --email test@fake.com
   ```

3. Login to mash:

   ```bash
   mash auth login --email test@fake.com
   ```

4. Setup public cloud account

   For the quick start, an AWS account setup is described. Please
   refer to [Configuring Mash Client](#configure_mash_client) for more
   details.

   ```bash
   mash account ec2 add \
       --name private \
       --partition aws \
       --region eu-central-1 \
       --subnet ... \
       --group ... \
       --access-key-id ... \
       --secret-access-key ...
   ```

   The values written as ```...``` are sensitive information
   from the respective AWS account credentials and account
   setup.

5. Create a job

   The most simple mash job for AWS covers the upload and registration
   of an AMI image from a given EC2 disk image URL.

   ```bash
   cat >example.job <<-EOF
   {
       "boot_firmware": [
           "uefi-preferred"
       ],
       "cloud_account": "private",
       "cloud_architecture": "x86_64",
       "cloud_image_name": "opensuse-leap-15.5-x86_64-v{date}",
       "download_url": "https://download.opensuse.org/repositories/Cloud:/Images:/Leap_15.5/images/",
       "image": "openSUSE-Leap-15.5",
       "image_description": "openSUSE Leap 15.5",
       "last_service": "create",
       "notification_email": "test@fake.com",
       "notify": false,
       "profile": "EC2",
       "utctime": "now"
   }
   EOF
   ```

   __NOTE__:
    The setting for boot_firmware connects to the boot capabilities of the
    referenced image and should be taken seriously. An image to boot in the
    AWS cloud can be selected to use either a BIOS+MasterBootRecord interface
    or an EFI+EFI-binary interface. Images built by SUSE supports both modes
    and we prefer EFI boot over BIOS boot which is the reason for the above
    setting. In case a self-built image or other image source should be used
    with mash, it's important to clarify on the boot capabilities first.

   To put the job into the pipeline call the following command:

   ```bash
   mash job ec2 add example.job
   ```

   List your job(s) with the following command:

   ```bash
   mash job list
   ```

## Installation

### openSUSE/SUSE package

The package can be found in the following repo:

```
$ zypper ar http://download.opensuse.org/repositories/Cloud:/Tools:/CI/<distribution>
```

To install Mash run the following commands:

```bash
$ zypper refresh
$ zypper in mash
```

## Usage

### Install and configure the Mash Client

The Mash Client provides a command line tool for interfacing with the Mash
Server REST API.

#### Installing from Cloud:Tools OBS project

```bash
zypper ar http://download.opensuse.org/repositories/Cloud:/Tools/<distribution>
zypper refresh
zypper in mash-client
```

#### Installing from PyPI

```
pip install mash-client
```

### Configuring Mash Client <a name="configure_mash_client"/>

The mash command by default reads a configuration file from
\~/.config/mash_client. It is recommended to use the default directory for the
configuration file. Otherwise the configuration directory must be specified
with every mash command execution. The client supports multiple profiles.
Each profile is represented by a configuration file in the configuration
directory in the form of a {profile}.yaml file. Profiles allow you to set up
an account on different target servers. The default profile name is "default"
(\~/.config/mash_client/default.yaml) and this file is created when using the
`mash config setup` command. To create a configuration file with
a different name use the `--profile` option for the setup command. For example
`mash config setup --profile prod` would create the
\~/.config/mash_client/prod.yaml file.

### Login and create a Mash user account

To sign in and create an account use one of the commands:

`mash auth oidc` or `mash auth login`

An email is required when not using an oidc provider.

### Creating AWS accounts

Credentials for the EC2 API are a set of an access_key_id and
secret_access_key. These can be for a root account or an IAM account although
it's recommended to use an IAM account. This adds security and disposability
to the credentials which will be stored on the Mash server. Accounts for
EC2 should normally have the partition set to "aws". A partition is a distinct
reference implementation of the AWS platform. The three partitions are; China,
US Gov and AWS (default).

#### Requirements

For Mash to successfully test an image it will require SSH access to the
instance in the account's chosen region. To ensure this, there are two options.
You can set the default security group for the region to allow ingress for SSH
(22) for all IP addresses. Or you can create a new subnet for mash and set its
default security group to allow ingress of SSH for all IP addresses. If you
choose to create a subnet ensure that the subnet ID is added to the account
when it's created in mash.

#### Creating a group with the required permissions

It's recommended to create a group that has the required permissions for mash.
Then when a new IAM account is created it can be added to this group to pick
up the permissions. The following permissions are required for mash:

#### Creating an IAM account from AWS Console

Once logged in the following steps will generate an IAM account
and a set of credentials which can be used with Mash:

1. Click the __Services__ dropdown
1. Find and click __IAM__ (Can start typing in the search box)
1. Click the __Users__ button
1. Click __Add user__
1. In the __User name__ text box enter a name which includes your name, login or
some other identifier (e.g. jdoe)
1. In the __Access type section__ Select the Programmatic access box
1. Click __Next: Permissions__
1. In the __Add user to group__ section find and select the box for the desired
group
1. Click __Next: Tags__
1. Add any optional tags for the user
1. Click __Next: Review__
1. Click __Create User__
1. Click __Show__ in the "Secret access key section"
1. Copy the "Access key ID" and "Secret access key" to a secure location
(or add directly to a new account using Mash client)
1. Click __Close__

The mash group will give the credentials full access to EC2 and S3 which is
required by the Mash server.

#### Adding a new EC2 account to MASH via client CLI

To add the account with Mash client use the following command:

```bash
mash account ec2 add \
  --name {account name} \
  --region {region name} \
  --access-key-id {access key id} \
  --secret-access-key {secret access key} \
  --partition {partition name}
```

__Group__

Additionally there is a `--group` option that may be included to organize all
three accounts. The group can be used when submitting a job to publish
simultaneously to all three partitions.

__Additional region__

For AWS partitions there may be additional regions which can be configured
when creating an EC2 account in Mash:

```bash
mash account ec2 add \
  --name {account name} \
  --region {region name} \
  --access-key-id {access key id} \
  --secret-access-key {secret access key} \
  --partition {partition name} \
  --additional-regions
```

The additional regions option will provide a REPL style workflow to add the
region.

__More info__

Creating an IAM account:
[EC2 docs](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html)

### Creating Azure accounts

MASH uses service principals for Azure authentication. A service principal
defines the access policy and permissions for the user/application in the
Azure AD tenant.

#### Create service principal with Azure CLI

If you are using openSUSE you can install the Azure CLI with the following command:

```bash
zypper install azure-cli
```

The following command will generate the necessary json service principal file:

```bash
$ az ad sp create-for-rbac \
  --sdk-auth \
  --role Contributor \
  --scopes /subscriptions/{subscription_id} \
  --name "{name}" > /path/to/credentials.json
```

#### Configure service principle permissions

Todo...

#### Example service principle JSON file

```json
{
    "clientId": "<Service principal ID>",
    "clientSecret": "<Service principal secret/password>",
    "subscriptionId": "<Subscription associated with the service principal>",
    "tenantId": "<The service principal's tenant>",
    "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
    "resourceManagerEndpointUrl": "https://management.azure.com/",
    "activeDirectoryGraphResourceId": "https://graph.windows.net/",
    "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
    "galleryEndpointUrl": "https://gallery.azure.com/",
    "managementEndpointUrl": "https://management.core.windows.net/"
}
```

#### Adding a new Azure account to MASH via client CLI

The command to add an Azure account to MASH is:

```bash
mash account azure add \
  --name {account_name} \
  --region {region_name} \
  --source-container {container_name} \
  --source-resource-group {resource_group_name} \
  --source-storage-account {storage_account_name} \
  --credentials /path/to/json/creds.json
```

### Creating GCP accounts

MASH uses service accounts for GCE authentication. The service accounts are
specific to a single project. For more info on service accounts see the
[Google documentation](https://cloud.google.com/compute/docs/access/service-accounts).

To setup credentials for any project the following steps can be used where
service account id is the name chosen for the new account, project id is the
project where the credentials are being created and bucket name is the bucket
where the image files/archives will be uploaded:

```bash
$ gcloud --project={project-id} iam service-accounts create {service-account-id}

$ gcloud --project={project-id} iam service-accounts \
  keys create {service-account-id}-key.json \
  --iam-account {service-account-id}@{project-id}.iam.gserviceaccount.com

$ gcloud projects add-iam-policy-binding {project-id} \
  --member serviceAccount:{service-account-id}@{project-id}.iam.gserviceaccount.com \
  --role roles/compute.instanceAdmin.v1

$ gcloud projects add-iam-policy-binding {project-id} \
  --member serviceAccount:{service-account-id}@{project-id}.iam.gserviceaccount.com \
  --role roles/iam.serviceAccountUser


$ gcloud projects add-iam-policy-binding {project-id} \
  --member serviceAccount:{service-account-id}@{project-id}.iam.gserviceaccount.com \
  --role roles/compute.viewer

$ gsutil iam ch serviceAccount:{service-account-id}@{project-id}.iam.gserviceaccount.com:admin gs://{bucket-name}
```

The json file generated by the second command “{service-account-id}-key.json”
is used for GCE authentication.

__Setup a service account with Google Cloud Console__

To create a service account in the Cloud Console log in at
https://cloud.google.com/compute/.

1. Once logged in click the __Go to console__ button.
1. From the console expand the menu via the hamburger button.
1. Open the __IAM & admin__ tab.
1. Click the __Service accounts__ page.
1. Click the __Select a project__ menu on the top navigation bar
(next to __Google Cloud Platform__).
1. Select your project and click __Open__.
1. Click __Create Service Account__.
1. Enter a service account name, service account ID and an optional description.
1. Click __Create__.
1. Click __Select a role__ dropdown.
1. Find and select "Compute Instance Admin (v1)"
1. Select __ADD ANOTHER ROLE__.
1. Click __Select a role__ dropdown.
1. Find and select "Service Account User"
1. Click __Continue__.
1. Click __CREATE KEY__.
1. Choose key type "JSON".
1. Click __CREATE__.
1. Save file which contains a private key.
1. Accept the notification by clicking __CLOSE__.
1. Click __DONE__.
1. Expand the menu via the hamburger button.
1. Select __Storage__.
1. Find the bucket name which maps to the project from the table above and
click the name.
1. Click the __Permissions__ tab.
1. Click __Add members__.
1. In the __New Members__ field paste the full service account ID which looks
like an email.
1. Click __Select a role__.
1. Find and select "Storage Admin".
1. Click __SAVE__.

__Adding a new GCE account to MASH via client CLI__

The command to add a GCE account from mash-client is:

```bash
mash account gce add \
  --name {account_name} \
  --zone {gce_zone} \
  --bucket {storage_bucket_name} \
  --credentials /path/to/service/account/file.json
```

Publishing projects in GCE do not have permissions to create new instances
for testing. Therefore for any publishing projects a set of testing
credentials is required for launching and testing images. To add a publishing
project with a testing account configured there are two more arguments in the
command line:

```bash
mash account gce add \
  --name {account_name} \
  --zone {gce_zone} \
  --bucket {storage_bucket_name} \
  --is-publishing-account \
  --testing-account {testing_acnt_name} \
  --credentials /path/to/service/account/file.json
```

Example service account JSON file:

```json
{
    "type": "service_account",
    "project_id": "<project ID>",
    "private_key_id": "<private key ID>",
    "private_key": "<private key>",
    "client_email": "<client email>",
    "client_id": "<client ID>",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://accounts.google.com/o/oauth2/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/<client email>"
}
```

__GCE role definitions__

Compute Instance Admin (v1) Role
([roles/compute.instanceAdmin.v1](https://cloud.google.com/compute/docs/access/iam#compute.instanceAdmin.v1))

Service Account User Role
([roles/iam.serviceAccountUser](https://cloud.google.com/compute/docs/access/iam#iam.serviceAccountUser))

Storage Admin Role
([roles/compute.storageAdmin](https://cloud.google.com/compute/docs/access/iam#compute.storageAdmin))

__More info__

Creating and enabling service accounts:
[create-enable-service-accounts-for-instances](https://cloud.google.com/compute/docs/access/create-enable-service-accounts-for-instances)

Create a new JSON private key:
[creating-managing-service-account-keys](https://cloud.google.com/iam/docs/creating-managing-service-account-keys)

Granting roles:
[granting-roles-to-service-accounts](https://cloud.google.com/iam/docs/granting-roles-to-service-accounts)

### Job doc arguments

Mash uses "job docs" for submitting new jobs to the server. The job docs are
json files that contain the necessary information to process a job. There are
a few options to get job doc arguments/options from the client:

- `mash job {cloud} schema` or `mash job {cloud} schema --annotated`: Returns
an annotated json string with all the possible arguments for a job doc based
on the cloud framework.
- `mash job {cloud} schema --json`: Returns an empty json string with all the
possible arguments that can be copied to start a job doc.
- `mash job {cloud} schema --raw`: Returns the raw json schema which is used
by the server to validate job docs for the given cloud framework.

### Submitting jobs

When you have a valid job doc you can submit it to the pipeline:

```
mash job {cloud} add /path/to/job.json
```

### Checking job status

To see the status of a running or finished job the following commands exist:

```
mash job status --job-id {job_id}
mash job info --job-id {job_id}
```

## Requirements

See [.virtualenv.requirements.txt](https://github.com/SUSE-Enceladus/mash/.virtualenv.requirements.txt)

## Service Design

The implementation of the Mash is based on a collection of services. Each service completes
an individual task of the process. At present the following services exist:

- __Download service__:

  Images are built in a build service or provided from some other source. The
  download service currently relies on [OBS](https://openbuildservice.org/) or
  a storage solution (S3 bucket) to provide the image files.
  For OBS, the service can validate that a compute image in OBS meets certain
  conditions. When conditions are met the image is downloaded locally.
  For S3 buckets, the images are downloaded directly from the S3 bucket.

The remaining services have cloud framework specific implementations. The services
handle communication via a centralized message broker. By default MASH has been
configured and tested using RabbitMQ. These core services for image automation are
chained in a series. As a job finishes in one service it moves to the next service.

- __Upload service__:

  Uploads an image file/archive to the cloud service provider.

- __Create service__:

  Creates and registers a public cloud compute image in the cloud
  service provider.

- __Test service__:

  Runs an instance of a given image and performs a suite of tests to
  validate the state of the image. This service leverages
  [img-proof](https://github.com/SUSE-Enceladus/img-proof)
  for the testing.

- __Raw Image upload service__:

  Uploads the raw image file/archive to a storage bucket.

- __Replicate service__:

  Duplicates or copies the newly created compute image to all 
  available regions.

- __Publish service__:

  Makes a compute image publically available.

  __NOTE__:
   the publish implementation does not fully cover all registrations
   into the cloud service provider marketplaces.

- __Deprecate service__:

  Deprecates a compute image depending on the cloud service provider.

Aside from the core services there 3 other HTTP services (Flask API):

- __Rest API__:

  Provides a public interface for interacting with Mash. It also validates the jobs
  Prior to sending them to the orchestrator for scheduling.

- __Credentials__:

  Handles storing, verifying and handing out cloud framework credentials for
  jobs in the pipeline.

- __Database__:

  Handles storage, deletion and retrieval of data from a relational database.

As mentioned there is a service that works as an orchestrator:

- __JobCreator__:

  This service sends out information about jobs as they enter the system. It
  organizes the information based on cloud framework and initiates the
  job in the pipeline.

Finally, there is a centralized logger:

- __Logger__:

  The logger service acts as a log aggregator and organizes all logs
  into service and/or job specific locations.

For more information on individual services see the docs.

## Issues/Enhancements

Please submit issues and requests to
[Github](https://github.com/SUSE-Enceladus/mash/issues).

## Contributing

Contributions to MASH are welcome and encouraged. See
[CONTRIBUTING](CONTRIBUTING.md) for info on getting started.

## Development

### Making & Propagating DB changes

__Note__: To create DB migrations a running database is required and should be
configured in Mash config.

#### Create database migration:

1. After changes have been made and finalized to the DB models ensure you are
in the mash/mash/services/database directory.
1. Create a new migration using `flask db migrate -m "<Short message describing changes>"`.
1. This new migration should look like
mash/mash/services/database/migrations/versions/{migration_name}.py.
1. All new migrations are committed to the repository.
1. To apply the migration locally run flask db upgrade.

#### Creating a single migration for testing with a sqlite DB:

1. On a test instance navigate to the /var/lib/mash/database directory.
1. Remove the existing migrations with `rm -rf migrations`.
1. Initialize a new migrations directory: `flask db init`.
1. Create a new single migration: `flask db migrate -m "single migration for testing"`.
1. Finally, apply the migration on the default sqlite database: `flask db upgrade`.

### Making API changes

#### Enable openAPI documentation in development mode

1. Open the extensions module "mash/mash/services/api/extensions.py".
1. Find the line that contains "doc=False,".
1. Comment out this line and start the API.
1. Either `flask run --port 5005` or `python wsgi.py` will start the server on
port 5005.
1. Direct browser to localhost:5005 and you should see the openAPI docs.

__Note__: Ensure you remove the comment in extensions.py prior to committing
any code.

### Prune expired user tokens

1. To prune tokens in development first go to the database service directory
/path-to-code/mash/services/database/.
1. Now run the `flask tokens cleanup` command.
1. A message will be displayed with the number of tokens deleted.

### Hot-swap API changes in Apache2

If a change is deployed to any of the Mash API services
(API, Credentials, Database) the API which runs on Apache2 can be hot-swapped
without downtime.

Service locations:

```
/var/lib/mash/ (API)
/var/lib/mash/credentials/ (creds)
/var/lib/mash/database/ (db)
```

1. Navigate to the directory where the relevant wsgi file exists
1. Run `touch wsgi.py`

This triggers Apache2 to reload the wsgi file which will pull in any changes
that have been made to the Mash code in site-packages.

### New API Versions

When an existing route requires a change it should be done in the next API
version. For example if "get user" has a change and the latest version is v1
then the next version would be v2. The version artifacts are split up into sub
directories based on version name. Any existing artifacts such as schema or
response types can be referenced from previous version if no changes are
needed. This prevents unnecessary duplication. The new routes should be
structured similar to the existing routes and the new namespace should be
added to the app configuration in the constructor (/mash/services/api/app.py).
For any net new routes or new optional arguments to existing routes the
existing version can be used as this is a non-breaking change.

The only route which has no version is the API spec. This route provides the
openAPI spec which is used to host the Swagger based API docs.

## License

Copyright (c) 2023 SUSE LLC.

Distributed under the terms of GPL-3.0+ license, see
[LICENSE](LICENSE) for details.
