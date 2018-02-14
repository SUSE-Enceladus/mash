from pytest import raises
from unittest.mock import patch

from mash.mash_exceptions import MashReplicationException
from mash.services.replication_service import main


class TestReplicationServiceMain(object):
    @patch('mash.services.replication_service.ReplicationService')
    def test_replication_main(self, mock_replication_service):
        main()
        mock_replication_service.assert_called_once_with(
            host='localhost', service_exchange='replication',
        )

    @patch('mash.services.replication_service.ReplicationService')
    @patch('sys.exit')
    def test_replication_main_mash_error(
        self, mock_exit, mock_replication_service
    ):
        mock_replication_service.side_effect = MashReplicationException(
            'error'
        )

        main()
        mock_replication_service.assert_called_once_with(
            host='localhost', service_exchange='replication',
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.replication_service.ReplicationService')
    @patch('sys.exit')
    def test_replication_main_system_exit(
        self, mock_exit, mock_replication_service
    ):
        mock_replication_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(
            mock_replication_service.side_effect
        )

    @patch('mash.services.replication_service.ReplicationService')
    def test_replication_main_unexpected_error(self, mock_replication_service):
        mock_replication_service.side_effect = Exception('Error!')

        with raises(Exception):
            main()
