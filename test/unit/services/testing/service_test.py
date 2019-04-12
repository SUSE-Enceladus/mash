from unittest.mock import patch

from mash.services.mash_service import MashService
from mash.services.testing.service import TestingService


class TestIPATestingService(object):

    @patch.object(MashService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None
        self.testing = TestingService()
        self.testing.listener_msg_args = ['cloud_image_name']
        self.testing.status_msg_args = ['cloud_image_name']

    def test_testing_service_init(self):
        self.testing.service_init()
        assert 'source_regions' in self.testing.listener_msg_args
        assert 'source_regions' in self.testing.status_msg_args
