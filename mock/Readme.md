
# Intro

This directory contains the required elements to mock the mash api to get your
desired output for testing.

# Mock

This mock is based on [Mockintosh](https://github.com/up9inc/mockintosh), an 
open source framework designed to mock APIs in microservices environments.

All the files required to run the mock are included in this directory. The 
recommended procedure to set up the mock is to run mockintosh as a container
in the container runtime engine of your choice. The examples provided use
'podman' as reference.

This directory provides:
- `launch_mock.sh`: script that runs the mockintosh container with podman and
makes the mock available in port 8000 of localhost.
- `launch_tests.sh`: Example requests with curl for every endpoint.
- `mash_mockintosh_config.yaml`: Configuration file for mockintosh to mock the
API.
- `templates`: Directory containing the jinja templates for the endpoint 
responses.

_Things that have to be taken into account with the mock_:
- Authentication is not validated, the mock just checks the Authorization
header is include with some value (any value is valid).
- The Oauth endpoints in the API have not been implemented in the mock.


## How to run the mock

To set up the mock, we can run the `testrio/mockintosh` container, mounting the 
directory where the configuration file is held in some directory inside the 
container (`/tmp` in the example), and pass the configuration file as an 
argument to mockintosh:

```sh
sudo podman run -it \
   -p 8000-8005:8000-8005 \
   -v `pwd`:/tmp/ \
   testrio/mockintosh \
   /tmp/mash_mockintosh_config.yaml
```

By default, the fake API is listening in the port 8000.

The configuration file also exposes a management interface where the behavior
of the mock can be modified (or stats of usage can be checked). In the 
mockintosh configuration file provided, the management interface is exposed
under the `__admin` path, so the url is `http://localhost:8000/__admin`.

## How to modify the behavior of the mock

In mockintosh, the behavior of the mock is defined with a yaml configuration
file. In this configuration file (`mash_mockintosh_config.yaml` in our case),
the different endpoints mocked are defined and the response is build by means
of [Jinja](https://jinja.palletsprojects.com/en/3.1.x/) templates.

The mash mock template responses are held in the `templates` directory and can
be modified easily to meet your needs.