from pytest import raises
from .test_helper import patch_open

from mash.exceptions import MashConfigError
from mash.services.obs.config import OBSConfig


class TestOBSConfig(object):
    def setup(self):
        self.config = OBSConfig('../data/obs_config.yml')
        self.config_defaults = OBSConfig('../data/obs_config_empty.yml')

    @patch_open
    def test_init_error(self, mock_open):
        mock_open.side_effect = Exception
        with raises(MashConfigError):
            OBSConfig('../data/obs_config.yml')

    def test_get_log_port(self):
        assert self.config.get_log_port() == 8888
        assert self.config_defaults.get_log_port() == 9001

    def test_get_control_port(self):
        assert self.config.get_control_port() == 9999
        assert self.config_defaults.get_control_port() == 9000

    def test_get_log_file(self):
        assert self.config.get_log_file() == '/tmp/foo.log'
        assert self.config_defaults.get_log_file() == '/tmp/obs_service.log'

    def test_get_download_directory(self):
        assert self.config.get_download_directory() == '/images'
        assert self.config_defaults.get_download_directory() == '/tmp'
