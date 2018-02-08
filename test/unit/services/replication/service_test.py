from pytest import raises
from unittest.mock import patch, MagicMock, Mock

from mash.services.base_service import BaseService
from mash.services.replication.service import ReplicationService


class TestReplicationService(object):

    @patch.object(BaseService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None

        self.config = Mock()
        self.config.config_data = None
        self.channel = Mock()
        self.channel.basic_ack.return_value = None
        self.channel.consumer_tags = []

        self.tag = Mock()
        self.method = {'delivery_tag': self.tag}

        self.message = MagicMock(
            channel=self.channel,
            method=self.method,
        )

        self.replication = ReplicationService()
        self.replication.jobs = {}
        self.replication.log = Mock()
        self.replication.channel = self.channel
        self.replication.service_exchange = 'replication'
        self.replication.service_queue = 'service'
        self.replication.job_document_key = 'job_document'

    @patch.object(ReplicationService, 'set_logfile')
    @patch.object(ReplicationService, 'start')
    @patch('mash.services.replication.service.ReplicationConfig')
    def test_replication_post_init(
        self, mock_replication_config, mock_start,
        mock_set_logfile
    ):
        mock_replication_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/replication_service.log'

        self.replication.post_init()

        self.config.get_log_file.assert_called_once_with()
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/replication_service.log'
        )
        mock_start.assert_called_once_with()

    @patch.object(ReplicationService, 'stop')
    def test_replication_start(self, mock_stop):
        self.replication.start()
        self.channel.start_consuming.assert_called_once_with()
        mock_stop.assert_called_once_with()

    @patch.object(ReplicationService, 'stop')
    @patch.object(ReplicationService, '_open_connection')
    def test_replication_start_exception(
        self, mock_open_connection, mock_stop
    ):
        self.channel.start_consuming.side_effect = KeyboardInterrupt()
        self.replication.start()

        mock_stop.assert_called_once_with()
        mock_stop.reset_mock()
        self.channel.start_consuming.side_effect = Exception(
            'Cannot start consuming.'
        )

        with raises(Exception) as error:
            self.replication.start()
        assert 'Cannot start consuming.' == str(error.value)

    @patch.object(ReplicationService, 'close_connection')
    def test_replication_stop(self, mock_close_connection):
        self.replication.stop()
        self.replication.channel.stop_consuming.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
