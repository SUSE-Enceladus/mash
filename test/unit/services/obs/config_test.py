from pytest import raises
from test.unit.test_helper import patch_open

from mash.mash_exceptions import MashConfigException
from mash.services.obs.config import OBSConfig


class TestOBSConfig(object):
    def setup(self):
        self.config = OBSConfig('../data/mash_config.yaml')
        self.config_defaults = OBSConfig('../data/empty_mash_config.yaml')

    @patch_open
    def test_init_error(self, mock_open):
        mock_open.side_effect = Exception
        with raises(MashConfigException):
            OBSConfig('../data/mash_config.yaml')

    def test_get_log_file(self):
        assert self.config.get_log_file('obs') == \
            '/tmp/log/obs_service.log'
        assert self.config_defaults.get_log_file('obs') == \
            '/var/log/mash/obs_service.log'

    def test_get_download_directory(self):
        assert self.config.get_download_directory() == '/images'
        assert self.config_defaults.get_download_directory() == '/var/lib/mash/images/'
