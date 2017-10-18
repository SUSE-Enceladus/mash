# Mash - Public Cloud Release Tool

[![Build Status](https://travis-ci.com/SUSE/mash.svg?branch=master)](https://travis-ci.com/SUSE/mash)

Service based Process for Image Release automation into
the Public Cloud Systems from Amazon EC2, Google Compute Engine and
Microsoft Azure

## Contents

  * [Contributing](#contributing)

## Contributing

The Python project uses `tox` to setup a development environment
for the desired Python version.

The following procedure describes how to create such an environment:

1.  Let tox create the virtual environment(s):

    ```
    $ tox
    ```

2.  Activate the virtual environment of your choice

    ```
    $ source .tox/2.7/bin/activate
    ```

3.  Install requirements inside the virtual environment:

    ```
    $ pip install -U pip setuptools
    $ pip install -r .virtualenv.dev-requirements.txt
    ```

4.  Let setuptools create/update your entrypoints

    ```
    $ ./setup.py develop
    ```

Once the development environment is activated and initialized with
the project required Python modules, you are ready to work.

In order to leave the development mode just call:

```
$ deactivate
```

To resume your work, change into your local Git repository and
run `source .tox/2.7/bin/activate` again. Skip step 3 and 4 as
the requirements are already installed.
