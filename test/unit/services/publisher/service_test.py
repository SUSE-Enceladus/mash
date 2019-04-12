from unittest.mock import patch

from mash.services.mash_service import MashService
from mash.services.publisher.service import PublisherService


class TestPublisherService(object):

    @patch.object(MashService, '__init__')
    def test_publisher_service(self, mock_base_init):
        mock_base_init.return_value = None
        PublisherService()
