from pytest import raises

from mash.mash_exceptions import (
    MashJobCreatorException
)
from mash.services.jobcreator import create_job


def test_job_creator_create_job():
    # invalid cloud
    with raises(MashJobCreatorException) as error:
        create_job({'cloud': 'fake'}, {}, {})

    assert str(error.value) == \
        'Support for fake Cloud Service not implemented'
