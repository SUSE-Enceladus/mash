## Dev Requirements

See [.virtualenv.dev-requirements.txt](https://github.com/SUSE-Enceladus/mash/.virtualenv.dev-requirements.txt)

## Contribution Checklist

- All patches must be signed. [Signing Commits](#signing-commits)
- All contributed code must conform to flake8. [Code Style](#code-style)
- All new code contributions must be accompanied by a test.
    - Tests must pass and coverage remain at 100%. [Unit & Integration Tests](#unit-&-integration-tests)
- Follow Semantic Versioning. [Versions & Releases](#versions-&-releases)


## Versions & Releases

MASH adheres to Semantic versioning; see http://semver.org/ for details.

bumpversion is used for release version management, and is configured in
setup.cfg:

```
$ bumpversion major|minor|patch
$ git push
```

Bumpversion will create a commit with version updated in all locations.
The annotated tag is created separately.

```
$ git tag -a v{version}
# git tag -a v0.0.1

# Create a message with the changes since last release and push tags.
$ git push --tags
```

## Unit & Integration Tests

All tests should pass and test coverage should remain at 100%.

The tests and coverage can be run directly via pytest.

```
$ cd test/unit/
$ pytest --cov=mash
```

## Code Style

Source should pass flake8 and pycodestyle standards.

```
$ flake8 mash
```

## Tox

The Python project uses `tox` to setup a development environment
for the desired Python version.

The following procedure describes how to create such an environment:

1.  Let tox create the virtual environment(s):

    ```
    $ tox
    ```

2.  Activate the virtual environment

    ```
    $ source .tox/3/bin/activate
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
run `source .tox/3/bin/activate` again. Skip step 3 and 4 as
the requirements are already installed.

## Signing Commits

The repository and the code base patches sent for inclusion must be GPG
signed. See the GitHub article,
[Signing commits using GPG](https://help.github.com/articles/signing-commits-using-gpg/),
for more information.
