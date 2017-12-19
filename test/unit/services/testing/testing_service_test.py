import io

from pytest import raises
from unittest.mock import call, MagicMock, Mock, patch

from amqpstorm import AMQPError
from apscheduler.jobstores.base import JobLookupError

from mash.services.base_service import BaseService
from mash.services.testing.service import TestingService

open_name = "builtins.open"


class TestIPATestingService(object):

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

        self.testing = TestingService()
        self.testing.jobs = {}
        self.testing.log = Mock()
        self.testing.service_exchange = 'testing'

        self.error_message = '{"testing_result": ' \
            '{"id": "1", "image_id": "image123", "status": 1}}'
        self.status_message = '{"testing_result": ' \
            '{"id": "1", "image_id": "image123", "status": 0}}'

    @patch.object(TestingService, 'set_logfile')
    @patch.object(TestingService, 'stop')
    @patch.object(TestingService, 'start')
    @patch.object(TestingService, '_restart_jobs')
    @patch('mash.services.testing.service.TestingConfig')
    @patch.object(TestingService, 'bind_service_queue')
    @patch.object(TestingService, '_process_message')
    @patch.object(TestingService, 'consume_queue')
    def test_testing_post_init(
        self, mock_consume_queue, mock_process_message,
        mock_bind_service_queue, mock_testing_config, mock_restart_jobs,
        mock_start, mock_stop, mock_set_logfile
    ):
        mock_testing_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/testing_service.log'

        self.testing.post_init()

        self.config.get_log_file.assert_called_once_with()
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/testing_service.log'
        )
        mock_consume_queue.assert_called_once_with(
            mock_process_message, mock_bind_service_queue.return_value
        )
        mock_bind_service_queue.assert_called_once_with()
        mock_start.assert_called_once_with()
        mock_stop.assert_called_once_with()

    @patch.object(TestingService, 'set_logfile')
    @patch.object(TestingService, 'stop')
    @patch.object(TestingService, 'start')
    @patch.object(TestingService, '_restart_jobs')
    @patch('mash.services.testing.service.TestingConfig')
    @patch.object(TestingService, 'bind_service_queue')
    @patch.object(TestingService, '_handle_jobs')
    @patch.object(TestingService, 'consume_queue')
    def test_testing_post_init_exceptions(
        self, mock_consume_queue, mock_handle_jobs,
        mock_bind_service_queue, mock_testing_config, mock_restart_jobs,
        mock_start, mock_stop, mock_set_logfile
    ):
        mock_testing_config.return_value = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/testing_service.log'

        mock_start.side_effect = KeyboardInterrupt()

        self.testing.post_init()

        mock_stop.assert_called_once_with()
        mock_start.side_effect = Exception()
        mock_stop.reset_mock()
        with raises(Exception):
            self.testing.post_init()

        mock_stop.assert_called_once_with()

    @patch.object(TestingService, '_validate_job')
    @patch.object(TestingService, '_persist_job_config')
    @patch.object(TestingService, '_process_message')
    @patch.object(TestingService, 'consume_queue')
    @patch.object(TestingService, 'bind_listener_queue')
    def test_testing_add_job(
        self, mock_bind_listener_queue, mock_consume_queue,
        mock_process_message, mock_persist_config, mock_validate_job
    ):
        job = Mock()
        job.id = '1'
        job._get_metadata.return_value = {'job_id': '1'}

        mock_validate_job.return_value = job
        mock_persist_config.return_value = 'config_file.json'

        self.testing._add_job({'id': '1'})

        # Dict is mutable, mock compares the final value of Dict
        # not the initial value that was passed in.
        mock_validate_job.assert_called_once_with(
            {'id': '1', 'config_file': 'config_file.json'}
        )
        self.testing.log.info.assert_called_once_with(
            'Job queued, awaiting uploader result.',
            extra={'job_id': '1'}
        )

        mock_consume_queue.assert_called_once_with(
            mock_process_message, mock_bind_listener_queue.return_value
        )
        mock_bind_listener_queue.assert_called_once_with('1')

    @patch.object(TestingService, '_validate_job')
    def test_testing_add_job_exists(self, mock_validate_job):
        job = Mock()
        job.id = '1'
        job._get_metadata.return_value = {'job_id': '1'}
        mock_validate_job.return_value = job

        self.testing.jobs['1'] = Mock()
        self.testing._add_job({'id': '1'})

        mock_validate_job.assert_called_once_with({'id': '1'})
        self.testing.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': '1'}
        )

    @patch.object(TestingService, '_validate_job')
    def test_testing_add_job_invalid(self, mock_validate_job):
        mock_validate_job.return_value = None

        self.testing._add_job({'id': '1'})
        mock_validate_job.assert_called_once_with({'id': '1'})

    @patch.object(TestingService, 'delete_listener_queue')
    def test_testing_delete_job(
        self, mock_delete_listener_queue
    ):
        job = Mock()
        job.id = '1'
        job._get_metadata.return_value = {'job_id': '1'}

        scheduler = Mock()
        scheduler.remove_job.side_effect = JobLookupError('1')

        self.testing.scheduler = scheduler
        self.testing.jobs['1'] = job
        self.testing._delete_job('1')

        self.testing.log.info.assert_called_once_with(
            'Deleting job.',
            extra={'job_id': '1'}
        )

        mock_delete_listener_queue.assert_called_once_with('1')
        scheduler.remove_job.assert_called_once_with('1')

    @patch.object(TestingService, '_delete_job')
    @patch.object(TestingService, '_publish_message')
    def test_testing_cleanup_job(self, mock_publish_message, mock_delete_job):
        job = Mock()
        job.id = '1'
        job.status = 0
        job.image_id = 'image123'
        job.utctime = 'now'
        job._get_metadata.return_value = {'job_id': '1'}

        self.testing.jobs['1'] = job
        self.testing._cleanup_job(job, 1)

        self.testing.log.warning.assert_called_once_with(
            'Failed upstream.',
            extra={'job_id': '1'}
        )
        mock_delete_job.assert_called_once_with('1')
        mock_publish_message.assert_called_once_with(job)

    def test_testing_delete_invalid_job(self):
        self.testing._delete_job('1')

        self.testing.log.warning.assert_called_once_with(
            'Job deletion failed, job is not queued.',
            extra={'job_id': '1'}
        )

    @patch.object(TestingService, '_delete_job')
    def test_testing_handle_jobs_delete(self, mock_delete_job):
        self.message.body = '{"testing_job_delete": "1"}'
        self.testing._handle_jobs(self.message)

        self.message.ack.assert_called_once_with()
        mock_delete_job.assert_called_once_with('1')

    @patch.object(TestingService, '_add_job')
    def test_testing_handle_jobs_add(self, mock_add_job):
        self.message.body = '{"testing_job_add": {"id": "1"}}'
        self.testing._handle_jobs(self.message)

        self.message.ack.assert_called_once_with()
        mock_add_job.assert_called_once_with({'id': '1'})

    @patch.object(TestingService, '_notify_invalid_config')
    def test_testing_handle_jobs_invalid(self, mock_notify):
        self.message.body = '{"testing_job_update": {"id": "1"}}'

        self.testing._handle_jobs(self.message)

        self.message.ack.assert_called_once_with()
        self.testing.log.error.assert_called_once_with(
            'Invalid testing job: Desc must contain either'
            'testing_job_add or testing_job_delete key.'
        )
        mock_notify.assert_called_once_with(self.message.body)

    @patch.object(TestingService, '_notify_invalid_config')
    def test_testing_handle_jobs_format(self, mock_notify):
        self.message.body = 'Invalid format.'
        self.testing._handle_jobs(self.message)

        self.message.ack.assert_called_once_with()
        self.testing.log.error.assert_called_once_with(
            'Invalid job config file: Expecting value:'
            ' line 1 column 1 (char 0).'
        )
        mock_notify.assert_called_once_with(self.message.body)

    def test_testing_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = 0
        job.image_id = 'image123'

        data = self.testing._get_status_message(job)
        assert data == self.status_message

    def test_testing_log_job_message(self):
        self.testing._log_job_message('Test message', {'job_id': '1'})

        self.testing.log.info.assert_called_once_with(
            'Test message',
            extra={'job_id': '1'}
        )

    @patch.object(TestingService, '_publish')
    def test_testing_notify(self, mock_publish):
        self.testing._notify_invalid_config('invalid')
        mock_publish.assert_called_once_with(
            'jobcreator',
            'invalid_config',
            'invalid'
        )

    @patch.object(TestingService, '_publish')
    def test_testing_notify_exception(self, mock_publish):
        mock_publish.side_effect = AMQPError('Broken')
        self.testing._notify_invalid_config('invalid')

        self.testing.log.warning.assert_called_once_with(
            'Message not received: {0}'.format('invalid')
        )

    @patch('mash.services.testing.service.NamedTemporaryFile')
    def test_testing_persist_job_config(self, mock_temp_file):
        self.testing.jobs_dir = 'tmp-dir'

        tmp_file = Mock()
        tmp_file.name = 'tmp-dir/job-test.json'
        mock_temp_file.return_value = tmp_file

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.testing._persist_job_config({'id': '1'})
            file_handle = mock_open.return_value.__enter__.return_value
            # Dict is mutable, mock compares the final value of Dict
            # not the initial value that was passed in.
            file_handle.write.assert_called_with(
                u'{"config_file": "tmp-dir/job-test.json", "id": "1"}'
            )

    @patch.object(TestingService, '_test_image')
    def test_testing_process_message_listener_event(self, mock_test_image):
        self.method['routing_key'] = 'listener_1'
        self.testing._process_message(self.message)

        mock_test_image.assert_called_once_with(self.message)

    @patch.object(TestingService, '_handle_jobs')
    def test_testing_process_message_service_event(self, mock_handle_jobs):
        self.method['routing_key'] = 'service_event'
        self.testing._process_message(self.message)

        mock_handle_jobs.assert_called_once_with(self.message)

    @patch.object(TestingService, '_delete_job')
    @patch.object(TestingService, '_publish')
    @patch.object(TestingService, '_get_status_message')
    @patch.object(TestingService, '_bind_queue')
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
        job.status = 0
        job.iteration_count = 1
        job._get_metadata.return_value = {'job_id': '1'}

        self.testing.jobs['1'] = job
        self.testing._process_test_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.testing.log.info.assert_called_once_with(
            'Pass[1]: Testing successful.',
            extra={'job_id': '1'}
        )
        mock_get_status_message.assert_called_once_with(job)
        mock_bind_queue.assert_called_once_with('publisher', 'listener_1')
        mock_publish.assert_called_once_with(
            'publisher',
            'listener_1',
            self.status_message
        )

    @patch.object(TestingService, '_publish_message')
    def test_testing_process_test_result_exception(
        self, mock_publish_message
    ):
        event = Mock()
        event.job_id = '1'
        event.exception = 'Broken!'

        job = Mock()
        job.utctime = 'always'
        job.status = 2
        job.iteration_count = 1
        job._get_metadata.return_value = {'job_id': '1'}

        self.testing.jobs['1'] = job
        self.testing._process_test_result(event)

        self.testing.log.error.assert_called_once_with(
            'Pass[1]: Exception testing image: Broken!',
            extra={'job_id': '1'}
        )
        mock_publish_message.assert_called_once_with(job)

    @patch.object(TestingService, '_publish')
    @patch.object(TestingService, '_get_status_message')
    @patch.object(TestingService, '_bind_queue')
    def test_testing_process_test_result_fail(
        self, mock_bind_queue, mock_get_status_message, mock_publish
    ):
        mock_get_status_message.return_value = self.error_message

        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.id = '1'
        job.image_id = 'image123'
        job.status = 1
        job.utctime = 'always'
        job.iteration_count = 1
        job._get_metadata.return_value = {'job_id': '1'}

        self.testing.jobs['1'] = job
        self.testing._process_test_result(event)

        self.testing.log.error.assert_called_once_with(
            'Pass[1]: Error occurred testing image with IPA.',
            extra={'job_id': '1'}
        )
        mock_get_status_message.assert_called_once_with(job)
        mock_bind_queue.assert_called_once_with('publisher', 'listener_1')
        mock_publish.assert_called_once_with(
            'publisher',
            'listener_1',
            self.error_message
        )

    @patch.object(TestingService, '_bind_queue')
    @patch.object(TestingService, '_publish')
    def test_testing_publish_message(self, mock_publish, mock_bind_queue):
        job = Mock()
        job.id = '1'
        job.status = 0
        job.image_id = 'image123'

        self.testing._publish_message(job)
        mock_bind_queue.assert_called_once_with('publisher', 'listener_1')
        mock_publish.assert_called_once_with(
            'publisher',
            'listener_1',
            self.status_message
        )

    @patch.object(TestingService, '_bind_queue')
    @patch.object(TestingService, '_publish')
    def test_testing_publish_message_exception(
        self, mock_publish, mock_bind_queue
    ):
        job = Mock()
        job.image_id = 'image123'
        job.id = '1'
        job.status = 1
        job._get_metadata.return_value = {'job_id': '1'}

        mock_publish.side_effect = AMQPError('Broken')
        self.testing._publish_message(job)

        mock_bind_queue.assert_called_once_with('publisher', 'listener_1')
        self.testing.log.warning.assert_called_once_with(
            'Message not received: {0}'.format(self.error_message),
            extra={'job_id': '1'}
        )

    @patch.object(TestingService, '_add_job')
    @patch('mash.services.testing.service.json.load')
    @patch('mash.services.testing.service.os.listdir')
    def test_testing_restart_jobs(
        self, mock_os_listdir, mock_json_load, mock_add_job
    ):
        self.testing.jobs_dir = 'tmp-dir'
        mock_os_listdir.return_value = ['job-123.json']
        mock_json_load.return_value = {'id': '1'}

        with patch(open_name, create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.testing._restart_jobs()

            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.call_count == 1

        mock_add_job.assert_called_once_with({'id': '1'})

    def test_testing_run_test(self):
        job = Mock()
        job.provider = 'EC2'
        job.account = 'test_account'
        job.distro = 'SLES'
        job.image_id = 'image123'
        job.tests = 'test1,test2'
        self.testing.jobs['1'] = job
        self.testing.host = 'localhost'

        self.testing._run_test('1')
        job.test_image.assert_called_once_with(host='localhost')

    @patch.object(TestingService, '_run_test')
    def test_testing_test_image(self, mock_run_test):
        job = Mock()
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        scheduler = Mock()
        self.testing.scheduler = scheduler

        self.message.body = \
            '{"uploader_result": {"id": "1", ' \
            '"image_id": "image123", "status": 0}}'

        self.testing._test_image(self.message)

        assert self.testing.jobs['1'].image_id == 'image123'
        assert self.testing.jobs['1'].listener_msg == self.message
        scheduler.add_job.assert_called_once_with(
            mock_run_test,
            args=('1',),
            id='1',
            max_instances=1,
            misfire_grace_time=None,
            coalesce=True
        )

    @patch.object(TestingService, '_cleanup_job')
    def test_testing_test_image_failed(self, mock_cleanup_job):
        job = Mock()
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        self.message.body = \
            '{"uploader_result": {"id": "1", ' \
            '"image_id": "image123", "status": 1}}'
        self.testing._test_image(self.message)

        mock_cleanup_job.assert_called_once_with(job, 1)
        self.message.ack.assert_called_once_with()

    def test_testing_test_image_job_none(self):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        self.message.body = ''
        self.testing._test_image(self.message)

        self.message.ack.assert_called_once_with()
        self.testing.log.error.assert_has_calls(
            [
                call('Invalid uploader result file: '),
                call('No id in uploader result file.')
            ]
        )

    def test_testing_test_image_job_invalid(self):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        self.message.body = '{"uploader_result": {"id": "2"}}'
        self.testing._test_image(self.message)

        self.message.ack.assert_called_once_with()
        self.testing.log.error.assert_called_once_with(
            'Invalid job from uploader with id: 2.'
        )

    @patch.object(TestingService, '_cleanup_job')
    def test_testing_test_image_no_image_id(self, mock_cleanup_job):
        job = Mock()
        job.id = '1'
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        self.message.body = '{"uploader_result": {"id": "1"}}'
        self.testing._test_image(self.message)

        self.testing.log.error.assert_called_once_with(
            'No image id in uploader result file.'
        )
        self.message.ack.assert_called_once_with()
        mock_cleanup_job.assert_called_once_with(job, 2)

    def test_testing_validate_job(self):
        job_config = {
            'account': 'account',
            'distro': 'SLES',
            'id': '1',
            'provider': 'EC2',
            'tests': 'test_stuff',
            'utctime': 'now'
        }

        job = self.testing._validate_job(job_config)

        assert job.account == 'account'
        assert job.distro == 'SLES'
        assert job.id == '1'
        assert job.provider == 'EC2'
        assert job.tests == ['test_stuff']
        assert job.utctime == 'now'

    def test_testing_validate_invalid_job(self):
        job = {
            'account': 'account',
            'id': '1',
            'provider': 'Fake',
            'tests': 'test_stuff',
            'utctime': 'now'
        }

        self.testing._validate_job(job)
        self.testing.log.exception.assert_called_once_with(
            'Provider Fake is not supported for testing.'
        )

    def test_testing_validate_no_provider(self):
        job = {
            'account': 'account',
            'id': '1',
            'tests': 'test_stuff',
            'utctime': 'now'
        }

        self.testing._validate_job(job)
        self.testing.log.exception.assert_called_once_with(
            'No provider: Provider must be in job config.'
        )

    @patch('mash.services.testing.service.EC2TestingJob')
    def test_testing_validate_exception(self, mock_ec2_job):
        job = {
            'account': 'account',
            'id': '1',
            'provider': 'EC2',
            'tests': 'test_stuff',
            'utctime': 'now'
        }

        mock_ec2_job.side_effect = Exception('Broken!')
        self.testing._validate_job(job)
        self.testing.log.exception.assert_called_once_with(
            'Invalid job configuration: Broken!'
        )

    def test_testing_start(self):
        scheduler = Mock()
        self.testing.scheduler = scheduler

        self.channel.consumer_tags = []
        self.testing.channel = self.channel

        self.testing.start()
        scheduler.start.assert_called_once_with()
        self.channel.start_consuming.assert_called_once_with()

    @patch.object(TestingService, '_open_connection')
    def test_testing_start_exception(self, mock_open_connection):
        scheduler = Mock()
        self.testing.scheduler = scheduler
        self.channel.start_consuming.side_effect = [AMQPError('Broken!'), None]
        self.channel.consumer_tags = []
        self.testing.channel = self.channel

        self.testing.start()
        self.testing.log.warning.assert_called_once_with('Broken!')
        mock_open_connection.assert_called_once_with()

    @patch.object(TestingService, 'close_connection')
    def test_testing_stop(self, mock_close_connection):
        scheduler = Mock()
        self.testing.scheduler = scheduler
        self.testing.channel = self.channel

        self.testing.stop()
        scheduler.shutdown.assert_called_once_with()
        self.channel.stop_consuming.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
