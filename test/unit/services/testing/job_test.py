from amqpstorm import AMQPError
from pytest import raises
from unittest.mock import MagicMock, Mock, patch

from mash.mash_exceptions import MashTestingException
from mash.services.testing.job import TestingJob


class TestTestingJob(object):
    def setup(self):
        self.job_config = {
            'distro': 'SLES',
            'id': '1',
            'provider': 'EC2',
            'tests': 'test_stuff',
            'utctime': 'now'
        }

    def test_valid_job(self):
        job = TestingJob(**self.job_config)

        assert job.id == '1'
        assert job.provider == 'EC2'
        assert job.tests == ['test_stuff']
        assert job.utctime == 'now'

    def test_bind_credential_queue(self):
        queue = 'credentials.testing.1'

        job = TestingJob(**self.job_config)
        channel = Mock()
        job.channel = channel

        job._bind_credential_queue()
        channel.queue.declare.assert_called_once_with(
            queue=queue,
            durable=True
        )
        channel.queue.bind.assert_called_once_with(
            exchange='testing',
            queue=queue,
            routing_key=queue
        )

    def test_close_connection(self):
        job = TestingJob(**self.job_config)
        channel = Mock()
        channel.is_open = True
        connection = Mock()
        connection.is_open = True

        job.channel = channel
        job.connection = connection

        job._close_connection()
        channel.close.assert_called_once_with()
        connection.close.assert_called_once_with()

    def test_get_credential_request(self):
        job = TestingJob(**self.job_config)
        with raises(NotImplementedError):
            job._get_credential_request()

    @patch.object(TestingJob, '_open_connection')
    @patch.object(TestingJob, '_bind_credential_queue')
    @patch.object(TestingJob, '_get_credential_request')
    @patch.object(TestingJob, '_wait_for_credentials')
    @patch.object(TestingJob, '_close_connection')
    @patch.object(TestingJob, '_process_credentials')
    def test_get_credentials(
        self, mock_process_creds, mock_close_connection, mock_wait_for_creds,
        mock_get_cred_request, mock_bind_cred_queue, mock_open_connection
    ):
        mock_get_cred_request.return_value = 'eyJzb21lIjoicGF5bG9hZCJ9'
        mock_wait_for_creds.return_value = 'eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp'

        job = TestingJob(**self.job_config)
        channel = Mock()
        job.channel = channel

        job._get_credentials('localhost')

        mock_open_connection.assert_called_once_with('localhost')
        channel.basic.publish.assert_called_once_with(
            'eyJzb21lIjoicGF5bG9hZCJ9',
            'request',
            exchange='credentials'
        )
        channel.queue.delete.assert_called_once_with(
            queue='credentials.testing.1'
        )
        mock_process_creds.assert_called_once_with(
            'eyJhbGciOiJIUzI1NiIsInR5cCI6Ikp'
        )

    @patch.object(TestingJob, '_open_connection')
    @patch.object(TestingJob, '_bind_credential_queue')
    @patch.object(TestingJob, '_get_credential_request')
    def test_get_credentials_exception(
        self, mock_get_cred_request, mock_bind_cred_queue, mock_open_connection
    ):
        job = TestingJob(**self.job_config)
        channel = Mock()
        channel.basic.publish.side_effect = AMQPError()
        job.channel = channel

        with raises(MashTestingException) as e:
            job._get_credentials('localhost')

        assert 'Credentials message not received by RabbitMQ.' == str(e.value)

    def test_job_get_metadata(self):
        job = TestingJob(**self.job_config)
        metadata = job.get_metadata()
        assert metadata == {'job_id': '1'}

    @patch('mash.services.testing.job.Connection')
    def test_open_connection(
        self, mock_connection
    ):
        connection = Mock()
        channel = Mock()
        connection.channel.return_value = channel
        mock_connection.return_value = connection

        job = TestingJob(**self.job_config)
        job._open_connection('localhost')

        channel.confirm_deliveries.assert_called_once_with()

    def test_process_credentials(self):
        job = TestingJob(**self.job_config)
        with raises(NotImplementedError):
            job._process_credentials('creds')

    def test_wait_for_credentials(self):
        job = TestingJob(**self.job_config)

        channel = Mock()
        message = MagicMock(body='body')
        channel.basic.get.return_value = message
        job.channel = channel

        body = job._wait_for_credentials()
        message.ack.assert_called_once_with()
        assert body == 'body'

    @patch('mash.services.testing.job.time')
    def test_wait_for_credentials_timeout(self, mock_sleep):
        job = TestingJob(**self.job_config)
        channel = Mock()
        channel.basic.get.return_value = None

        job.channel = channel

        msg = 'Credentials message not received from credential service.'
        with raises(MashTestingException) as e:
            job._wait_for_credentials()

        assert msg == str(e.value)

    def test_run_tests(self):
        job = TestingJob(**self.job_config)
        with raises(NotImplementedError):
            job._run_tests()

    def test_set_log_callback(self):
        job = TestingJob(**self.job_config)
        callback = Mock()
        job.set_log_callback(callback)

        assert job.log_callback == callback

    @patch.object(TestingJob, '_get_credentials')
    @patch.object(TestingJob, '_run_tests')
    def test_test_image(self, mock_run_tests, mock_get_creds):
        job = TestingJob(**self.job_config)
        job.log_callback = Mock()
        job.test_image('localhost')

        job.log_callback.assert_called_once_with(
            'Pass[1]: Running IPA tests against image.',
            {'job_id': '1'}
        )

    def test_invalid_distro(self):
        self.job_config['distro'] = 'Fake'
        msg = 'Distro: Fake not supported.'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg

    def test_invalid_provider(self):
        self.job_config['provider'] = 'Fake'
        msg = 'Provider: Fake not supported.'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg

    def test_invalid_tests(self):
        self.job_config['tests'] = ''
        msg = 'Must provide at least one test.'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg

        self.job_config['tests'] = ['test_stuff']
        msg = 'Invalid tests format, must be a comma seperated list.'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg

    def test_invalid_timestamp(self):
        self.job_config['utctime'] = 'never'
        msg = 'Invalid utctime format: Unknown string format'
        with raises(MashTestingException) as e:
            TestingJob(**self.job_config)

        assert str(e.value) == msg
