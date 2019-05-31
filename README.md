[![Build Status](https://travis-ci.com/SUSE-Enceladus/mash.svg?branch=master)](https://travis-ci.com/SUSE-Enceladus/mash)

# Mash - Public Cloud Release Tool

MASH provides a set of Python3 service based processes for Image Release
automation into the Public Cloud Frameworks. Amazon EC2, Google Compute Engine
and Microsoft Azure are currently supported.

Images can be built, uploaded, tested and published. A job can be
started based on a number of different conditions such as datetime and
package versions.

The services work asynchronously and handle communication via a centralized
message broker. By default MASH has been configured and tested with RabbitMQ.
The core services for image uploading, testing and publishing are in a chained
pipeline. As a job finishes in one service it moves to the next in line. The
following services are part of the pipeline:

- OBS (image build service)
- Uploader
- Testing
- Replication
- Publisher
- Deprecation

Aside from pipeline services there 4 other helper services:

- __Rest API__:

  Jobs are validated by the API which uses Flask to serve a REST API.

- __JobCreator__:

  Valid jobs move to the JobCreator service which initially sends the job to
  credentials service for account validation. If the credentials all check out
  the JobCreator service generates the necessary messages and initiates the
  job in the pipeline.

- __Credentials__:

  Handles storing, verifying and handing out cloud framework credentials for
  jobs in the pipeline.

- __Logger__:

  Finally, the logger service acts as a log aggregator and organizes all logs
  into service and/or job specific locations.

For more information on individual services see the docs.

## Installation

Development repo:

```
$ zypper ar http://download.opensuse.org/repositories/Cloud:/Tools/<distribution>
```

Stable repo:

```
$ zypper ar http://download.opensuse.org/repositories/Cloud:/Tools:/CI/<distribution>
```

Refresh & install:

```
$ zypper refresh
$ zypper in mash
```

## Requirements

- adal
- apache-libcloud
- azure-mgmt-compute
- azure-mgmt-resource
- azure-mgmt-storage
- azure-storage
- flask
- setuptools
- idna<2.7
- boto3
- cryptography>=2.2.0
- jsonschema
- PyYAML
- PyJWT
- APScheduler
- python-dateutil>=2.6.0,<3.0.0
- amqpstorm
- ec2imgutils
- img-proof>=4.0.0
- lxml
- requests

## Issues/Enhancements

Please submit issues and requests to
[Github](https://github.com/SUSE-Enceladus/mash/issues).

## Contributing

Contributions to MASH are welcome and encouraged. See
[CONTRIBUTING](CONTRIBUTING.md) for info on getting started.

## License

Copyright (c) 2019 SUSE LLC.

Distributed under the terms of GPL-3.0+ license, see
[LICENSE](LICENSE) for details.
