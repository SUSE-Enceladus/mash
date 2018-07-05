import pytest

from mash.mash_exceptions import MashConfigException
from mash.services import get_configuration

from mash.services.credentials.config import CredentialsConfig
from mash.services.deprecation.config import DeprecationConfig
from mash.services.jobcreator.config import JobCreatorConfig
from mash.services.logger.config import LoggerConfig
from mash.services.obs.config import OBSConfig
from mash.services.publisher.config import PublisherConfig
from mash.services.replication.config import ReplicationConfig
from mash.services.testing.config import TestingConfig
from mash.services.uploader.config import UploaderConfig


@pytest.mark.parametrize(
    'service,class_type',
    [
        ('credentials', CredentialsConfig),
        ('deprecation', DeprecationConfig),
        ('jobcreator', JobCreatorConfig),
        ('logger', LoggerConfig),
        ('obs', OBSConfig),
        ('publisher', PublisherConfig),
        ('replication', ReplicationConfig),
        ('testing', TestingConfig),
        ('uploader', UploaderConfig)
    ]
)
def test_get_configuration(service, class_type):
    config = get_configuration(service)
    assert type(config) == class_type


def test_invalid_configuration():
    with pytest.raises(MashConfigException) as error:
        get_configuration('fake')

    assert str(error.value) == 'No configuration available for fake service.'
