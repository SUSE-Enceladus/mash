from pytest import raises

from mash.mash_exceptions import (
    MashJobCreatorException
)
from mash.services.jobcreator import create_job


def test_job_creator_create_job():
    # invalid provider
    with raises(MashJobCreatorException) as error:
        create_job('123', {'provider': 'fake'}, {}, {})

    assert str(error.value) == \
        'Support for fake Cloud Service not implemented'
