from unittest.mock import patch

from mash.services.mash_service import MashService
from mash.services.replication.service import ReplicationService


class TestReplicationService(object):

    @patch.object(MashService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None
        self.replication = ReplicationService()
        self.replication.listener_msg_args = ['cloud_image_name']

    def test_testing_service_init(self):
        self.replication.service_init()
        assert 'source_regions' in self.replication.listener_msg_args
