from pytest import raises
from test.unit.test_helper import patch_open

from mash.mash_exceptions import MashConfigException
from mash.services.uploader.config import UploaderConfig


class TestUploaderConfig(object):
    def setup(self):
        self.config = UploaderConfig(
            '../data/uploader_config.yml'
        )
        self.config_defaults = UploaderConfig(
            '../data/uploader_config_empty.yml'
        )

    @patch_open
    def test_init_error(self, mock_open):
        mock_open.side_effect = Exception
        with raises(MashConfigException):
            UploaderConfig('../data/uploader_config.yml')

    def test_get_log_file(self):
        assert self.config.get_log_file() == '/tmp/foo.log'
        assert self.config_defaults.get_log_file() == \
            '/tmp/uploader_service.log'
