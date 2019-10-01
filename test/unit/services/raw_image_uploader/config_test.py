from pytest import raises
from test.unit.test_helper import patch_open

from mash.mash_exceptions import MashConfigException
from mash.services.raw_image_uploader.config import RawImageUploaderConfig


class TestRawImagerUploaderConfig(object):
    def setup(self):
        self.config = RawImageUploaderConfig(
            '../data/mash_config.yaml'
        )
        self.config_defaults = RawImageUploaderConfig(
            '../data/empty_mash_config.yaml'
        )

    @patch_open
    def test_init_error(self, mock_open):
        mock_open.side_effect = Exception
        with raises(MashConfigException):
            RawImageUploaderConfig('../data/mash_config.yaml')
