from pytest import raises
from unittest.mock import patch

from mash.mash_exceptions import (
    MashJobCreatorException
)
from mash.services.jobcreator import create_job


def test_job_creator_create_job():
    # invalid cloud
    with raises(MashJobCreatorException) as error:
        create_job({'cloud': 'fake'})

    assert str(error.value) == \
        'Support for fake Cloud Service not implemented'


@patch('builtins.__import__')
def test_job_creator_create_job_oci_missing_package(mock_import):
    real_import = __import__

    def side_effect(name, *args, **kwargs):
        if name == 'oci':
            raise ImportError("Mocked ImportError")
        return real_import(name, *args, **kwargs)

    mock_import.side_effect = side_effect

    with raises(MashJobCreatorException) as error:
        create_job({'cloud': 'oci'})

    assert "missing 'oci' package" in str(error.value)
