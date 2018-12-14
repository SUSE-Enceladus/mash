import io

from pytest import raises
from unittest.mock import call, MagicMock, Mock, patch

from amqpstorm import AMQPError
from apscheduler.jobstores.base import JobLookupError

from mash.services.base_service import BaseService
from mash.services.testing.service import TestingService
from mash.services.testing.azure_job import AzureTestingJob
from mash.services.testing.ec2_job import EC2TestingJob
from mash.services.testing.gce_job import GCETestingJob
from mash.utils.json_format import JsonFormat

open_name = "builtins.open"


class TestIPATestingService(object):

    @patch.object(BaseService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None

        self.config = Mock()
        self.config.config_data = None
        self.config.get_ipa_timeout.return_value = 600

        self.channel = Mock()
        self.channel.basic_ack.return_value = None

        self.tag = Mock()
        self.method = {'delivery_tag': self.tag}

        self.message = MagicMock(
            channel=self.channel,
            method=self.method,
        )

        self.testing = TestingService()
        self.testing.jobs = {}
        self.testing.log = Mock()
        self.testing.service_exchange = 'testing'
        self.testing.service_queue = 'service'
        self.testing.job_document_key = 'job_document'
        self.testing.listener_msg_key = 'listener_msg'
        self.testing.listener_queue = 'listener'
        self.testing.ssh_private_key_file = 'private_ssh_key.file'

        self.error_message = JsonFormat.json_message({
            "testing_result": {
                "id": "1", "status": "error"
            }
        })

        self.status_message = JsonFormat.json_message({
            "testing_result": {
                "cloud_image_name": "image123",
                "id": "1",
                "source_regions": {"us-east-2": "ami-123456"},
                "status": "success"
            }
        })

    @patch('mash.services.testing.service.os')
    @patch.object(TestingService, '_create_ssh_key_pair')
    @patch.object(TestingService, 'bind_credentials_queue')
    @patch.object(TestingService, 'set_logfile')
    @patch.object(TestingService, 'start')
    @patch.object(TestingService, 'restart_jobs')
    def test_testing_post_init(
        self, mock_restart_jobs,
        mock_start, mock_set_logfile, mock_bind_creds_queue,
        mock_create_ssh_key_pair, mock_os
    ):
        mock_os.path.exists.return_value = False
        self.testing.config = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/testing_service.log'

        self.testing.post_init()

        self.config.get_log_file.assert_called_once_with('testing')
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/testing_service.log'
        )
        mock_create_ssh_key_pair.assert_called_once_with()
        mock_bind_creds_queue.assert_called_once_with()
        mock_restart_jobs.assert_called_once_with(self.testing._add_job)
        mock_start.assert_called_once_with()

    @patch.object(TestingService, '_create_job')
    def test_testing_add_job(self, mock_create_job):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id, 'provider': 'ec2'}

        self.testing._add_job({'id': job.id, 'provider': 'ec2'})

        mock_create_job.assert_called_once_with(
            EC2TestingJob, {'id': job.id, 'provider': 'ec2'}
        )

    @patch.object(TestingService, '_create_job')
    def test_testing_add_azure_job(self, mock_create_job):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id, 'provider': 'azure'}

        self.testing._add_job({'id': job.id, 'provider': 'azure'})

        mock_create_job.assert_called_once_with(
            AzureTestingJob, {'id': job.id, 'provider': 'azure'}
        )

    @patch.object(TestingService, '_create_job')
    def test_testing_add_gce_job(self, mock_create_job):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id, 'provider': 'gce'}

        self.testing._add_job({'id': job.id, 'provider': 'gce'})

        mock_create_job.assert_called_once_with(
            GCETestingJob, {'id': job.id, 'provider': 'gce'}
        )

    def test_testing_add_job_exists(self):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id}

        self.testing.jobs[job.id] = Mock()
        self.testing._add_job({'id': job.id, 'provider': 'ec2'})

        self.testing.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': job.id}
        )

    def test_testing_add_job_invalid(self):
        self.testing._add_job({'id': '1', 'provider': 'fake'})
        self.testing.log.error.assert_called_once_with(
            'Provider fake is not supported.'
        )

    @patch.object(TestingService, 'persist_job_config')
    def test_testing_create_job(
        self, mock_persist_config
    ):
        mock_persist_config.return_value = 'temp-config.json'
        self.testing.config = self.config

        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id}

        job_class = Mock()
        job_class.return_value = job
        job_config = {'id': job.id, 'provider': 'ec2'}
        self.testing._create_job(job_class, job_config)

        job_class.assert_called_once_with(
            id=job.id, ipa_timeout=600, provider='ec2',
            ssh_private_key_file='private_ssh_key.file'
        )
        job.set_log_callback.assert_called_once_with(
            self.testing.log_job_message
        )
        assert job.job_file == 'temp-config.json'
        self.testing.log.info.assert_called_once_with(
            'Job queued, awaiting uploader result.',
            extra={'job_id': '1'}
        )

    def test_testing_create_job_exception(self):
        job_class = Mock()
        job_class.side_effect = Exception('Cannot create job.')
        self.testing.config = self.config
        job_config = {'id': '1', 'provider': 'ec2'}

        self.testing._create_job(job_class, job_config)
        self.testing.log.exception.assert_called_once_with(
            'Invalid job configuration: Cannot create job.'
        )

    @patch('mash.services.testing.service.rsa')
    def test_create_ssh_key_pair(self, mock_rsa):
        private_key = MagicMock()
        public_key = MagicMock()

        public_key.public_bytes.return_value = b'0987654321'

        private_key.public_key.return_value = public_key
        private_key.private_bytes.return_value = b'1234567890'

        mock_rsa.generate_private_key.return_value = private_key

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.testing._create_ssh_key_pair()
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.assert_has_calls([
                call(b'1234567890'),
                call(b'0987654321')
            ])

    @patch.object(TestingService, 'unbind_queue')
    def test_testing_delete_job(self, mock_unbind_queue):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id}

        self.testing.jobs[job.id] = job
        self.testing._delete_job(job.id)

        self.testing.log.info.assert_called_once_with(
            'Deleting job.',
            extra={'job_id': job.id}
        )

    @patch.object(TestingService, '_delete_job')
    @patch.object(TestingService, '_publish_message')
    def test_testing_cleanup_job(self, mock_publish_message, mock_delete_job):
        job = Mock()
        job.id = '1'
        job.status = "success"
        job.image_id = 'image123'
        job.utctime = 'now'
        job.get_metadata.return_value = {'job_id': job.id}

        scheduler = Mock()
        scheduler.remove_job.side_effect = JobLookupError(job.id)
        self.testing.scheduler = scheduler

        self.testing.jobs[job.id] = job
        self.testing._cleanup_job(job, 1)

        self.testing.log.warning.assert_called_once_with(
            'Failed upstream.',
            extra={'job_id': job.id}
        )
        scheduler.remove_job.assert_called_once_with(job.id)
        mock_delete_job.assert_called_once_with(job.id)
        mock_publish_message.assert_called_once_with(job)

    def test_testing_delete_invalid_job(self):
        self.testing._delete_job('1')

        self.testing.log.warning.assert_called_once_with(
            'Job deletion failed, job is not queued.',
            extra={'job_id': '1'}
        )

    @patch.object(TestingService, '_schedule_job')
    @patch.object(TestingService, 'decode_credentials')
    def test_testing_handle_credentials_response(
        self, mock_decode_credentials, mock_schedule_job
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.testing.jobs[job.id] = job

        message = Mock()
        message.body = '{"jwt_token": "response"}'

        mock_decode_credentials.return_value = job.id, {'fake': 'creds'}
        self.testing._handle_credentials_response(message)

        mock_schedule_job.assert_called_once_with(job.id)
        message.ack.assert_called_once_with()

    @patch.object(TestingService, 'decode_credentials')
    def test_testing_handle_credentials_response_exceptions(
        self, mock_decode_credentials
    ):
        message = Mock()
        message.body = '{"jwt_token": "response"}'

        # Test job does not exist.
        mock_decode_credentials.return_value = '1', {'fake': 'creds'}
        self.testing._handle_credentials_response(message)
        self.testing.log.error.assert_called_once_with(
            'Credentials recieved for invalid job with ID: 1.'
        )

        # Invalid json string
        self.testing.log.error.reset_mock()
        message.body = 'invalid json string'
        self.testing._handle_credentials_response(message)
        self.testing.log.error.assert_called_once_with(
            'Invalid credentials response message: '
            'Must be a json encoded message.'
        )

        assert message.ack.call_count == 2

    @patch.object(TestingService, '_add_job')
    def test_testing_handle_jobs_add(self, mock_add_job):
        self.message.body = '{"testing_job": {"id": "1"}}'
        self.testing._handle_jobs(self.message)

        self.message.ack.assert_called_once_with()
        mock_add_job.assert_called_once_with({'id': '1'})

    def test_testing_handle_jobs_format(self):
        self.message.body = 'Invalid format.'
        self.testing._handle_jobs(self.message)

        self.message.ack.assert_called_once_with()
        self.testing.log.error.assert_called_once_with(
            'Error adding job: Expecting value:'
            ' line 1 column 1 (char 0).'
        )

    def test_testing_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = "success"
        job.cloud_image_name = 'image123'
        job.test_regions = {'us-east-2': {'account': 'test-aws'}}
        job.source_regions = {'us-east-2': 'ami-123456'}

        data = self.testing._get_status_message(job)
        assert data == self.status_message

    @patch.object(TestingService, '_delete_job')
    @patch.object(TestingService, '_publish')
    @patch.object(TestingService, '_get_status_message')
    @patch.object(TestingService, 'bind_queue')
    def test_testing_process_test_result(
        self, mock_bind_queue, mock_get_status_message,
        mock_publish, mock_delete_job
    ):
        mock_get_status_message.return_value = self.status_message

        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.id = '1'
        job.utctime = 'now'
        job.status = "success"
        job.iteration_count = 1
        job.get_metadata.return_value = {'job_id': job.id}

        self.testing.jobs[job.id] = job
        self.testing._process_test_result(event)

        mock_delete_job.assert_called_once_with(job.id)
        self.testing.log.info.assert_called_once_with(
            'Pass[1]: Testing successful.',
            extra={'job_id': job.id}
        )
        mock_get_status_message.assert_called_once_with(job)
        mock_publish.assert_called_once_with(
            'replication', 'listener_msg', self.status_message
        )

    def test_testing_process_test_result_exception(self):
        event = Mock()
        event.job_id = '1'
        event.exception = 'Broken!'

        job = Mock()
        job.utctime = 'always'
        job.status = "exception"
        job.iteration_count = 1
        job.get_metadata.return_value = {'job_id': '1'}

        message = Mock()
        job.listener_msg = message

        self.testing.jobs['1'] = job
        self.testing._process_test_result(event)

        self.testing.log.error.assert_called_once_with(
            'Pass[1]: Exception testing image: Broken!',
            extra={'job_id': '1'}
        )
        message.ack.assert_called_once_with()

    @patch.object(TestingService, '_delete_job')
    @patch.object(TestingService, 'publish_job_result')
    @patch.object(TestingService, '_get_status_message')
    def test_testing_process_test_result_fail(
        self, mock_get_status_message,
        mock_publish, mock_delete_job
    ):
        mock_get_status_message.return_value = self.error_message

        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.id = '1'
        job.cloud_image_name = 'image123'
        job.test_regions = {'us-east-2': {'account': 'test-aws'}}
        job.status = "error"
        job.utctime = 'now'
        job.iteration_count = 1
        job.get_metadata.return_value = {'job_id': job.id}

        self.testing.jobs[job.id] = job
        self.testing._process_test_result(event)

        mock_delete_job.assert_called_once_with(job.id)
        self.testing.log.error.assert_called_once_with(
            'Pass[1]: Error occurred testing image with IPA.',
            extra={'job_id': job.id}
        )
        mock_get_status_message.assert_called_once_with(job)
        mock_publish.assert_called_once_with(
            'replication', self.error_message
        )

    @patch.object(TestingService, 'bind_queue')
    @patch.object(TestingService, '_publish')
    def test_testing_publish_message(self, mock_publish, mock_bind_queue):
        job = Mock()
        job.id = '1'
        job.status = "success"
        job.cloud_image_name = 'image123'
        job.test_regions = {'us-east-2': {'account': 'test-aws'}}
        job.source_regions = {'us-east-2': 'ami-123456'}

        self.testing._publish_message(job)
        mock_publish.assert_called_once_with(
            'replication', 'listener_msg', self.status_message
        )

    @patch.object(TestingService, 'bind_queue')
    @patch.object(TestingService, '_publish')
    def test_testing_publish_message_exception(
        self, mock_publish, mock_bind_queue
    ):
        job = Mock()
        job.image_id = 'image123'
        job.id = '1'
        job.status = "error"
        job.get_metadata.return_value = {'job_id': job.id}

        mock_publish.side_effect = AMQPError('Broken')
        self.testing._publish_message(job)

        self.testing.log.warning.assert_called_once_with(
            'Message not received: {0}'.format(self.error_message),
            extra={'job_id': job.id}
        )

    def test_testing_run_test(self):
        job = Mock()
        job.provider = 'ec2'
        job.account = 'test_account'
        job.distro = 'SLES'
        job.image_id = 'image123'
        job.tests = 'test1,test2'
        self.testing.jobs['1'] = job

        self.testing._run_test('1')
        job.test_image.assert_called_once_with()

    def test_testing_schedule_job(self):
        scheduler = Mock()
        self.testing.scheduler = scheduler

        self.testing._schedule_job('1')

        self.testing.scheduler.add_job.assert_called_once_with(
            self.testing._run_test,
            args=('1',),
            id='1',
            max_instances=1,
            misfire_grace_time=None,
            coalesce=True
        )

    @patch.object(TestingService, 'publish_credentials_request')
    @patch.object(TestingService, '_validate_listener_msg')
    @patch.object(TestingService, '_run_test')
    def test_testing_handle_listener_message(
        self, mock_run_test, mock_validate_listener_msg, mock_pub_cred_request
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.credentials = None
        self.testing.jobs[job.id] = job

        mock_validate_listener_msg.return_value = job

        scheduler = Mock()
        self.testing.scheduler = scheduler

        self.message.body = JsonFormat.json_message({
            "uploader_result": {
                "id": "1",
                "image_id": "image123",
                "status": "success"
            }
        })

        self.testing._handle_listener_message(self.message)

        assert self.testing.jobs[job.id].listener_msg == self.message
        mock_pub_cred_request.assert_called_once_with(job.id)

    @patch.object(TestingService, '_schedule_job')
    @patch.object(TestingService, '_validate_listener_msg')
    @patch.object(TestingService, '_run_test')
    def test_testing_handle_listener_message_creds(
        self, mock_run_test, mock_validate_listener_msg, mock_schedule_job
    ):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.credentials = {'credentials': 'info'}
        self.testing.jobs[job.id] = job

        mock_validate_listener_msg.return_value = job

        scheduler = Mock()
        self.testing.scheduler = scheduler

        self.message.body = JsonFormat.json_message({
            "uploader_result": {
                "id": "1",
                "image_id": "image123",
                "status": "success"
            }
        })

        self.testing._handle_listener_message(self.message)

        assert self.testing.jobs[job.id].listener_msg == self.message
        mock_schedule_job.assert_called_once_with(job.id)

    @patch.object(TestingService, '_validate_listener_msg')
    def test_testing_handle_listener_message_no_job(
        self, mock_validate_listener_msg
    ):
        mock_validate_listener_msg.return_value = None

        self.message.body = JsonFormat.json_message({
            "uploader_result": {
                "id": "1"
            }
        })
        self.testing._handle_listener_message(self.message)

        self.message.ack.assert_called_once_with()

    def test_testing_validate_listener_msg(self):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        job.test_regions = {'us-east-1': {'account': 'test-aws'}}
        self.testing.jobs[job.id] = job

        self.message.body = JsonFormat.json_message({
            "uploader_result": {
                "id": "1",
                "cloud_image_name": "My image",
                "source_regions": {"us-east-1": "ami-123456"},
                "status": "success"
            }
        })
        result = self.testing._validate_listener_msg(self.message.body)

        assert result == job
        job.set_cloud_image_name.assert_called_once_with('My image')
        job.set_source_regions.assert_called_once_with(
            {'us-east-1': 'ami-123456'}
        )

    @patch.object(TestingService, '_cleanup_job')
    def test_testing_validate_listener_msg_failed(self, mock_cleanup_job):
        job = Mock()
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        self.message.body = JsonFormat.json_message({
            "uploader_result": {
                "id": "1",
                "image_id": "image123",
                "status": "error"
            }
        })
        self.testing._validate_listener_msg(self.message.body)

        mock_cleanup_job.assert_called_once_with(job, 'error')

    def test_testing_validate_listener_msg_invalid(self):
        self.message.body = ''
        result = self.testing._validate_listener_msg(self.message.body)

        assert result is None
        self.testing.log.error.assert_called_once_with(
            'Invalid uploader result file: '
        )

    def test_testing_validate_listener_msg_job_invalid(self):
        self.message.body = JsonFormat.json_message({
            "uploader_result": {"id": "2"}
        })
        result = self.testing._validate_listener_msg(self.message.body)

        assert result is None
        self.testing.log.error.assert_called_once_with(
            'Invalid testing service job with id: 2.'
        )

    def test_testing_validate_listener_msg_no_id(self):
        self.message.body = JsonFormat.json_message({
            "uploader_result": {"provider": "ec2"}
        })
        result = self.testing._validate_listener_msg(self.message.body)

        assert result is None
        self.testing.log.error.assert_called_once_with(
            'id is required in uploader result.'
        )

    def test_testing_validate_listener_msg_no_source_regions(self):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.testing.jobs[job.id] = job

        self.message.body = JsonFormat.json_message({
            "uploader_result": {
                "id": "1",
                "cloud_image_name": "My image",
                "status": "success"
            }
        })
        result = self.testing._validate_listener_msg(self.message.body)

        assert result is None
        self.testing.log.error.assert_called_once_with(
            'source_regions is required in uploader result.'
        )

    def test_testing_validate_listener_msg_no_image_name(self):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.testing.jobs[job.id] = job

        self.message.body = JsonFormat.json_message({
            "uploader_result": {"id": "1", "status": "success"}
        })
        result = self.testing._validate_listener_msg(self.message.body)

        assert result is None
        self.testing.log.error.assert_called_once_with(
            'cloud_image_name is required in uploader result.'
        )

    @patch.object(TestingService, 'consume_credentials_queue')
    @patch.object(TestingService, 'consume_queue')
    @patch.object(TestingService, 'stop')
    def test_testing_start(
        self, mock_stop, mock_consume_queue, mock_consume_credentials_queue
    ):
        scheduler = Mock()
        self.testing.scheduler = scheduler
        self.testing.channel = self.channel

        self.testing.start()
        scheduler.start.assert_called_once_with()
        self.channel.start_consuming.assert_called_once_with()
        mock_consume_queue.assert_has_calls([
            call(self.testing._handle_jobs),
            call(
                self.testing._handle_listener_message,
                queue_name='listener'
            )
        ])
        mock_consume_credentials_queue.assert_called_once_with(
            self.testing._handle_credentials_response
        )
        mock_stop.assert_called_once_with()

    @patch.object(TestingService, 'consume_credentials_queue')
    @patch.object(TestingService, 'consume_queue')
    @patch.object(TestingService, 'stop')
    def test_testing_start_exception(
        self, mock_stop, mock_consume_queue, mock_consume_credentials_queue
    ):
        scheduler = Mock()
        self.testing.scheduler = scheduler
        self.testing.channel = self.channel

        self.channel.start_consuming.side_effect = KeyboardInterrupt()
        self.testing.start()

        mock_stop.assert_called_once_with()
        mock_stop.reset_mock()
        self.channel.start_consuming.side_effect = Exception(
            'Cannot start scheduler.'
        )

        with raises(Exception) as error:
            self.testing.start()

        assert 'Cannot start scheduler.' == str(error.value)

    @patch.object(TestingService, 'close_connection')
    def test_testing_stop(self, mock_close_connection):
        scheduler = Mock()
        self.testing.scheduler = scheduler
        self.testing.channel = self.channel

        self.testing.stop()
        scheduler.shutdown.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
        self.channel.stop_consuming.assert_called_once_with()
