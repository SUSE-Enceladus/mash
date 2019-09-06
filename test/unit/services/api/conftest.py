import pytest

from mash.services.api.app import create_app
from mash.services.api.config import Config


@pytest.fixture(scope='module')
def test_client():
    flask_config = Config(
        config_file='../data/mash_config.yaml',
        testing=True
    )
    application = create_app(flask_config)
    testing_client = application.test_client()

    ctx = application.app_context()
    ctx.push()

    yield testing_client
    ctx.pop()
