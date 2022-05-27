![Continuous testing & Linting](https://github.com/SUSE-Enceladus/mash/workflows/Continuous%20testing%20&%20Linting/badge.svg?branch=master)

# Mash - Public Cloud Image Release Tool

MASH is an automated image testing & publishing tool for Public Cloud images.
It is written in Python3 and designed to run as a set of Systemd & HTTP
services. Mash currently supports a number of Public Cloud Frameworks; such
as Amazon EC2, Google Compute Engine and Microsoft Azure.

The following actions can be triggered for a given image:

- retrieval
- upload
- create
- test
- raw_image_upload (upload an image file to a storage bucket or coontainer)
- replicate (depending on the cloud framework)
- publish
- deprecate

The retrieval services currently relies on an [OBS](https://openbuildservice.org/)
style download server. This could be replaced by any other retrieval service
as desired.

The remaining services have cloud framework specific implementations. The services
handle communication via a centralized message broker. By default MASH has been
configured and tested using RabbitMQ. These core services for image automation are
chained in a series. As a job finishes in one service it moves to the next service.

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

## Installation

### openSUSE/SUSE package

The package can be found in the following repo:

```
$ zypper ar http://download.opensuse.org/repositories/Cloud:/Tools:/CI/<distribution>
```

To install Mash run the following commands:

```
$ zypper refresh
$ zypper in mash
```

### openSUSE Leap Container (in development)

There is a Podman container in development to simplify deployment. To pull down
and run the container use the following commands:

```
$ podman pull registry.opensuse.org/virtualization/appliances/images/images/opensuse/mash:latest
$ podman run --privileged -ti --network=host opensuse/mash
```

This will start the container and the default login information is:

user: masher
password: linux

The container image is maintained in the
[openSUSE build service](https://build.opensuse.org/package/show/Virtualization:Appliances:Images/mash-image-docker).

## Requirements

See [.virtualenv.requirements.txt](https://github.com/SUSE-Enceladus/mash/.virtualenv.requirements.txt)

## Issues/Enhancements

Please submit issues and requests to
[Github](https://github.com/SUSE-Enceladus/mash/issues).

## Contributing

Contributions to MASH are welcome and encouraged. See
[CONTRIBUTING](CONTRIBUTING.md) for info on getting started.

## License

Copyright (c) 2022 SUSE LLC.

Distributed under the terms of GPL-3.0+ license, see
[LICENSE](LICENSE) for details.
