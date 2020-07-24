import pytest

from datetime import datetime
from unittest.mock import patch, Mock

from mash.services.database.app import create_app
from mash.services.database.flask_config import Config
from mash.services.database.commands import tokens_cli


@pytest.fixture(scope='module')
def test_app():
    flask_config = Config(
        config_file='test/data/mash_config.yaml',
        test=True
    )
    app = create_app(flask_config)

    ctx = app.app_context()
    ctx.push()

    yield app
    ctx.pop()


@patch('mash.services.database.utils.tokens.Token')
@patch('mash.services.database.utils.tokens.db')
def test_tokens_cleanup(mock_db, mock_token, test_app):
    queryset = Mock()
    queryset.delete.return_value = 1
    mock_token.query.filter.return_value = queryset
    mock_token.expires = datetime.now()

    runner = test_app.test_cli_runner()

    # Success
    result = runner.invoke(tokens_cli, ['cleanup'])
    assert 'Removed 1 expired token(s).' in result.output
    mock_db.session.commit.assert_called_once_with()

    # Failure
    mock_db.session.commit.side_effect = Exception('Access denied!')
    result = runner.invoke(tokens_cli, ['cleanup'])
    assert 'Unable to cleanup tokens: Access denied!' in result.output
