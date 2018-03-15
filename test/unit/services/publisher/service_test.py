from pytest import raises
from unittest.mock import call, MagicMock, Mock, patch

from amqpstorm import AMQPError

from apscheduler.jobstores.base import ConflictingIdError, JobLookupError

from mash.services.base_service import BaseService
from mash.services.publisher.service import PublisherService
from mash.services.publisher.ec2_job import EC2PublisherJob

open_name = "builtins.open"


class TestPublisherService(object):

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

        self.error_message = '{"publisher_result": ' \
            '{"id": "1", "status": "error"}}'
        self.status_message = '{"publisher_result": ' \
            '{"cloud_image_name": "image123", "id": "1", ' \
            '"source_regions": {"us-east-1": "ami-12345"}, ' \
            '"status": "success"}}'

        self.publisher = PublisherService()
        self.publisher.jobs = {}
        self.publisher.log = Mock()

        scheduler = Mock()
        self.publisher.scheduler = scheduler

        self.publisher.service_exchange = 'publisher'
        self.publisher.service_queue = 'service'
        self.publisher.listener_queue = 'listener'
        self.publisher.job_document_key = 'job_document'

    @patch.object(PublisherService, 'bind_credentials_queue')
    @patch.object(PublisherService, 'restart_jobs')
    @patch.object(PublisherService, 'set_logfile')
    @patch.object(PublisherService, 'start')
    @patch('mash.services.publisher.service.PublisherConfig')
    def test_publisher_post_init(
        self, mock_publisher_config, mock_start,
        mock_set_logfile, mock_restart_jobs, mock_bind_creds
    ):
        mock_publisher_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/publisher_service.log'

        self.publisher.post_init()

        self.config.get_log_file.assert_called_once_with('publisher')
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/publisher_service.log'
        )

        mock_bind_creds.assert_called_once_with()
        mock_restart_jobs.assert_called_once_with(self.publisher._add_job)
        mock_start.assert_called_once_with()

    @patch.object(PublisherService, '_create_job')
    def test_publisher_add_job(self, mock_create_job):
        job_config = {
            'id': '1', 'provider': 'ec2', 'utctime': 'now',
        }

        self.publisher._add_job(job_config)

        mock_create_job.assert_called_once_with(
            EC2PublisherJob,
            job_config
        )

    def test_publisher_add_job_exists(self):
        job = Mock()
        job.id = '1'
        self.publisher.jobs['1'] = job
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'provider': 'ec2', 'utctime': 'now',
        }

        self.publisher._add_job(job_config)
        self.publisher.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': '1'}
        )

    def test_publisher_add_job_invalid_provider(self):
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'provider': 'Provider', 'utctime': 'now',
        }

        self.publisher._add_job(job_config)
        self.publisher.log.error.assert_called_once_with(
            'Provider Provider is not supported.'
        )

    @patch.object(PublisherService, '_delete_job')
    @patch.object(PublisherService, '_publish_message')
    def test_publisher_cleanup_job(
        self, mock_publish_message, mock_delete_job
    ):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.utctime = 'now'
        job.get_metadata.return_value = {'job_id': '1'}

        self.publisher.jobs['1'] = job
        self.publisher._cleanup_job(job, 1)

        self.publisher.log.warning.assert_called_once_with(
            'Failed upstream.',
            extra={'job_id': '1'}
        )
        mock_delete_job.assert_called_once_with('1')
        mock_publish_message.assert_called_once_with(job)

    @patch.object(PublisherService, 'bind_listener_queue')
    @patch.object(PublisherService, 'persist_job_config')
    def test_publisher_create_job(
        self, mock_persist_config, mock_bind_listener_queue
    ):
        mock_persist_config.return_value = 'temp-config.json'

        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': '1'}

        job_class = Mock()
        job_class.return_value = job
        job_config = {'id': '1', 'provider': 'EC2'}
        self.publisher._create_job(job_class, job_config)

        job_class.assert_called_once_with(id='1', provider='EC2')
        job.set_log_callback.assert_called_once_with(
            self.publisher.log_job_message
        )
        assert job.job_file == 'temp-config.json'
        mock_bind_listener_queue.assert_called_once_with('1')
        self.publisher.log.info.assert_called_once_with(
            'Job queued, awaiting replication result.',
            extra={'job_id': '1'}
        )

    def test_publisher_create_job_exception(self):
        job_class = Mock()
        job_class.side_effect = Exception('Cannot create job.')
        job_config = {'id': '1', 'provider': 'EC2'}

        self.publisher._create_job(job_class, job_config)
        self.publisher.log.exception.assert_called_once_with(
            'Invalid job configuration: Cannot create job.'
        )

    @patch.object(PublisherService, 'remove_file')
    @patch.object(PublisherService, 'unbind_queue')
    def test_publisher_delete_job(
        self, mock_unbind_queue, mock_remove_file
    ):
        self.publisher.scheduler.remove_job.side_effect = JobLookupError(
            'Job finished.'
        )

        job = Mock()
        job.id = '1'
        job.job_file = 'job-test.json'
        job.status = 'success'
        job.utctime = 'now'
        job.get_metadata.return_value = {'job_id': '1'}
        self.publisher.jobs['1'] = job

        self.publisher._delete_job('1')

        self.publisher.scheduler.remove_job.assert_called_once_with('1')
        self.publisher.log.info.assert_called_once_with(
            'Deleting job.',
            extra={'job_id': '1'}
        )

        assert '1' not in self.publisher.jobs
        mock_unbind_queue.assert_called_once_with(
            'listener', 'publisher', '1'
        )
        mock_remove_file.assert_called_once_with('job-test.json')

    def test_publisher_delete_invalid_job(self):
        self.publisher._delete_job('1')

        self.publisher.log.warning.assert_called_once_with(
            'Job deletion failed, job is not queued.',
            extra={'job_id': '1'}
        )

    def test_publisher_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'
        job.source_regions = {'us-east-1': 'ami-12345'}

        data = self.publisher._get_status_message(job)
        assert data == self.status_message

    @patch.object(PublisherService, '_schedule_job')
    @patch.object(PublisherService, 'decode_credentials')
    def test_publisher_handle_credentials_response(
        self, mock_decode_credentials, mock_schedule_job
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.publisher.jobs['1'] = job

        message = Mock()
        message.body = '{"jwt_token": "response"}'

        mock_decode_credentials.return_value = '1', {'fake': 'creds'}
        self.publisher._handle_credentials_response(message)

        mock_schedule_job.assert_called_once_with('1')
        message.ack.assert_called_once_with()

    @patch.object(PublisherService, 'decode_credentials')
    def test_publisher_handle_credentials_response_exceptions(
        self, mock_decode_credentials
    ):
        message = Mock()
        message.body = '{"jwt_token": "response"}'

        # Test job does not exist.
        mock_decode_credentials.return_value = '1', {'fake': 'creds'}
        self.publisher._handle_credentials_response(message)
        self.publisher.log.error.assert_called_once_with(
            'Credentials recieved for invalid job with ID: 1.'
        )

        # Invalid json string
        self.publisher.log.error.reset_mock()
        message.body = 'invalid json string'
        self.publisher._handle_credentials_response(message)
        self.publisher.log.error.assert_called_once_with(
            'Invalid credentials response message: '
            'Must be a json encoded message.'
        )

        assert message.ack.call_count == 2

    @patch.object(PublisherService, 'publish_credentials_request')
    @patch.object(PublisherService, '_publish_image')
    def test_publisher_handle_listener_message(
        self, mock_publish_image, mock_publish_creds_request
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.credentials = None
        self.publisher.jobs['1'] = job

        self.message.body = \
            '{"replication_result": {"id": "1", ' \
            '"cloud_image_name": "image name", ' \
            '"source_regions": {"us-west-1": "ami-123456"}, ' \
            '"status": "success"}}'

        self.publisher._handle_listener_message(self.message)

        assert self.publisher.jobs['1'].listener_msg == self.message
        mock_publish_creds_request.assert_called_once_with('1')

    @patch.object(PublisherService, '_schedule_job')
    @patch.object(PublisherService, '_publish_image')
    def test_publisher_handle_listener_message_creds(
        self, mock_publish_image, mock_schedule_job
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.credentials = {'some': 'credentials'}
        self.publisher.jobs['1'] = job

        self.message.body = \
            '{"replication_result": {"id": "1", ' \
            '"cloud_image_name": "image name", ' \
            '"source_regions": {"us-west-1": "ami-123456"}, ' \
            '"status": "success"}}'

        self.publisher._handle_listener_message(self.message)

        assert self.publisher.jobs['1'].listener_msg == self.message
        mock_schedule_job.assert_called_once_with('1')

    @patch.object(PublisherService, '_cleanup_job')
    def test_publisher_listener_message_failed(self, mock_cleanup_job):
        job = Mock()
        job.utctime = 'always'
        self.publisher.jobs['1'] = job

        self.message.body = \
            '{"replication_result": {"id": "1", ' \
            '"cloud_image_name": "image name", ' \
            '"source_regions": {"us-west-1": "ami-123"}, "status": "error"}}'
        self.publisher._handle_listener_message(self.message)

        mock_cleanup_job.assert_called_once_with(job, 'error')
        self.message.ack.assert_called_once_with()

    def test_publisher_listener_message_job_none(self):
        self.message.body = \
            '{"replication_result": {"id": "1", ' \
            '"cloud_image_name": "image name", ' \
            '"source_regions": {"us-west-1": "ami-123"}, "status": "error"}}'
        self.publisher._handle_listener_message(self.message)

        self.message.ack.assert_called_once_with()
        self.publisher.log.error.assert_called_once_with(
            'Invalid publisher service job with id: 1.'
        )

    def test_publisher_listener_message_config_invalid(self):
        job = Mock()
        job.utctime = 'always'
        self.publisher.jobs['1'] = job

        self.message.body = '{"replication_result": ' \
            '{"id": "1", "status": "success"}}'
        self.publisher._handle_listener_message(self.message)

        self.message.ack.assert_called_once_with()
        self.publisher.log.error.assert_called_once_with(
            'cloud_image_name is required in replication result.'
        )

    @patch.object(PublisherService, '_add_job')
    def test_publisher_handle_service_message(self, mock_add_job):
        self.method['routing_key'] = 'job_document'
        self.message.body = '{"publisher_job": {"allow_copy": false, ' \
            '"id": "1", ' \
            '"provider": "EC2", "utctime": "now", "share_with": "all", ' \
            '"publish_regions": {"test-aws": ["us-east-1"]}}}'
        self.publisher._handle_service_message(self.message)

        mock_add_job.assert_called_once_with(
            {'allow_copy': False, 'id': '1', 'provider': 'EC2',
             'utctime': 'now', 'share_with': 'all',
             'publish_regions': {'test-aws': ['us-east-1']}}
        )
        self.message.ack.assert_called_once_with()

    @patch.object(PublisherService, 'notify_invalid_config')
    def test_publisher_handle_service_message_invalid(self, mock_notify):
        self.message.body = 'Invalid format.'
        self.publisher._handle_service_message(self.message)

        self.message.ack.assert_called_once_with()
        self.publisher.log.error.assert_called_once_with(
            'Invalid job config file: Expecting value:'
            ' line 1 column 1 (char 0).'
        )
        mock_notify.assert_called_once_with(self.message.body)

    @patch.object(PublisherService, 'notify_invalid_config')
    def test_publisher_handle_service_message_bad_key(self, mock_notify):
        self.message.body = '{"publisher_job_update": {"id": "1"}}'

        self.publisher._handle_service_message(self.message)

        self.message.ack.assert_called_once_with()
        self.publisher.log.error.assert_called_once_with(
            'Invalid publisher job: Job document must contain the '
            'publisher_job key.'
        )
        mock_notify.assert_called_once_with(self.message.body)

    @patch.object(PublisherService, '_validate_job_config')
    @patch.object(PublisherService, 'notify_invalid_config')
    def test_publisher_handle_service_message_fail_validation(
        self, mock_notify, mock_validate_job
    ):
        mock_validate_job.return_value = False
        self.message.body = '{"publisher_job": {"id": "1"}}'
        self.publisher._handle_service_message(self.message)

        self.message.ack.assert_called_once_with()
        mock_notify.assert_called_once_with(self.message.body)

    @patch.object(PublisherService, '_delete_job')
    @patch.object(PublisherService, '_publish_message')
    def test_publisher_process_publishing_result(
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

        self.publisher.jobs['1'] = job
        self.publisher._process_publishing_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.publisher.log.info.assert_called_once_with(
            'Pass[1]: Publishing successful.',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(job)
        msg.ack.assert_called_once_with()

    @patch.object(PublisherService, '_delete_job')
    @patch.object(PublisherService, '_publish_message')
    def test_publisher_process_publishing_result_exception(
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

        self.publisher.jobs['1'] = job
        self.publisher._process_publishing_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.publisher.log.error.assert_called_once_with(
            'Pass[1]: Exception publishing image: Image not found!',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(job)

    @patch.object(PublisherService, '_delete_job')
    @patch.object(PublisherService, '_publish_message')
    def test_publishing_process_publishing_result_fail(
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

        self.publisher.jobs['1'] = job
        self.publisher._process_publishing_result(event)

        self.publisher.log.error.assert_called_once_with(
            'Pass[1]: Error occurred publishing image.',
            extra={'job_id': '1'}
        )
        mock_delete_job('1')
        mock_publish_message.assert_called_once_with(job)

    def test_publisher_publish_image(self):
        job = Mock()
        self.publisher.jobs['1'] = job
        self.publisher.host = 'localhost'

        self.publisher._publish_image('1')
        job.publish_image.assert_called_once_with()

    @patch.object(PublisherService, 'publish_job_result')
    def test_publisher_publish_message(self, mock_publish):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'
        job.source_regions = {'us-east-1': 'ami-12345'}

        self.publisher._publish_message(job)
        mock_publish.assert_called_once_with(
            'deprecation',
            '1',
            self.status_message
        )

    @patch.object(PublisherService, 'bind_queue')
    @patch.object(PublisherService, '_publish')
    def test_publisher_publish_message_exception(
        self, mock_publish, mock_bind_queue
    ):
        job = Mock()
        job.id = '1'
        job.status = 'error'
        job.get_metadata.return_value = {'job_id': '1'}

        mock_publish.side_effect = AMQPError('Unable to connect to RabbitMQ.')
        self.publisher._publish_message(job)

        mock_bind_queue.assert_called_once_with('deprecation', '1', 'listener')
        self.publisher.log.warning.assert_called_once_with(
            'Message not received: {0}'.format(self.error_message),
            extra={'job_id': '1'}
        )

    @patch.object(PublisherService, '_publish_image')
    def test_publisher_schedule_duplicate_job(
        self, mock_publish_image
    ):
        job = Mock()
        job.utctime = 'always'
        self.publisher.jobs['1'] = job

        scheduler = Mock()
        scheduler.add_job.side_effect = ConflictingIdError('Conflicting jobs.')
        self.publisher.scheduler = scheduler

        self.publisher._schedule_job('1')
        self.publisher.log.warning.assert_called_once_with(
            'Publisher job already running. Received multiple '
            'listener messages.',
            extra={'job_id': '1'}
        )
        scheduler.add_job.assert_called_once_with(
            self.publisher._publish_image,
            args=('1',),
            id='1',
            max_instances=1,
            misfire_grace_time=None,
            coalesce=True
        )

    def test_publisher_validate_invalid_job_config(self):
        status = self.publisher._validate_job_config('{"id": "1"}')
        assert status is False
        self.publisher.log.error.assert_called_once_with(
            'allow_copy is required in publisher job config.'
        )

    def test_publisher_validate_invalid_listener_msg(self):
        status = self.publisher._validate_listener_msg('Test')
        assert status is None
        self.publisher.log.error.assert_called_once_with(
            'Invalid replication result file: Test'
        )

    def test_publisher_validate_listener_msg_no_job(self):
        status = self.publisher._validate_listener_msg(
            '{"replication_result": {"id": "1"}}'
        )
        assert status is None
        self.publisher.log.error.assert_called_once_with(
            'Invalid publisher service job with id: 1.'
        )

    def test_publisher_validate_listener_msg_no_id(self):
        self.message.body = '{"replication_result": {"provider": "EC2"}}'
        result = self.publisher._validate_listener_msg(self.message.body)

        assert result is None
        self.publisher.log.error.assert_called_once_with(
            'id is required in replication result.'
        )

    @patch.object(PublisherService, 'consume_credentials_queue')
    @patch.object(PublisherService, 'consume_queue')
    @patch.object(PublisherService, 'stop')
    def test_publisher_start(
        self, mock_stop, mock_consume_queue, mock_consume_credentials_queue
    ):
        self.publisher.channel = self.channel
        self.publisher.start()

        self.channel.start_consuming.assert_called_once_with()
        mock_consume_queue.assert_has_calls([
            call(self.publisher._handle_service_message),
            call(
                self.publisher._handle_listener_message, queue_name='listener'
            )
        ])
        mock_consume_credentials_queue.assert_called_once_with(
            self.publisher._handle_credentials_response
        )
        mock_stop.assert_called_once_with()

    @patch.object(PublisherService, 'consume_credentials_queue')
    @patch.object(PublisherService, 'stop')
    def test_publisher_start_exception(
        self, mock_stop, mock_consume_credentials_queue
    ):
        self.publisher.channel = self.channel

        self.channel.start_consuming.side_effect = KeyboardInterrupt()
        self.publisher.start()

        mock_stop.assert_called_once_with()
        mock_stop.reset_mock()
        self.channel.start_consuming.side_effect = Exception(
            'Cannot start consuming.'
        )

        with raises(Exception) as error:
            self.publisher.start()
        assert 'Cannot start consuming.' == str(error.value)

    @patch.object(PublisherService, 'close_connection')
    def test_publisher_stop(self, mock_close_connection):
        self.publisher.channel = self.channel

        self.publisher.stop()
        self.channel.stop_consuming.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
