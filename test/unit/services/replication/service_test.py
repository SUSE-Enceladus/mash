from pytest import raises

from unittest.mock import call, MagicMock, Mock, patch

from amqpstorm import AMQPError

from apscheduler.jobstores.base import ConflictingIdError, JobLookupError

from mash.services.base_service import BaseService
from mash.services.replication.service import ReplicationService
from mash.services.replication.ec2_job import EC2ReplicationJob

open_name = "builtins.open"


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

        self.tag = Mock()
        self.method = {'delivery_tag': self.tag}

        self.message = MagicMock(
            channel=self.channel,
            method=self.method,
        )

        self.error_message = '{"replication_result": ' \
            '{"id": "1", "status": "error"}}'
        self.status_message = '{"replication_result": ' \
            '{"cloud_image_name": "image123", "id": "1", ' \
            '"status": "success"}}'

        self.replication = ReplicationService()
        self.replication.jobs = {}
        self.replication.log = Mock()

        scheduler = Mock()
        self.replication.scheduler = scheduler

        self.replication.service_exchange = 'replication'
        self.replication.service_queue = 'service'
        self.replication.listener_queue = 'listener'
        self.replication.job_document_key = 'job_document'

    @patch.object(ReplicationService, 'bind_credentials_queue')
    @patch.object(ReplicationService, 'restart_jobs')
    @patch.object(ReplicationService, 'set_logfile')
    @patch.object(ReplicationService, 'start')
    @patch('mash.services.replication.service.ReplicationConfig')
    def test_replication_post_init(
        self, mock_replication_config, mock_start,
        mock_set_logfile, mock_restart_jobs, mock_bind_creds_queue
    ):
        mock_replication_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/replication_service.log'

        self.replication.post_init()

        self.config.get_log_file.assert_called_once_with('replication')
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/replication_service.log'
        )

        mock_bind_creds_queue.assert_called_once_with()

        mock_restart_jobs.assert_called_once_with(self.replication._add_job)
        mock_start.assert_called_once_with()

    @patch.object(ReplicationService, '_create_job')
    def test_replication_add_job(self, mock_create_job):
        job_config = {
            'id': '1', 'provider': 'ec2', 'utctime': 'now',
        }

        self.replication._add_job(job_config)

        mock_create_job.assert_called_once_with(
            EC2ReplicationJob,
            job_config
        )

    def test_replication_add_job_exists(self):
        job = Mock()
        job.id = '1'
        self.replication.jobs['1'] = job
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'provider': 'ec2', 'utctime': 'now',
        }

        self.replication._add_job(job_config)
        self.replication.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': '1'}
        )

    def test_replication_add_job_invalid_provider(self):
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'provider': 'Provider', 'utctime': 'now',
        }

        self.replication._add_job(job_config)
        self.replication.log.error.assert_called_once_with(
            'Provider Provider is not supported.'
        )

    @patch.object(ReplicationService, '_delete_job')
    @patch.object(ReplicationService, '_publish_message')
    def test_replication_cleanup_job(
        self, mock_publish_message, mock_delete_job
    ):
        self.replication.scheduler.remove_job.side_effect = JobLookupError('1')

        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.image_id = 'image123'
        job.utctime = 'now'
        job.get_metadata.return_value = {'job_id': '1'}

        self.replication.jobs['1'] = job
        self.replication._cleanup_job(job, 1)

        self.replication.log.warning.assert_called_once_with(
            'Failed upstream.',
            extra={'job_id': '1'}
        )
        self.replication.scheduler.remove_job.assert_called_once_with('1')
        mock_delete_job.assert_called_once_with('1')
        mock_publish_message.assert_called_once_with(job)

    @patch.object(ReplicationService, 'bind_listener_queue')
    @patch.object(ReplicationService, 'persist_job_config')
    def test_replication_create_job(
        self, mock_persist_config, mock_bind_listener_queue
    ):
        mock_persist_config.return_value = 'temp-config.json'

        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': '1'}

        job_class = Mock()
        job_class.return_value = job
        job_config = {'id': '1', 'provider': 'EC2'}
        self.replication._create_job(job_class, job_config)

        job_class.assert_called_once_with(id='1', provider='EC2')
        job.set_log_callback.assert_called_once_with(
            self.replication.log_job_message
        )
        assert job.job_file == 'temp-config.json'
        mock_bind_listener_queue.assert_called_once_with('1')
        self.replication.log.info.assert_called_once_with(
            'Job queued, awaiting testing result.',
            extra={'job_id': '1'}
        )

    def test_replication_create_job_exception(self):
        job_class = Mock()
        job_class.side_effect = Exception('Cannot create job.')
        job_config = {'id': '1', 'provider': 'EC2'}

        self.replication._create_job(job_class, job_config)
        self.replication.log.exception.assert_called_once_with(
            'Invalid job configuration: Cannot create job.'
        )

    @patch.object(ReplicationService, 'remove_file')
    @patch.object(ReplicationService, 'unbind_queue')
    def test_replication_delete_job(
        self, mock_unbind_queue, mock_remove_file
    ):
        job = Mock()
        job.id = '1'
        job.job_file = 'job-test.json'
        job.status = 'success'
        job.image_id = 'image123'
        job.utctime = 'now'
        job.get_metadata.return_value = {'job_id': '1'}
        self.replication.jobs['1'] = job

        self.replication._delete_job('1')

        self.replication.log.info.assert_called_once_with(
            'Deleting job.',
            extra={'job_id': '1'}
        )

        assert '1' not in self.replication.jobs
        mock_unbind_queue.assert_called_once_with(
            'listener', 'replication', '1'
        )
        mock_remove_file.assert_called_once_with('job-test.json')

    def test_replication_delete_invalid_job(self):
        self.replication._delete_job('1')

        self.replication.log.warning.assert_called_once_with(
            'Job deletion failed, job is not queued.',
            extra={'job_id': '1'}
        )

    def test_replication_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'

        data = self.replication._get_status_message(job)
        assert data == self.status_message

    @patch.object(ReplicationService, '_schedule_job')
    @patch.object(ReplicationService, 'decode_credentials')
    def test_replication_handle_credentials_response(
        self, mock_decode_credentials, mock_schedule_job
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.replication.jobs['1'] = job

        message = Mock()
        message.body = '{"jwt_token": "response"}'

        mock_decode_credentials.return_value = '1', {'fake': 'creds'}
        self.replication._handle_credentials_response(message)

        mock_schedule_job.assert_called_once_with('1')
        message.ack.assert_called_once_with()

    @patch.object(ReplicationService, 'decode_credentials')
    def test_replication_handle_credentials_response_exceptions(
        self, mock_decode_credentials
    ):
        message = Mock()
        message.body = '{"jwt_token": "response"}'

        # Test job does not exist.
        mock_decode_credentials.return_value = '1', {'fake': 'creds'}
        self.replication._handle_credentials_response(message)
        self.replication.log.error.assert_called_once_with(
            'Credentials recieved for invalid job with ID: 1.'
        )

        # Invalid json string
        self.replication.log.error.reset_mock()
        message.body = 'invalid json string'
        self.replication._handle_credentials_response(message)
        self.replication.log.error.assert_called_once_with(
            'Invalid credentials response message: '
            'Must be a json encoded message.'
        )

        assert message.ack.call_count == 2

    @patch.object(ReplicationService, '_replicate_image')
    def test_replication_handle_listener_message(self, mock_replicate_image):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.credentials = {'test-aws': {'test': 'credentials'}}
        self.replication.jobs['1'] = job

        scheduler = Mock()
        self.replication.scheduler = scheduler

        self.message.body = \
            '{"testing_result": {"id": "1", ' \
            '"cloud_image_name": "image_name", ' \
            '"source_regions": {"us-east-1": "ami-bc5b48d0"}, ' \
            '"status": "success"}}'

        self.replication._handle_listener_message(self.message)

        assert self.replication.jobs['1'].cloud_image_name == 'image_name'
        assert self.replication.jobs['1'].listener_msg == self.message
        scheduler.add_job.assert_called_once_with(
            mock_replicate_image,
            args=('1',),
            id='1',
            max_instances=1,
            misfire_grace_time=None,
            coalesce=True
        )

    @patch.object(ReplicationService, 'publish_credentials_request')
    def test_replication_handle_new_listener_message(
        self, mock_pub_creds_req
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.credentials = None
        self.replication.jobs['1'] = job

        scheduler = Mock()
        self.replication.scheduler = scheduler

        self.message.body = \
            '{"testing_result": {"id": "1", ' \
            '"cloud_image_name": "image name", ' \
            '"source_regions": {"us-east-1": "ami-bc5b48d0"}, ' \
            '"status": "success"}}'

        self.replication._handle_listener_message(self.message)
        mock_pub_creds_req.assert_called_once_with('1')

    @patch.object(ReplicationService, '_cleanup_job')
    def test_replication_listener_message_failed(self, mock_cleanup_job):
        job = Mock()
        job.utctime = 'always'
        self.replication.jobs['1'] = job

        self.message.body = \
            '{"testing_result": {"id": "1", ' \
            '"image_id": "image123", "image_name": "image name", ' \
            '"source_region": "us-west-1", "status": "error"}}'
        self.replication._handle_listener_message(self.message)

        mock_cleanup_job.assert_called_once_with(job, 'error')
        self.message.ack.assert_called_once_with()

    def test_replication_listener_message_job_none(self):
        self.message.body = \
            '{"testing_result": {"id": "1", ' \
            '"image_id": "image123", "image_name": "image name", ' \
            '"source_region": "us-west-1", "status": "error"}}'
        self.replication._handle_listener_message(self.message)

        self.message.ack.assert_called_once_with()
        self.replication.log.error.assert_called_once_with(
            'Invalid replication service job with id: 1.'
        )

    def test_replication_listener_message_config_invalid(self):
        job = Mock()
        job.utctime = 'always'
        self.replication.jobs['1'] = job

        self.message.body = '{"testing_result": ' \
            '{"id": "1", "status": "success"}}'
        self.replication._handle_listener_message(self.message)

        self.message.ack.assert_called_once_with()
        self.replication.log.error.assert_called_once_with(
            'cloud_image_name is required in testing result.'
        )

    @patch.object(ReplicationService, '_add_job')
    def test_replication_handle_service_message(self, mock_add_job):
        self.method['routing_key'] = 'job_document'

        self.message.body = '{"replication_job": {"id": "1", ' \
            '"image_description": "My image", "provider": "EC2", ' \
            '"utctime": "now", "replication_source_regions": {"us-east-1": {' \
            '"account": "test-aws", "target_regions": ' \
            '["us-east-2", "us-west-2", "eu-west-3"]}}}}'
        self.replication._handle_service_message(self.message)

        mock_add_job.assert_called_once_with(
            {
                'id': '1', 'image_description': 'My image',
                'provider': 'EC2', 'utctime': 'now',
                'replication_source_regions': {
                    'us-east-1': {
                        'account': 'test-aws', 'target_regions': [
                            "us-east-2", "us-west-2", "eu-west-3"
                        ]
                    }
                }
            }
        )
        self.message.ack.assert_called_once_with()

    def test_replication_handle_service_message_invalid(self):
        self.message.body = 'Invalid format.'
        self.replication._handle_service_message(self.message)

        self.message.ack.assert_called_once_with()
        self.replication.log.error.assert_called_once_with(
            'Error adding job: Expecting value:'
            ' line 1 column 1 (char 0).'
        )

    @patch.object(ReplicationService, '_delete_job')
    @patch.object(ReplicationService, '_publish_message')
    def test_replication_process_replication_result(
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

        self.replication.jobs['1'] = job
        self.replication._process_replication_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.replication.log.info.assert_called_once_with(
            'Pass[1]: Replication successful.',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(job)
        msg.ack.assert_called_once_with()

    @patch.object(ReplicationService, '_delete_job')
    @patch.object(ReplicationService, '_publish_message')
    def test_replication_process_replication_result_exception(
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

        self.replication.jobs['1'] = job
        self.replication._process_replication_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.replication.log.error.assert_called_once_with(
            'Pass[1]: Exception replicating image: Image not found!',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(job)

    @patch.object(ReplicationService, '_delete_job')
    @patch.object(ReplicationService, '_publish_message')
    def test_replication_process_replication_result_fail(
        self, mock_publish_message, mock_delete_job
    ):
        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.id = '1'
        job.image_id = 'image123'
        job.status = 'error'
        job.utctime = 'now'
        job.iteration_count = 1
        job.get_metadata.return_value = {'job_id': '1'}

        self.replication.jobs['1'] = job
        self.replication._process_replication_result(event)

        self.replication.log.error.assert_called_once_with(
            'Pass[1]: Error occurred replicating image.',
            extra={'job_id': '1'}
        )
        mock_delete_job('1')
        mock_publish_message.assert_called_once_with(job)

    def test_replication_replicate_image(self):
        job = Mock()
        self.replication.jobs['1'] = job

        self.replication._replicate_image('1')
        job.replicate_image.assert_called_once_with()

    @patch.object(ReplicationService, 'publish_job_result')
    def test_replication_publish_message(self, mock_publish):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'

        self.replication._publish_message(job)
        mock_publish.assert_called_once_with(
            'publisher', '1', self.status_message
        )

    @patch.object(ReplicationService, 'bind_queue')
    @patch.object(ReplicationService, '_publish')
    def test_replication_publish_message_exception(
        self, mock_publish, mock_bind_queue
    ):
        job = Mock()
        job.image_id = 'image123'
        job.id = '1'
        job.status = 'error'
        job.get_metadata.return_value = {'job_id': '1'}

        mock_publish.side_effect = AMQPError(
            'Unable to connect to RabbitMQ.'
        )
        self.replication._publish_message(job)

        mock_bind_queue.assert_called_once_with('publisher', '1', 'listener')
        self.replication.log.warning.assert_called_once_with(
            'Message not received: {0}'.format(self.error_message),
            extra={'job_id': '1'}
        )

    @patch.object(ReplicationService, '_replicate_image')
    def test_replication_schedule_duplicate_job(
        self, mock_replicate_image
    ):
        job = Mock()
        job.utctime = 'always'
        job.id = '1'
        self.replication.jobs['1'] = job

        scheduler = Mock()
        scheduler.add_job.side_effect = ConflictingIdError('Conflicting jobs.')
        self.replication.scheduler = scheduler

        self.replication._schedule_job('1')
        self.replication.log.warning.assert_called_once_with(
            'Replication job already running. Received multiple '
            'listener messages.',
            extra={'job_id': '1'}
        )
        scheduler.add_job.assert_called_once_with(
            self.replication._replicate_image,
            args=('1',),
            id='1',
            max_instances=1,
            misfire_grace_time=None,
            coalesce=True
        )

    def test_replication_validate_invalid_listener_msg(self):
        status = self.replication._validate_listener_msg('Test')
        assert status is None
        self.replication.log.error.assert_called_once_with(
            'Invalid testing result file: Test'
        )

    def test_replication_validate_listener_msg_no_job(self):
        status = self.replication._validate_listener_msg(
            '{"testing_result": {"id": "1"}}'
        )
        assert status is None
        self.replication.log.error.assert_called_once_with(
            'Invalid replication service job with id: 1.'
        )

    def test_replication_validate_listener_msg_no_id(self):
        self.message.body = '{"testing_result": {"provider": "EC2"}}'
        result = self.replication._validate_listener_msg(self.message.body)

        assert result is None
        self.replication.log.error.assert_called_once_with(
            'id is required in testing result.'
        )

    @patch.object(ReplicationService, 'consume_credentials_queue')
    @patch.object(ReplicationService, 'consume_queue')
    @patch.object(ReplicationService, 'stop')
    def test_replication_start(
        self, mock_stop, mock_consume_queue, mock_consume_credentials_queue
    ):
        self.replication.channel = self.channel
        self.replication.start()

        self.channel.start_consuming.assert_called_once_with()
        mock_consume_queue.assert_has_calls([
            call(self.replication._handle_service_message),
            call(
                self.replication._handle_listener_message,
                queue_name='listener'
            )
        ])
        mock_consume_credentials_queue.assert_called_once_with(
            self.replication._handle_credentials_response
        )
        mock_stop.assert_called_once_with()

    @patch.object(ReplicationService, 'consume_credentials_queue')
    @patch.object(ReplicationService, 'stop')
    def test_replication_start_exception(
        self, mock_stop, mock_consume_credentials_queue
    ):
        self.replication.channel = self.channel

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
        self.replication.channel = self.channel

        self.replication.stop()
        self.channel.stop_consuming.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
