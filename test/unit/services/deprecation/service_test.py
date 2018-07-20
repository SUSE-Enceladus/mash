from pytest import raises
from unittest.mock import call, MagicMock, Mock, patch

from amqpstorm import AMQPError

from apscheduler.jobstores.base import ConflictingIdError, JobLookupError

from mash.services.base_service import BaseService
from mash.services.deprecation.service import DeprecationService
from mash.services.deprecation.ec2_job import EC2DeprecationJob

open_name = "builtins.open"


class TestDeprecationService(object):

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

        self.error_message = '{"deprecation_result": ' \
            '{"id": "1", "status": "error"}}'
        self.status_message = '{"deprecation_result": ' \
            '{"cloud_image_name": "image123", "id": "1", ' \
            '"status": "success"}}'

        self.publisher_result = \
            '{"publisher_result": {"id": "1", ' \
            '"cloud_image_name": "image name", ' \
            '"status": "success"}}'
        self.publisher_result_fail = \
            '{"publisher_result": {"id": "1", "status": "error"}}'

        self.deprecation = DeprecationService()
        self.deprecation.jobs = {}
        self.deprecation.log = Mock()

        scheduler = Mock()
        self.deprecation.scheduler = scheduler

        self.deprecation.service_exchange = 'deprecation'
        self.deprecation.service_queue = 'service'
        self.deprecation.listener_queue = 'listener'
        self.deprecation.job_document_key = 'job_document'

    @patch.object(DeprecationService, 'bind_credentials_queue')
    @patch.object(DeprecationService, 'restart_jobs')
    @patch.object(DeprecationService, 'set_logfile')
    @patch.object(DeprecationService, 'start')
    def test_deprecation_post_init(
        self, mock_start,
        mock_set_logfile, mock_restart_jobs, mock_bind_creds
    ):
        self.deprecation.config = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/deprecation_service.log'

        self.deprecation.post_init()

        self.config.get_log_file.assert_called_once_with('deprecation')
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/deprecation_service.log'
        )

        mock_bind_creds.assert_called_once_with()
        mock_restart_jobs.assert_called_once_with(self.deprecation._add_job)
        mock_start.assert_called_once_with()

    @patch.object(DeprecationService, '_create_job')
    def test_deprecation_add_job(self, mock_create_job):
        job_config = {
            'id': '1', 'provider': 'ec2', 'utctime': 'now',
        }

        self.deprecation._add_job(job_config)

        mock_create_job.assert_called_once_with(
            EC2DeprecationJob,
            job_config
        )

    def test_deprecation_add_job_exists(self):
        job = Mock()
        job.id = '1'
        self.deprecation.jobs['1'] = job
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'provider': 'ec2', 'utctime': 'now',
        }

        self.deprecation._add_job(job_config)
        self.deprecation.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': '1'}
        )

    def test_deprecation_add_job_invalid_provider(self):
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'provider': 'Provider', 'utctime': 'now',
        }

        self.deprecation._add_job(job_config)
        self.deprecation.log.exception.assert_called_once_with(
            'Provider Provider is not supported.'
        )

    @patch.object(DeprecationService, '_delete_job')
    @patch.object(DeprecationService, '_publish_message')
    def test_deprecation_cleanup_job(
        self, mock_publish_message, mock_delete_job
    ):
        self.deprecation.scheduler.remove_job.side_effect = JobLookupError('1')

        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.utctime = 'now'
        job.get_metadata.return_value = {'job_id': '1'}

        self.deprecation.jobs['1'] = job
        self.deprecation._cleanup_job(job, 1)

        self.deprecation.log.warning.assert_called_once_with(
            'Failed upstream.',
            extra={'job_id': '1'}
        )
        self.deprecation.scheduler.remove_job.assert_called_once_with('1')
        mock_delete_job.assert_called_once_with('1')
        mock_publish_message.assert_called_once_with(job)

    @patch.object(DeprecationService, 'bind_listener_queue')
    @patch.object(DeprecationService, 'persist_job_config')
    def test_deprecation_create_job(
        self, mock_persist_config, mock_bind_listener_queue
    ):
        mock_persist_config.return_value = 'temp-config.json'

        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': '1'}

        job_class = Mock()
        job_class.return_value = job
        job_config = {'id': '1', 'provider': 'ec2'}
        self.deprecation._create_job(job_class, job_config)

        job_class.assert_called_once_with(id='1', provider='ec2')
        job.set_log_callback.assert_called_once_with(
            self.deprecation.log_job_message
        )
        assert job.job_file == 'temp-config.json'
        mock_bind_listener_queue.assert_called_once_with('1')
        self.deprecation.log.info.assert_called_once_with(
            'Job 1 queued, awaiting publisher result.',
            extra={'job_id': '1'}
        )

    def test_deprecation_create_job_exception(self):
        job_class = Mock()
        job_class.side_effect = Exception('Cannot create job.')
        job_config = {'id': '1', 'provider': 'ec2'}

        self.deprecation._create_job(job_class, job_config)
        self.deprecation.log.exception.assert_called_once_with(
            'Invalid job configuration: Cannot create job.'
        )

    @patch.object(DeprecationService, 'remove_file')
    @patch.object(DeprecationService, 'unbind_queue')
    def test_deprecation_delete_job(
        self, mock_unbind_queue, mock_remove_file
    ):
        job = Mock()
        job.id = '1'
        job.job_file = 'job-test.json'
        job.status = 'success'
        job.utctime = 'now'
        job.get_metadata.return_value = {'job_id': '1'}

        self.deprecation.jobs['1'] = job
        self.deprecation._delete_job('1')

        self.deprecation.log.info.assert_called_once_with(
            'Deleting job.',
            extra={'job_id': '1'}
        )

        assert '1' not in self.deprecation.jobs
        mock_unbind_queue.assert_called_once_with(
            'listener', 'deprecation', '1'
        )
        mock_remove_file.assert_called_once_with('job-test.json')

    def test_deprecation_delete_invalid_job(self):
        self.deprecation._delete_job('1')

        self.deprecation.log.warning.assert_called_once_with(
            'Job deletion failed, job is not queued.',
            extra={'job_id': '1'}
        )

    def test_deprecation_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'

        data = self.deprecation._get_status_message(job)
        assert data == self.status_message

    @patch.object(DeprecationService, '_schedule_job')
    @patch.object(DeprecationService, 'decode_credentials')
    def test_deprecation_handle_credentials_response(
        self, mock_decode_credentials, mock_schedule_job
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.deprecation.jobs['1'] = job

        message = Mock()
        message.body = '{"jwt_token": "response"}'

        mock_decode_credentials.return_value = '1', {'fake': 'creds'}
        self.deprecation._handle_credentials_response(message)

        mock_schedule_job.assert_called_once_with('1')
        message.ack.assert_called_once_with()

    @patch.object(DeprecationService, 'decode_credentials')
    def test_deprecation_handle_credentials_response_exceptions(
        self, mock_decode_credentials
    ):
        message = Mock()
        message.body = '{"jwt_token": "response"}'

        # Test job does not exist.
        mock_decode_credentials.return_value = '1', {'fake': 'creds'}
        self.deprecation._handle_credentials_response(message)
        self.deprecation.log.error.assert_called_once_with(
            'Credentials recieved for invalid job with ID: 1.'
        )

        # Invalid json string
        self.deprecation.log.error.reset_mock()
        message.body = 'invalid json string'
        self.deprecation._handle_credentials_response(message)
        self.deprecation.log.error.assert_called_once_with(
            'Invalid credentials response message: '
            'Must be a json encoded message.'
        )

        assert message.ack.call_count == 2

    @patch.object(DeprecationService, 'publish_credentials_request')
    @patch.object(DeprecationService, '_deprecate_image')
    def test_deprecation_handle_listener_message(
        self, mock_deprecate_image, mock_publish_creds_request
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.credentials = None
        self.deprecation.jobs['1'] = job

        self.message.body = self.publisher_result
        self.deprecation._handle_listener_message(self.message)

        assert self.deprecation.jobs['1'].listener_msg == self.message
        mock_publish_creds_request.assert_called_once_with('1')

    @patch.object(DeprecationService, '_schedule_job')
    @patch.object(DeprecationService, '_deprecate_image')
    def test_deprecation_handle_listener_message_creds(
        self, mock_deprecate_image, mock_schedule_job
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.credentials = {'some': 'credentials'}
        self.deprecation.jobs['1'] = job

        self.message.body = self.publisher_result
        self.deprecation._handle_listener_message(self.message)

        assert self.deprecation.jobs['1'].listener_msg == self.message
        mock_schedule_job.assert_called_once_with('1')

    @patch.object(DeprecationService, '_cleanup_job')
    def test_deprecation_listener_message_failed(self, mock_cleanup_job):
        job = Mock()
        job.utctime = 'always'
        self.deprecation.jobs['1'] = job

        self.message.body = self.publisher_result_fail
        self.deprecation._handle_listener_message(self.message)

        mock_cleanup_job.assert_called_once_with(job, 'error')
        self.message.ack.assert_called_once_with()

    def test_deprecation_listener_message_job_none(self):
        self.message.body = self.publisher_result_fail
        self.deprecation._handle_listener_message(self.message)

        self.message.ack.assert_called_once_with()
        self.deprecation.log.error.assert_called_once_with(
            'Invalid deprecation service job with id: 1.'
        )

    def test_deprecation_listener_message_config_invalid(self):
        job = Mock()
        job.utctime = 'always'
        self.deprecation.jobs['1'] = job

        self.message.body = '{"publisher_result": ' \
            '{"id": "1", "status": "success"}}'
        self.deprecation._handle_listener_message(self.message)

        self.message.ack.assert_called_once_with()
        self.deprecation.log.error.assert_called_once_with(
            'cloud_image_name is required in publisher result.'
        )

    @patch.object(DeprecationService, '_add_job')
    def test_deprecation_handle_service_message(self, mock_add_job):
        self.method['routing_key'] = 'job_document'
        self.message.body = '{"deprecation_job": {"id": "1", ' \
            '"provider": "ec2", "utctime": "now", ' \
            '"old_cloud_image_name": "old_image_123", ' \
            '"deprecation_regions": [{"account": "test-aws", ' \
            '"target_regions": ["us-east-1"]}]}}'
        self.deprecation._handle_service_message(self.message)

        mock_add_job.assert_called_once_with({
            'id': '1', 'provider': 'ec2', 'utctime': 'now',
            'old_cloud_image_name': 'old_image_123',
            'deprecation_regions': [{
                'account': 'test-aws',
                'target_regions': ['us-east-1']
            }]
        })
        self.message.ack.assert_called_once_with()

    def test_deprecation_handle_service_message_invalid(self):
        self.message.body = 'Invalid format.'
        self.deprecation._handle_service_message(self.message)

        self.message.ack.assert_called_once_with()
        self.deprecation.log.error.assert_called_once_with(
            'Error adding job: Expecting value:'
            ' line 1 column 1 (char 0).'
        )

    @patch.object(DeprecationService, '_delete_job')
    @patch.object(DeprecationService, '_publish_message')
    def test_deprecation_process_deprecation_result(
        self, mock_publish_message, mock_delete_job
    ):
        event = Mock()
        event.job_id = '1'
        event.exception = None

        msg = Mock()

        job = Mock()
        job.id = '1'
        job.utctime = 'now'
        job.status = 'success'
        job.iteration_count = 1
        job.listener_msg = msg
        job.get_metadata.return_value = {'job_id': '1'}

        self.deprecation.jobs['1'] = job
        self.deprecation._process_deprecation_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.deprecation.log.info.assert_called_once_with(
            'Pass[1]: Deprecation successful.',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(job)
        msg.ack.assert_called_once_with()

    @patch.object(DeprecationService, '_delete_job')
    @patch.object(DeprecationService, '_publish_message')
    def test_deprecation_process_deprecation_result_exception(
        self, mock_publish_message, mock_delete_job
    ):
        event = Mock()
        event.job_id = '1'
        event.exception = 'Image not found!'

        job = Mock()
        job.utctime = 'now'
        job.status = 2
        job.iteration_count = 1
        job.get_metadata.return_value = {'job_id': '1'}

        self.deprecation.jobs['1'] = job
        self.deprecation._process_deprecation_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.deprecation.log.error.assert_called_once_with(
            'Pass[1]: Exception deprecating image: Image not found!',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(job)

    @patch.object(DeprecationService, '_delete_job')
    @patch.object(DeprecationService, '_publish_message')
    def test_publishing_process_deprecation_result_fail(
        self, mock_publish_message, mock_delete_job
    ):
        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.id = '1'
        job.status = 'error'
        job.utctime = 'now'
        job.iteration_count = 1
        job.get_metadata.return_value = {'job_id': '1'}

        self.deprecation.jobs['1'] = job
        self.deprecation._process_deprecation_result(event)

        self.deprecation.log.error.assert_called_once_with(
            'Pass[1]: Error occurred deprecating image.',
            extra={'job_id': '1'}
        )
        mock_delete_job('1')
        mock_publish_message.assert_called_once_with(job)

    def test_deprecation_deprecate_image(self):
        job = Mock()
        self.deprecation.jobs['1'] = job
        self.deprecation.host = 'localhost'

        self.deprecation._deprecate_image('1')
        job.deprecate_image.assert_called_once_with()

    @patch.object(DeprecationService, 'publish_job_result')
    def test_deprecation_publish_message(self, mock_publish):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'

        self.deprecation._publish_message(job)
        mock_publish.assert_called_once_with(
            'pint',
            '1',
            self.status_message
        )

    @patch.object(DeprecationService, 'bind_queue')
    @patch.object(DeprecationService, '_publish')
    def test_deprecation_publish_message_exception(
        self, mock_publish, mock_bind_queue
    ):
        job = Mock()
        job.id = '1'
        job.status = 'error'
        job.get_metadata.return_value = {'job_id': '1'}

        mock_publish.side_effect = AMQPError('Unable to connect to RabbitMQ.')
        self.deprecation._publish_message(job)

        mock_bind_queue.assert_called_once_with('pint', '1', 'listener')
        self.deprecation.log.warning.assert_called_once_with(
            'Message not received: {0}'.format(self.error_message),
            extra={'job_id': '1'}
        )

    @patch.object(DeprecationService, '_deprecate_image')
    def test_deprecation_schedule_duplicate_job(
        self, mock_deprecate_image
    ):
        job = Mock()
        job.utctime = 'always'
        self.deprecation.jobs['1'] = job

        scheduler = Mock()
        scheduler.add_job.side_effect = ConflictingIdError('Conflicting jobs.')
        self.deprecation.scheduler = scheduler

        self.deprecation._schedule_job('1')
        self.deprecation.log.warning.assert_called_once_with(
            'Deprecation job already running. Received multiple '
            'listener messages.',
            extra={'job_id': '1'}
        )
        scheduler.add_job.assert_called_once_with(
            self.deprecation._deprecate_image,
            args=('1',),
            id='1',
            max_instances=1,
            misfire_grace_time=None,
            coalesce=True
        )

    def test_deprecation_validate_invalid_listener_msg(self):
        status = self.deprecation._validate_listener_msg('Test')
        assert status is None
        self.deprecation.log.error.assert_called_once_with(
            'Invalid publisher result file: Test'
        )

    def test_deprecation_validate_listener_msg_no_job(self):
        status = self.deprecation._validate_listener_msg(
            '{"publisher_result": {"id": "1"}}'
        )
        assert status is None
        self.deprecation.log.error.assert_called_once_with(
            'Invalid deprecation service job with id: 1.'
        )

    def test_deprecation_validate_listener_msg_no_id(self):
        self.message.body = '{"publisher_result": {"provider": "ec2"}}'
        result = self.deprecation._validate_listener_msg(self.message.body)

        assert result is None
        self.deprecation.log.error.assert_called_once_with(
            'id is required in publisher result.'
        )

    @patch.object(DeprecationService, 'consume_credentials_queue')
    @patch.object(DeprecationService, 'consume_queue')
    @patch.object(DeprecationService, 'stop')
    def test_deprecation_start(
        self, mock_stop, mock_consume_queue, mock_consume_credentials_queue
    ):
        self.deprecation.channel = self.channel
        self.deprecation.start()

        self.channel.start_consuming.assert_called_once_with()
        mock_consume_queue.assert_has_calls([
            call(self.deprecation._handle_service_message),
            call(
                self.deprecation._handle_listener_message,
                queue_name='listener'
            )
        ])
        mock_consume_credentials_queue.assert_called_once_with(
            self.deprecation._handle_credentials_response
        )
        mock_stop.assert_called_once_with()

    @patch.object(DeprecationService, 'consume_credentials_queue')
    @patch.object(DeprecationService, 'stop')
    def test_deprecation_start_exception(
        self, mock_stop, mock_consume_credentials_queue
    ):
        self.deprecation.channel = self.channel

        self.channel.start_consuming.side_effect = KeyboardInterrupt()
        self.deprecation.start()

        mock_stop.assert_called_once_with()
        mock_stop.reset_mock()
        self.channel.start_consuming.side_effect = Exception(
            'Cannot start consuming.'
        )

        with raises(Exception) as error:
            self.deprecation.start()
        assert 'Cannot start consuming.' == str(error.value)

    @patch.object(DeprecationService, 'close_connection')
    def test_deprecation_stop(self, mock_close_connection):
        self.deprecation.channel = self.channel

        self.deprecation.stop()
        self.channel.stop_consuming.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
