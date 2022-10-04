
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
be modified easily to meet your needs. The update procedure is the following:

1- Check, in [mash_mockintosh_config.yaml](mash_mockintosh_config.yaml) file, 
what is the template file that rules the response for the endpoint you are 
modifying. The template will be under the `response->body` section in the yaml
entry for the endpoint. 

`templates/jobs/gce/response_post_gce_job.json.j2` in the example below.

```
      # CREATE GCE JOB
      - path: "/v1/jobs/gce"
        method: POST
        headers:
          Authorization: "{{ regEx('.+') }}"
        body:
          schema:
            type: object
            properties:
              last_service:
                type: string
              utctime:
                type: string
              image:
                type: string
              download_url:
                type: string
              cloud_account:
                type: string
            required:
              - last_service
              - utctime
              - image
              - download_url
              - cloud_account
        response:
          status: 201
          headers:
            Content-Type: "application/json; charset=UTF-8"
          body: "@templates/jobs/gce/response_post_gce_job.json.j2"
```

The structure for the `templates` directory is the following, there's a
directory for each group of endpoints and then a subdirectory per cloud
provider (if it makes sense for the endpoint group):

```
templates/
├── accounts
│   ├── aliyun
│   ├── azure
│   ├── ec2
│   └── gce
├── auth
├── jobs
│   ├── aliyun
│   ├── azure
│   ├── ec2
│   ├── gce
└── user
```

2- Then go modify the template to match the modified behavior in the endpoint.
The format for the template is Jinja.

