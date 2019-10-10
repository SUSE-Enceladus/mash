from unittest.mock import patch

from mash.services.api.app import create_app
from mash.services.api.config import Config
from mash.services.api.commands import tokens_cli

flask_config = Config(
    config_file='test/data/mash_config.yaml',
    testing=True
)
app = create_app(flask_config)


@patch('mash.services.api.commands.prune_expired_tokens')
def test_tokens_cleanup(mock_pruned_tokens):
    mock_pruned_tokens.return_value = 1

    runner = app.test_cli_runner()

    # Success
    result = runner.invoke(tokens_cli, ['cleanup'])
    assert 'Removed 1 expired token(s).' in result.output

    # Failure
    mock_pruned_tokens.side_effect = Exception('Access denied!')
    result = runner.invoke(tokens_cli, ['cleanup'])
    assert 'Unable to cleanup tokens: Access denied!' in result.output
