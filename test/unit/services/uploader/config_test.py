from pytest import raises
from test.unit.test_helper import patch_open

from mash.mash_exceptions import MashConfigException
from mash.services.uploader.config import UploaderConfig


class TestUploaderConfig(object):
    def setup(self):
        self.config = UploaderConfig(
            '../data/mash_config.yaml'
        )
        self.config_defaults = UploaderConfig(
            '../data/empty_mash_config.yaml'
        )

    @patch_open
    def test_init_error(self, mock_open):
        mock_open.side_effect = Exception
        with raises(MashConfigException):
            UploaderConfig('../data/mash_config.yaml')
