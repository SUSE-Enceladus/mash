from unittest.mock import patch

from mash.services.mash_service import MashService
from mash.services.deprecation.service import DeprecationService


class TestDeprecationService(object):

    @patch.object(MashService, '__init__')
    def test_deprecation_service(self, mock_base_init):
        mock_base_init.return_value = None
        DeprecationService()
