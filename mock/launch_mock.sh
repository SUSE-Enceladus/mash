#!/bin/bash

sudo podman run -it \
   -p 8000-8005:8000-8005 \
   -v `pwd`:/tmp/ \
   testrio/mockintosh \
   /tmp/mash_mockintosh_config.yaml
