import pytest

from unittest.mock import call, MagicMock, Mock, patch

from amqpstorm import AMQPError

from apscheduler.jobstores.base import ConflictingIdError

from mash.services.base_defaults import Defaults
from mash.services.mash_service import MashService
from mash.services.listener_service import ListenerService
from mash.mash_exceptions import MashListenerServiceException
from mash.utils.json_format import JsonFormat


class TestListenerService(object):
    @patch.object(MashService, '__init__')
    def setup_method(
        self, method, mock_base_init
    ):
        mock_base_init.return_value = None
        self.config = Mock()
        self.config.config_data = None
        self.config.get_service_names.return_value = [
            'obs', 'upload', 'test', 'replicate', 'publish',
            'deprecate'
        ]
        self.config.get_job_directory.return_value = '/var/lib/mash/replicate_jobs/'
        self.config.get_base_thread_pool_count.return_value = 10

        self.channel = Mock()
        self.channel.basic_ack.return_value = None

        self.connection = Mock()

        self.tag = Mock()
        self.method = {'delivery_tag': self.tag}

        self.message = MagicMock(
            channel=self.channel,
            method=self.method,
        )

        self.msg_properties = {
            'content_type': 'application/json',
            'delivery_mode': 2
        }

        self.error_message = JsonFormat.json_message({
            "replicate_result": {
                "id": "1",
                "status": "failed"
            }
        })
        self.status_message = JsonFormat.json_message({
            "replicate_result": {
                "cloud_image_name": "image123",
                "id": "1",
                "status": "success"
            }
        })

        self.service = ListenerService()
        self.service.encryption_keys_file = 'encryption_keys.file'
        self.service.jwt_secret = 'a-secret'
        self.service.jwt_algorithm = 'HS256'
        self.service.jobs = {}
        self.service.log = Mock()

        self.service.channel = self.channel
        self.service.config = self.config

        scheduler = Mock()
        self.service.scheduler = scheduler

        self.service.service_exchange = 'replicate'
        self.service.service_queue = 'service'
        self.service.listener_queue = 'listener'
        self.service.job_document_key = 'job_document'
        self.service.listener_msg_key = 'listener_msg'
        self.service.prev_service = 'test'
        self.service.custom_args = None
        self.service.listener_msg_args = ['cloud_image_name']
        self.service.status_msg_args = ['cloud_image_name']

    @patch('mash.services.listener_service.os.makedirs')
    @patch.object(ListenerService, 'bind_queue')
    @patch('mash.services.listener_service.restart_jobs')
    @patch('mash.services.listener_service.setup_logfile')
    @patch.object(ListenerService, 'start')
    def test_service_post_init(
        self, mock_start,
        mock_setup_logfile, mock_restart_jobs,
        mock_bind_queue, mock_makedirs
    ):
        self.service.config = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/service_service.log'

        with pytest.raises(MashListenerServiceException):
            self.service.post_init()

        self.service.custom_args = {
            'listener_msg_args': ['source_regions'],
            'status_msg_args': ['source_regions'],
            'job_factory': Mock()
        }
        self.config.get_job_directory.reset_mock()
        mock_makedirs.reset_mock()

        self.service.post_init()

        self.config.get_job_directory.assert_called_once_with('replicate')
        mock_makedirs.assert_called_once_with(
            '/var/lib/mash/replicate_jobs/', exist_ok=True
        )

        self.config.get_log_file.assert_called_once_with('replicate')
        mock_setup_logfile.assert_called_once_with(
            '/var/log/mash/service_service.log'
        )

        mock_bind_queue.assert_has_calls([
            call('replicate', 'job_document', 'service'),
            call('test', 'listener_msg', 'listener')
        ])
        mock_restart_jobs.assert_called_once_with(
            '/var/lib/mash/replicate_jobs/',
            self.service._add_job
        )
        mock_start.assert_called_once_with()

    @patch('mash.services.listener_service.os.makedirs')
    @patch.object(Defaults, 'get_job_directory')
    @patch.object(ListenerService, 'bind_queue')
    @patch('mash.services.listener_service.restart_jobs')
    @patch('mash.services.listener_service.setup_logfile')
    @patch.object(ListenerService, 'start')
    def test_service_post_init_custom_args(
        self, mock_start,
        mock_setup_logfile, mock_restart_jobs,
        mock_bind_queue, mock_get_job_directory, mock_makedirs
    ):
        mock_makedirs.return_value = True
        self.service.config = self.config
        self.service.custom_args = {
            'listener_msg_args': ['source_regions'],
            'status_msg_args': ['source_regions'],
            'job_factory': Mock()
        }
        self.config.get_log_file.return_value = \
            '/var/log/mash/service_service.log'

        self.service.post_init()

    @patch.object(ListenerService, '_delete_job')
    @patch.object(ListenerService, '_publish_message')
    def test_service_cleanup_job(
        self, mock_publish_message, mock_delete_job
    ):
        job = Mock()
        job.id = '1'
        job.status = 'failed'
        job.utctime = 'now'
        job.get_job_id.return_value = {'job_id': '1'}
        job.get_status_message.return_value = {'id': '1', 'status': 'failed'}

        self.service.jobs['1'] = job
        self.service._cleanup_job('1')

        self.service.log.warning.assert_called_once_with(
            'Failed upstream.',
            extra={'job_id': '1'}
        )
        mock_delete_job.assert_called_once_with('1')
        msg = {"replicate_result": {"id": "1", "status": "failed"}}
        mock_publish_message.assert_called_once_with(
            JsonFormat.json_message(msg),
            '1'
        )

    def test_service_add_job_exists(self):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id}

        self.service.jobs[job.id] = Mock()
        self.service._add_job({'id': job.id, 'cloud': 'ec2'})

        self.service.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': job.id}
        )

    @patch('mash.services.listener_service.persist_json')
    def test_service_add_job(self, mock_persist_json):
        job = Mock()
        job.id = '1'
        job.get_job_id.return_value = {'job_id': '1'}

        factory = Mock()
        factory.create_job.return_value = job

        self.service.job_factory = factory
        self.service.job_directory = 'tmp-dir/'

        job_config = {'id': '1', 'cloud': 'ec2'}
        self.service._add_job(job_config)

        assert job.log_callback == self.service.log
        assert job.job_file == 'tmp-dir/job-1.json'
        self.service.log.info.assert_called_once_with(
            'Job queued, awaiting listener message.',
            extra={'job_id': '1'}
        )

    def test_service_add_job_exception(self):
        job_config = {'id': '1', 'cloud': 'ec2'}
        factory = Mock()
        factory.create_job.side_effect = Exception(
            'Cannot create job'
        )
        self.service.job_factory = factory
        self.service._add_job(job_config)
        self.service.log.error.assert_called_once_with(
            'Invalid job: Cannot create job.'
        )

    @patch('mash.services.listener_service.remove_file')
    @patch.object(ListenerService, 'unbind_queue')
    def test_service_delete_job(self, mock_unbind_queue, mock_remove_file):
        job = Mock()
        job.id = '1'
        job.job_file = 'job-test.json'
        job.last_service = 'replicate'
        job.status = 'success'
        job.utctime = 'now'
        job.get_job_id.return_value = {'job_id': '1'}

        self.service.jobs['1'] = job
        self.service._delete_job('1')

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

    @patch.object(ListenerService, '_schedule_job')
    def test_service_handle_listener_message(self, mock_schedule_job):
        job = Mock()
        job.id = '1'
        job.utctime = 'now'
        self.service.jobs['1'] = job

        self.message.body = JsonFormat.json_message({
            "test_result": {
                "cloud_image_name": "image123",
                "id": "1",
                "status": "success",
                "errors": []
            }
        })
        self.service._handle_listener_message(self.message)

        assert self.service.jobs['1'].listener_msg == self.message
        mock_schedule_job.assert_called_once_with('1')

    def test_service_handle_listener_message_no_job(self):
        self.message.body = JsonFormat.json_message({
            "test_result": {
                "cloud_image_name": "image123",
                "id": "1",
                "status": "success",
                "errors": []
            }
        })
        self.service._handle_listener_message(self.message)
        self.message.ack.assert_called_once_with()

    def test_service_handle_listener_msg_invalid(self):
        self.message.body = self.status_message
        self.service._handle_listener_message(self.message)

        self.message.ack.assert_called_once_with()

    @patch.object(ListenerService, '_cleanup_job')
    def test_service_handle_listener_message_failed(self, mock_cleanup_job):
        job = Mock()
        job.id = '1'
        job.utctime = 'now'
        self.service.jobs['1'] = job

        self.message.body = JsonFormat.json_message({
            "test_result": {
                "cloud_image_name": "image123",
                "id": "1",
                "status": "failed",
                "errors": ['Something went terribly wrong!']
            }
        })
        self.service._handle_listener_message(self.message)
        mock_cleanup_job.assert_called_once_with('1')

    @patch.object(ListenerService, '_add_job')
    def test_service_handle_service_message(self, mock_add_job):
        self.method['routing_key'] = 'job_document'
        self.message.body = '{"replicate_job": {"id": "1", ' \
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

    @patch.object(ListenerService, '_get_status_message')
    @patch.object(ListenerService, '_delete_job')
    @patch.object(ListenerService, '_publish_message')
    def test_service_process_job_result(
        self, mock_publish_message, mock_delete_job,
        mock_get_status_msg
    ):
        event = Mock()
        event.job_id = '1'
        event.exception = None

        msg = Mock()

        job = Mock()
        job.id = '1'
        job.utctime = 'now'
        job.status = 'success'
        job.listener_msg = msg
        job.get_job_id.return_value = {'job_id': '1'}

        mock_get_status_msg.return_value = '{"status": "message"}'

        self.service.jobs['1'] = job
        self.service._process_job_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.service.log.info.assert_called_once_with(
            'replicate successful.',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(
            '{"status": "message"}',
            '1'
        )
        msg.ack.assert_called_once_with()

    @patch.object(ListenerService, '_get_status_message')
    @patch.object(ListenerService, '_delete_job')
    @patch.object(ListenerService, '_publish_message')
    def test_service_process_job_result_exception(
        self, mock_publish_message, mock_delete_job,
        mock_get_status_msg
    ):
        event = Mock()
        event.job_id = '1'
        event.exception = 'Image not found!'

        job = Mock()
        job.id = '1'
        job.utctime = 'now'
        job.status = 2
        job.status_msg = {'errors': []}
        job.get_job_id.return_value = {'job_id': '1'}

        mock_get_status_msg.return_value = '{"status": "message"}'

        self.service.jobs['1'] = job
        self.service._process_job_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.service.log.error.assert_called_once_with(
            'Exception in replicate: Image not found!',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(
            '{"status": "message"}',
            '1'
        )

    @patch.object(ListenerService, '_delete_job')
    @patch.object(ListenerService, '_publish_message')
    def test_publishing_process_job_result_fail(
        self, mock_publish_message, mock_delete_job
    ):
        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.id = '1'
        job.status = 'error'
        job.utctime = 'now'
        job.get_job_id.return_value = {'job_id': '1'}
        job.get_status_message.return_value = {"id": "1", "status": "error"}

        self.service.jobs['1'] = job
        self.service._process_job_result(event)

        self.service.log.error.assert_called_once_with(
            'Error occurred in replicate.',
            extra={'job_id': '1'}
        )
        mock_delete_job('1')
        msg = {"replicate_result": {"id": "1", "status": "error"}}
        mock_publish_message.assert_called_once_with(
            JsonFormat.json_message(msg),
            '1'
        )

    def test_service_process_job_missed(self):
        event = Mock()
        event.job_id = '1'
        event.code = 2 ** 14

        msg = Mock()

        job = Mock()
        job.id = '1'
        job.utctime = 'now'
        job.status = 'success'
        job.listener_msg = msg
        job.get_job_id.return_value = {'job_id': '1'}

        self.service.jobs['1'] = job
        self.service._process_job_missed(event)

        self.service.log.warning.assert_called_once_with(
            'Job missed during replicate.',
            extra={'job_id': '1'}
        )

    @patch.object(ListenerService, '_get_status_message')
    @patch.object(ListenerService, 'publish_job_result')
    def test_service_publish_message(
        self, mock_publish, mock_get_status_message
    ):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'

        mock_get_status_message.return_value = self.status_message
        self.service._publish_message('{"test": "message"}', job.id)
        mock_publish.assert_called_once_with(
            'replicate',
            '{"test": "message"}'
        )

    @patch.object(ListenerService, '_get_status_message')
    @patch.object(ListenerService, '_publish')
    def test_service_publish_message_exception(
        self, mock_publish, mock_get_status_message
    ):
        job = Mock()
        job.id = '1'
        job.status = 'error'
        job.get_job_id.return_value = {'job_id': '1'}

        mock_get_status_message.return_value = self.error_message
        mock_publish.side_effect = AMQPError('Unable to connect to RabbitMQ.')

        self.service._publish_message('{"test": "message"}', job.id)
        self.service.log.warning.assert_called_once_with(
            'Message not received: {0}'.format('{"test": "message"}'),
            extra={'job_id': '1'}
        )

    @patch.object(ListenerService, '_start_job')
    def test_service_schedule_duplicate_job(
        self, mock_start_job
    ):
        job = Mock()
        job.utctime = 'now'
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

    @patch.object(ListenerService, 'consume_queue')
    def test_service_start(
        self, mock_consume_queue
    ):
        self.service.channel = self.channel
        self.service.start()

        self.channel.start_consuming.assert_called_once_with()
        mock_consume_queue.assert_has_calls([
            call(
                self.service._handle_service_message,
                'service',
                'replicate'
            ),
            call(
                self.service._handle_listener_message,
                'listener',
                'test'
            )
        ])

    @patch.object(ListenerService, 'close_connection')
    def test_service_start_exception(self, mock_close_connection):
        self.service.channel = self.channel
        self.channel.start_consuming.side_effect = Exception(
            'Cannot start consuming.'
        )

        with pytest.raises(Exception) as error:
            self.service.start()

        mock_close_connection.assert_called_once_with()
        assert 'Cannot start consuming.' == str(error.value)

    def test_get_prev_service(self):
        # Test service with prev service
        self.service.service_exchange = 'test'
        prev_service = self.service._get_previous_service()
        assert prev_service == 'upload'

        # Test service not in pipeline
        self.service.service_exchange = 'credentials'
        prev_service = self.service._get_previous_service()
        assert prev_service is None

        # Test service as beginning of pipeline
        self.service.service_exchange = 'obs'
        prev_service = self.service._get_previous_service()
        assert prev_service is None

    @patch('mash.services.mash_service.Connection')
    def test_publish_job_result(self, mock_connection):
        mock_connection.return_value = self.connection
        self.service.publish_job_result('exchange', 'message')
        self.channel.basic.publish.assert_called_once_with(
            body='message', exchange='exchange', mandatory=True,
            properties=self.msg_properties, routing_key='listener_msg'
        )

    def test_service_start_job(self):
        job = Mock()
        self.service.jobs['1'] = job
        self.service.host = 'localhost'

        self.service._start_job('1')
        job.process_job.assert_called_once_with()

    def test_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.get_status_message.return_value = {
            'id': '1',
            'status': 'success',
            'cloud_image_name': 'image123'
        }

        data = self.service._get_status_message(job)
        assert data == self.status_message

    @patch.object(ListenerService, 'close_connection')
    def test_service_stop(self, mock_close_connection):
        frame = Mock()
        self.service.stop(signum=15, frame=frame)
        self.service.log.info.assert_called_once_with(
            'Got a TERM/INTERRUPT signal, shutting down gracefully.'
        )
        mock_close_connection.assert_called_once_with()
