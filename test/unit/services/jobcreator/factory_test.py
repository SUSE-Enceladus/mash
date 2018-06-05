from pytest import raises
from unittest.mock import patch

from mash.mash_exceptions import (
    MashJobCreatorException,
    MashValidationException
)
from mash.services.jobcreator import create_job


@patch('mash.services.jobcreator.validate')
def test_job_creator_create_job(mock_validate):
    # invalid provider
    with raises(MashJobCreatorException) as error:
        create_job({'provider': 'fake'}, {}, {})

    assert str(error.value) == \
        'Support for fake Cloud Service not implemented'

    mock_validate.side_effect = MashValidationException(
        'Validation failed for provided job doc.'
    )

    # invalid job doc
    with raises(MashValidationException) as error:
        create_job({'provider': 'ec2'}, {}, {'ec2': {}})

    assert str(error.value) == \
        'Validation failed for provided job doc.'
