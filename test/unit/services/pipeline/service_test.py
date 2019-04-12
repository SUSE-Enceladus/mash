import pytest

from unittest.mock import call, MagicMock, Mock, patch

from amqpstorm import AMQPError

from apscheduler.jobstores.base import ConflictingIdError, JobLookupError

from mash.services.mash_service import MashService
from mash.services.pipeline_service import PipelineService
from mash.utils.json_format import JsonFormat

NOT_IMPL_METHODS = [
    'add_job'
]


class TestPipelineService(object):
    @patch.object(MashService, '__init__')
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

        self.error_message = JsonFormat.json_message({
            "replication_result": {
                "id": "1",
                "status": "failed"
            }
        })
        self.status_message = JsonFormat.json_message({
            "replication_result": {
                "cloud_image_name": "image123",
                "id": "1",
                "status": "success"
            }
        })

        self.service = PipelineService()
        self.service.jobs = {}
        self.service.log = Mock()

        scheduler = Mock()
        self.service.scheduler = scheduler

        self.service.service_exchange = 'replication'
        self.service.service_queue = 'service'
        self.service.listener_queue = 'listener'
        self.service.job_document_key = 'job_document'
        self.service.listener_msg_key = 'listener_msg'
        self.service.next_service = 'publisher'
        self.service.prev_service = 'testing'
        self.service.listener_msg_args = ['cloud_image_name']
        self.service.status_msg_args = ['cloud_image_name']

    @patch.object(PipelineService, 'bind_credentials_queue')
    @patch.object(PipelineService, 'restart_jobs')
    @patch.object(PipelineService, 'set_logfile')
    @patch.object(PipelineService, 'start')
    def test_service_post_init(
        self, mock_start,
        mock_set_logfile, mock_restart_jobs, mock_bind_creds
    ):
        self.service.config = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/service_service.log'

        self.service.post_init()

        self.config.get_log_file.assert_called_once_with('replication')
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/service_service.log'
        )

        mock_bind_creds.assert_called_once_with()
        mock_restart_jobs.assert_called_once_with(self.service.add_job)
        mock_start.assert_called_once_with()

    @patch.object(PipelineService, '_delete_job')
    @patch.object(PipelineService, '_publish_message')
    def test_service_cleanup_job(
        self, mock_publish_message, mock_delete_job
    ):
        self.service.scheduler.remove_job.side_effect = JobLookupError('1')

        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.utctime = 'now'
        job.get_job_id.return_value = {'job_id': '1'}

        self.service.jobs['1'] = job
        self.service._cleanup_job(job, 1)

        self.service.log.warning.assert_called_once_with(
            'Failed upstream.',
            extra={'job_id': '1'}
        )
        self.service.scheduler.remove_job.assert_called_once_with('1')
        mock_delete_job.assert_called_once_with('1')
        mock_publish_message.assert_called_once_with(job)

    @patch.object(PipelineService, 'persist_job_config')
    def test_service_create_job(
        self, mock_persist_config
    ):
        mock_persist_config.return_value = 'temp-config.json'

        job = Mock()
        job.id = '1'
        job.get_job_id.return_value = {'job_id': '1'}

        job_class = Mock()
        job_class.return_value = job
        job_config = {'id': '1', 'cloud': 'ec2'}
        self.service._create_job(job_class, job_config)

        job_class.assert_called_once_with(id='1', cloud='ec2')
        assert job.log_callback == self.service.log_job_message
        assert job.job_file == 'temp-config.json'
        self.service.log.info.assert_called_once_with(
            'Job queued, awaiting listener message.',
            extra={'job_id': '1'}
        )

    def test_service_create_job_exception(self):
        job_class = Mock()
        job_class.side_effect = Exception('Cannot create job.')
        job_config = {'id': '1', 'cloud': 'ec2'}

        self.service._create_job(job_class, job_config)
        self.service.log.exception.assert_called_once_with(
            'Invalid job configuration: Cannot create job.'
        )

    @patch.object(PipelineService, 'publish_credentials_delete')
    @patch.object(PipelineService, 'remove_file')
    @patch.object(PipelineService, 'unbind_queue')
    def test_service_delete_job(
        self, mock_unbind_queue, mock_remove_file, mock_publish_creds_delete
    ):
        job = Mock()
        job.id = '1'
        job.job_file = 'job-test.json'
        job.last_service = 'replication'
        job.status = 'success'
        job.utctime = 'now'
        job.get_job_id.return_value = {'job_id': '1'}

        self.service.jobs['1'] = job
        self.service._delete_job('1')

        mock_publish_creds_delete.assert_called_once_with('1')
        self.service.log.info.assert_called_once_with(
            'Deleting job.',
            extra={'job_id': '1'}
        )

        assert '1' not in self.service.jobs
        mock_remove_file.assert_called_once_with('job-test.json')

    def test_service_delete_invalid_job(self):
        self.service._delete_job('1')

        self.service.log.warning.assert_called_once_with(
            'Job deletion failed, job is not queued.',
            extra={'job_id': '1'}
        )

    @patch.object(PipelineService, '_schedule_job')
    @patch.object(PipelineService, 'decode_credentials')
    def test_service_handle_credentials_response(
        self, mock_decode_credentials, mock_schedule_job
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.service.jobs['1'] = job

        message = Mock()
        message.body = '{"jwt_token": "response"}'

        mock_decode_credentials.return_value = '1', {'fake': 'creds'}
        self.service._handle_credentials_response(message)

        mock_schedule_job.assert_called_once_with('1')
        message.ack.assert_called_once_with()

    @patch.object(PipelineService, 'decode_credentials')
    def test_service_handle_credentials_response_exceptions(
        self, mock_decode_credentials
    ):
        message = Mock()
        message.body = '{"jwt_token": "response"}'

        # Test job does not exist.
        mock_decode_credentials.return_value = '1', {'fake': 'creds'}
        self.service._handle_credentials_response(message)
        self.service.log.error.assert_called_once_with(
            'Credentials received for invalid job with ID: 1.'
        )

        # Invalid json string
        self.service.log.error.reset_mock()
        message.body = 'invalid json string'
        self.service._handle_credentials_response(message)
        self.service.log.error.assert_called_once_with(
            'Invalid credentials response message: '
            'Must be a json encoded message.'
        )

        assert message.ack.call_count == 2

    @patch.object(PipelineService, '_validate_listener_msg')
    @patch.object(PipelineService, 'publish_credentials_request')
    def test_service_handle_listener_message(
        self, mock_publish_creds_request, mock_validate_listener_msg
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.credentials = None
        self.service.jobs['1'] = job

        mock_validate_listener_msg.return_value = job

        self.message.body = self.status_message
        self.service._handle_listener_message(self.message)

        assert self.service.jobs['1'].listener_msg == self.message
        mock_publish_creds_request.assert_called_once_with('1')

    @patch.object(PipelineService, '_validate_listener_msg')
    @patch.object(PipelineService, '_schedule_job')
    def test_service_handle_listener_message_creds(
        self, mock_schedule_job, mock_validate_listener_msg
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.credentials = {'some': 'credentials'}
        self.service.jobs['1'] = job

        mock_validate_listener_msg.return_value = job

        self.message.body = self.status_message
        self.service._handle_listener_message(self.message)

        assert self.service.jobs['1'].listener_msg == self.message
        mock_schedule_job.assert_called_once_with('1')

    @patch.object(PipelineService, '_validate_listener_msg')
    def test_service_handle_listener_msg_invalid(
        self, mock_validate_listener_msg
    ):
        mock_validate_listener_msg.return_value = None

        self.message.body = self.status_message
        self.service._handle_listener_message(self.message)

        self.message.ack.assert_called_once_with()

    @patch.object(PipelineService, 'add_job')
    def test_service_handle_service_message(self, mock_add_job):
        self.method['routing_key'] = 'job_document'
        self.message.body = '{"replication_job": {"id": "1", ' \
            '"cloud": "ec2", "utctime": "now"}}'
        self.service._handle_service_message(self.message)

        mock_add_job.assert_called_once_with({
            'id': '1', 'cloud': 'ec2', 'utctime': 'now'
        })
        self.message.ack.assert_called_once_with()

    def test_service_handle_service_message_invalid(self):
        self.message.body = 'Invalid format.'
        self.service._handle_service_message(self.message)

        self.message.ack.assert_called_once_with()
        self.service.log.error.assert_called_once_with(
            'Error adding job: Expecting value:'
            ' line 1 column 1 (char 0).'
        )

    @patch.object(PipelineService, 'send_email_notification')
    @patch.object(PipelineService, '_delete_job')
    @patch.object(PipelineService, '_publish_message')
    def test_service_process_job_result(
        self, mock_publish_message, mock_delete_job,
        mock_send_email_notification
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
        job.get_job_id.return_value = {'job_id': '1'}

        self.service.jobs['1'] = job
        self.service._process_job_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.service.log.info.assert_called_once_with(
            'Pass[1]: replication successful.',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(job)
        msg.ack.assert_called_once_with()

    @patch.object(PipelineService, 'send_email_notification')
    @patch.object(PipelineService, '_delete_job')
    @patch.object(PipelineService, '_publish_message')
    def test_service_process_job_result_exception(
        self, mock_publish_message, mock_delete_job,
        mock_send_email_notification
    ):
        event = Mock()
        event.job_id = '1'
        event.exception = 'Image not found!'

        job = Mock()
        job.utctime = 'now'
        job.status = 2
        job.iteration_count = 1
        job.get_job_id.return_value = {'job_id': '1'}

        self.service.jobs['1'] = job
        self.service._process_job_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.service.log.error.assert_called_once_with(
            'Pass[1]: Exception in replication: Image not found!',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(job)

    @patch.object(PipelineService, 'send_email_notification')
    @patch.object(PipelineService, '_delete_job')
    @patch.object(PipelineService, '_publish_message')
    def test_publishing_process_job_result_fail(
        self, mock_publish_message, mock_delete_job,
        mock_send_email_notification
    ):
        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.id = '1'
        job.status = 'error'
        job.utctime = 'now'
        job.iteration_count = 1
        job.get_job_id.return_value = {'job_id': '1'}

        self.service.jobs['1'] = job
        self.service._process_job_result(event)

        self.service.log.error.assert_called_once_with(
            'Pass[1]: Error occurred in replication.',
            extra={'job_id': '1'}
        )
        mock_delete_job('1')
        mock_publish_message.assert_called_once_with(job)

    @patch.object(PipelineService, '_get_status_message')
    @patch.object(PipelineService, 'publish_job_result')
    def test_service_publish_message(
        self, mock_publish, mock_get_status_message
    ):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'

        mock_get_status_message.return_value = self.status_message
        self.service._publish_message(job)
        mock_publish.assert_called_once_with(
            'publisher',
            self.status_message
        )

    @patch.object(PipelineService, '_get_status_message')
    @patch.object(PipelineService, '_publish')
    def test_service_publish_message_exception(
        self, mock_publish, mock_get_status_message
    ):
        job = Mock()
        job.id = '1'
        job.status = 'error'
        job.get_job_id.return_value = {'job_id': '1'}

        mock_get_status_message.return_value = self.error_message
        mock_publish.side_effect = AMQPError('Unable to connect to RabbitMQ.')

        self.service._publish_message(job)
        self.service.log.warning.assert_called_once_with(
            'Message not received: {0}'.format(self.error_message),
            extra={'job_id': '1'}
        )

    @patch.object(PipelineService, '_start_job')
    def test_service_schedule_duplicate_job(
        self, mock_start_job
    ):
        job = Mock()
        job.utctime = 'always'
        self.service.jobs['1'] = job

        scheduler = Mock()
        scheduler.add_job.side_effect = ConflictingIdError('Conflicting jobs.')
        self.service.scheduler = scheduler

        self.service._schedule_job('1')
        self.service.log.warning.assert_called_once_with(
            'Job already running. Received multiple '
            'listener messages.',
            extra={'job_id': '1'}
        )
        scheduler.add_job.assert_called_once_with(
            self.service._start_job,
            args=('1',),
            id='1',
            max_instances=1,
            misfire_grace_time=None,
            coalesce=True
        )

    @pytest.mark.parametrize(
        "method",
        NOT_IMPL_METHODS,
        ids=NOT_IMPL_METHODS
    )
    def test_service_not_implemented_methods(self, method):
        mock_arg = MagicMock()

        with pytest.raises(NotImplementedError) as error:
            getattr(self.service, method)(mock_arg)
        assert str(error.value) == 'Implement in child service.'

    @patch.object(PipelineService, 'consume_credentials_queue')
    @patch.object(PipelineService, 'consume_queue')
    @patch.object(PipelineService, 'close_connection')
    def test_service_start(
        self, mock_close_connection, mock_consume_queue,
        mock_consume_credentials_queue
    ):
        self.service.channel = self.channel
        self.service.start()

        self.channel.start_consuming.assert_called_once_with()
        mock_consume_queue.assert_has_calls([
            call(self.service._handle_service_message),
            call(
                self.service._handle_listener_message,
                queue_name='listener'
            )
        ])
        mock_consume_credentials_queue.assert_called_once_with(
            self.service._handle_credentials_response
        )
        mock_close_connection.assert_called_once_with()

    @patch.object(PipelineService, 'consume_credentials_queue')
    @patch.object(PipelineService, 'close_connection')
    def test_service_start_exception(
        self, mock_close_connection, mock_consume_credentials_queue
    ):
        self.service.channel = self.channel

        self.channel.start_consuming.side_effect = KeyboardInterrupt()
        self.service.start()

        mock_close_connection.assert_called_once_with()
        mock_close_connection.reset_mock()
        self.channel.start_consuming.side_effect = Exception(
            'Cannot start consuming.'
        )

        with pytest.raises(Exception) as error:
            self.service.start()

        assert 'Cannot start consuming.' == str(error.value)

    def test_service_validate_listener_msg(self):
        job = MagicMock()
        self.service.jobs = {'1': job}
        message = '{' \
                  '"testing_result": {' \
                  '"status": "success", "id": "1", ' \
                  '"cloud_image_name": "name"' \
                  '}}'

        result = self.service._validate_listener_msg(message)
        assert result == job

    def test_service_validate_listener_msg_invalid(self):
        message = '{"fake_result": {"status": "success"}}'
        result = self.service._validate_listener_msg(message)
        assert result is None

    def test_service_validate_listener_msg_no_job(self):
        message = '{' \
                  '"testing_result": {' \
                  '"status": "success", "id": "1", ' \
                  '"cloud_image_name": "name"' \
                  '}}'
        result = self.service._validate_listener_msg(message)
        assert result is None

    def test_service_validate_base_msg_missing_id(self):
        message = {'status': 'success'}
        result = self.service._validate_base_msg(
            message, ['cloud_image_name']
        )
        assert result is False

    @patch.object(PipelineService, '_cleanup_job')
    def test_service_validate_base_msg_failed(self, mock_cleanup_job):
        message = {
            'id': '1',
            'status': 'failed',
            'cloud_image_name': 'name'
        }
        job = MagicMock()
        self.service.jobs = {'1': job}

        result = self.service._validate_base_msg(
            message, ['cloud_image_name']
        )
        mock_cleanup_job.assert_called_once_with(job, 'failed')
        assert result is False

    def test_service_validate_base_msg_missing_arg(self):
        message = {
            'id': '1',
            'status': 'success'
        }
        job = MagicMock()
        self.service.jobs = {'1': job}

        result = self.service._validate_base_msg(
            message, ['cloud_image_name']
        )
        assert result is False

    def test_service_start_job(self):
        job = Mock()
        self.service.jobs['1'] = job
        self.service.host = 'localhost'

        self.service._start_job('1')
        job.process_job.assert_called_once_with()

    def test_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = "success"
        job.cloud_image_name = 'image123'
        job.source_regions = {'us-east-2': 'ami-123456'}

        data = self.service._get_status_message(job)
        assert data == self.status_message
