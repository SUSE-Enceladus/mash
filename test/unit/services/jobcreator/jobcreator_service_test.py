from pytest import raises
from unittest.mock import MagicMock, Mock, patch

from amqpstorm import AMQPError

from mash.services.base_service import BaseService
from mash.services.jobcreator.service import JobCreatorService


class TestJobCreatorService(object):

    @patch.object(BaseService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None
        self.config = Mock()
        self.config.config_data = None
        self.channel = Mock()
        self.channel.basic_ack.return_value = None

        self.tag = Mock()
        self.method = {'delivery_tag': self.tag}

        self.message = MagicMock(
            channel=self.channel,
            method=self.method,
        )

        self.jobcreator = JobCreatorService()
        self.jobcreator.log = Mock()
        self.jobcreator.service_exchange = 'jobcreator'

    @patch.object(JobCreatorService, 'set_logfile')
    @patch.object(JobCreatorService, 'stop')
    @patch.object(JobCreatorService, 'start')
    @patch('mash.services.jobcreator.service.JobCreatorConfig')
    @patch.object(JobCreatorService, '_bind_queue')
    @patch.object(JobCreatorService, '_process_message')
    @patch.object(JobCreatorService, 'consume_queue')
    def test_job_creator_post_init(
        self, mock_consume_queue, mock_process_message,
        mock_bind_queue, mock_jobcreator_config, mock_start, mock_stop,
        mock_set_logfile
    ):
        mock_jobcreator_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/job_creator_service.log'

        self.jobcreator.post_init()

        self.config.get_log_file.assert_called_once_with()
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/job_creator_service.log'
        )
        mock_consume_queue.assert_called_once_with(
            mock_process_message, mock_bind_queue.return_value
        )
        mock_bind_queue.assert_called_once_with('jobcreator', 'invalid_config')
        mock_start.assert_called_once_with()
        mock_stop.assert_called_once_with()

    @patch.object(JobCreatorService, 'stop')
    @patch.object(JobCreatorService, 'start')
    @patch('mash.services.jobcreator.service.JobCreatorConfig')
    @patch.object(JobCreatorService, '_bind_queue')
    @patch.object(JobCreatorService, '_process_message')
    @patch.object(JobCreatorService, 'consume_queue')
    def test_job_creator_post_init_exceptions(
        self, mock_consume_queue, mock_process_message,
        mock_bind_queue, mock_jobcreator_config, mock_start, mock_stop
    ):
        mock_jobcreator_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/job_creator_service.log'

        mock_start.side_effect = KeyboardInterrupt()

        self.jobcreator.post_init()

        mock_stop.assert_called_once_with()
        mock_start.side_effect = Exception()
        mock_stop.reset_mock()
        with raises(Exception):
            self.jobcreator.post_init()

        mock_stop.assert_called_once_with()

    def test_job_creator_proccess_message_invalid(self):
        self.method['routing_key'] = 'invalid_tag'
        self.message.body = 'A message.'
        self.jobcreator._process_message(self.message)

        self.message.ack.assert_called_once_with()
        self.jobcreator.log.warning.assert_called_once_with(
            'Received unknown message with key: invalid_tag. '
            'Message: A message.'
        )

    @patch.object(JobCreatorService, '_process_invalid_config')
    def test_job_creator_proccess_message_invalid_config(
        self, mock_invalid_config
    ):
        self.method['routing_key'] = 'invalid_config'
        self.jobcreator._process_message(self.message)

        mock_invalid_config.assert_called_once_with(self.message)

    def test_job_creator_proccess_invalid_config(self):
        self.method['routing_key'] = 'invalid_tag'
        self.message.body = 'A message.'
        self.jobcreator._process_invalid_config(self.message)

        self.message.ack.assert_called_once_with()

    def test_jobcreator_start(self):
        self.channel.consumer_tags = []
        self.jobcreator.channel = self.channel

        self.jobcreator.start()
        self.channel.start_consuming.assert_called_once_with()

    @patch.object(JobCreatorService, '_open_connection')
    def test_jobcreator_start_exception(self, mock_open_connection):
        self.channel.start_consuming.side_effect = [AMQPError('Broken!'), None]
        self.channel.consumer_tags = []
        self.jobcreator.channel = self.channel

        self.jobcreator.start()
        self.jobcreator.log.warning.assert_called_once_with('Broken!')
        mock_open_connection.assert_called_once_with()

    @patch.object(JobCreatorService, 'close_connection')
    def test_jobcreator_stop(self, mock_close_connection):
        self.jobcreator.channel = self.channel

        self.jobcreator.stop()
        self.channel.stop_consuming.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
