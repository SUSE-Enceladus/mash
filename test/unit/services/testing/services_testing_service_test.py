from unittest.mock import Mock, patch

from mash.services.base_service import BaseService
from mash.services.testing.config import TestingConfig
from mash.services.testing.service import TestingService


class TestIPATestingService(object):

    @patch.object(BaseService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None

        self.config = Mock()
        self.channel = Mock()
        self.channel.basic_ack.return_value = None

        self.testing = TestingService()
        self.testing.jobs = {}
        self.testing.log = Mock()

        self.status_message = '{"testing_result": ' \
            '{"job_id": "1", "status": 0, "image": "image123"}}'

    @patch.object(TestingConfig, '__init__')
    @patch.object(TestingService, 'bind_service_queue')
    @patch.object(TestingService, '_handle_jobs')
    @patch.object(TestingService, 'consume_queue')
    def test_testing_post_init(
        self, mock_consume_queue, mock_handle_jobs,
        mock_bind_service_queue, mock_testing_config
    ):
        mock_testing_config.return_value = None
        self.testing.post_init()
        mock_consume_queue.assert_called_once_with(
            mock_handle_jobs, mock_bind_service_queue.return_value
        )
        mock_bind_service_queue.assert_called_once_with()

    @patch.object(TestingService, '_test_image')
    @patch.object(TestingService, '_get_job_metadata')
    @patch.object(TestingService, 'consume_queue')
    @patch.object(TestingService, 'bind_listener_queue')
    def test_testing_add_job(
        self, mock_bind_listener_queue, mock_consume_queue, mock_get_metadata,
        mock_test_image
    ):
        mock_get_metadata.return_value = {'job_id': '1'}
        job = Mock()
        job.job_id = '1'

        self.testing._add_job(job)

        self.testing.log.info.assert_called_once_with(
            'Job queued.',
            extra={'job_id': '1'}
        )

        mock_consume_queue.assert_called_once_with(
            mock_test_image, mock_bind_listener_queue.return_value
        )
        mock_bind_listener_queue.assert_called_once_with('1')

    @patch.object(TestingService, '_get_job_metadata')
    def test_testing_add_job_exists(
        self, mock_get_metadata
    ):
        mock_get_metadata.return_value = {'job_id': '1'}
        job = Mock()
        job.job_id = '1'

        self.testing.jobs['1'] = Mock()
        self.testing._add_job(job)

        self.testing.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': '1'}
        )

    @patch.object(TestingService, '_get_job_metadata')
    @patch.object(TestingService, 'delete_listener_queue')
    def test_testing_delete_job(
        self, mock_delete_listener_queue, mock_get_metadata
    ):
        mock_get_metadata.return_value = {'job_id': '1'}
        job = Mock()
        job.job_id = '1'

        self.testing.jobs['1'] = job
        self.testing._delete_job('1')

        self.testing.log.info.assert_called_once_with(
            'Deleting job.',
            extra={'job_id': '1'}
        )

        mock_delete_listener_queue.assert_called_once_with('1')

    @patch.object(TestingService, '_get_job_metadata')
    def test_testing_delete_invalid_job(
        self, mock_get_metadata
    ):
        mock_get_metadata.return_value = {'job_id': '1'}

        self.testing._delete_job('1')

        self.testing.log.warning.assert_called_once_with(
            'Job deletion failed, job is not queued.',
            extra={'job_id': '1'}
        )

    def test_testing_get_metadata(self):
        job = Mock()
        job.job_id = '1'

        data = self.testing._get_job_metadata(job)
        assert data == {'job_id': '1'}

    @patch.object(TestingService, '_delete_job')
    def test_testing_handle_jobs_delete(self, mock_delete_job):
        self.testing._handle_jobs(
            self.channel, Mock(), Mock(), b'{"testing_job_delete": "1"}'
        )

        mock_delete_job.assert_called_once_with('1')

    @patch.object(TestingService, '_validate_job')
    def test_testing_handle_jobs_add(self, mock_validate_job):
        self.testing._handle_jobs(
            self.channel,
            Mock(),
            Mock(),
            b'{"testing_job_add": {"job_id": "1"}}'
        )

        mock_validate_job.assert_called_once_with({'job_id': '1'})

    def test_testing_handle_jobs_invalid(self):
        self.testing._handle_jobs(
            self.channel,
            Mock(),
            Mock(),
            b'{"testing_job_update": {"job_id": "1"}}'
        )

        self.testing.log.error.assert_called_once_with(
            'Invalid testing job: Desc must contain either'
            'testing_job_add or testing_job_delete key.'
        )

    def test_testing_handle_jobs_format(self):
        self.testing._handle_jobs(
            self.channel,
            Mock(),
            Mock(),
            b'Invalid format.'
        )

        self.testing.log.error.assert_called_once_with(
            'Invalid job config file: Expecting value:'
            ' line 1 column 1 (char 0).'
        )

    def test_testing_get_status_message(self):
        job = Mock()
        job.job_id = '1'
        job.status = 0
        job.image = 'image123'

        data = self.testing._get_status_message(job)
        assert data == self.status_message

    @patch.object(TestingService, '_delete_job')
    @patch.object(TestingService, '_publish_message')
    @patch.object(TestingService, '_get_status_message')
    @patch.object(TestingService, '_get_job_metadata')
    def test_testing_process_test_result(
        self, mock_get_metadata, mock_get_status_message,
        mock_publish_message, mock_delete_job
    ):
        mock_get_metadata.return_value = {'job_id': '1'}
        mock_get_status_message.return_value = self.status_message

        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.utctime = 'now'
        job.status = 0

        self.testing.jobs['1'] = job
        self.testing._process_test_result(event)

        mock_delete_job.assert_called_once_with('1')
        self.testing.log.info.assert_called_once_with(
            'Testing successful.',
            extra={'job_id': '1'}
        )
        mock_get_status_message.assert_called_once_with(job)
        mock_publish_message.assert_called_once_with(
            '1',
            self.status_message
        )

    @patch.object(TestingService, '_publish_message')
    @patch.object(TestingService, '_get_status_message')
    @patch.object(TestingService, '_get_job_metadata')
    def test_testing_process_test_result_exception(
        self, mock_get_metadata, mock_get_status_message,
        mock_publish_message
    ):
        mock_get_metadata.return_value = {'job_id': '1'}
        mock_get_status_message.return_value = self.status_message

        event = Mock()
        event.job_id = '1'
        event.exception = 'Broken!'

        job = Mock()
        job.utctime = 'always'
        job.status = 0

        self.testing.jobs['1'] = job
        self.testing._process_test_result(event)

        self.testing.log.error.assert_called_once_with(
            'Exception testing image: Broken!',
            extra={'job_id': '1'}
        )
        mock_get_status_message.assert_called_once_with(job)
        mock_publish_message.assert_called_once_with(
            '1',
            self.status_message
        )

    @patch.object(TestingService, '_publish_message')
    @patch.object(TestingService, '_get_status_message')
    @patch.object(TestingService, '_get_job_metadata')
    def test_testing_process_test_result_fail(
        self, mock_get_metadata, mock_get_status_message,
        mock_publish_message
    ):
        mock_get_metadata.return_value = {'job_id': '1'}
        mock_get_status_message.return_value = self.status_message

        event = Mock()
        event.job_id = '1'
        event.exception = None

        job = Mock()
        job.utctime = 'always'
        job.status = 1

        self.testing.jobs['1'] = job
        self.testing._process_test_result(event)

        self.testing.log.error.assert_called_once_with(
            'Error occurred testing image with IPA.',
            extra={'job_id': '1'}
        )
        mock_get_status_message.assert_called_once_with(job)
        mock_publish_message.assert_called_once_with(
            '1',
            self.status_message
        )

    @patch.object(TestingService, '_publish')
    def test_testing_publish_message(self, mock_publish):
        self.testing._publish_message('1', self.status_message)

        mock_publish.assert_called_once_with(
            'publisher',
            'listener_1',
            self.status_message
        )

    @patch('mash.services.testing.service.test_image')
    def test_testing_run_test(self, mock_test_image):
        mock_test_image.return_value = (0, {'results': '...'})

        job = Mock()
        job.provider = 'EC2'
        job.account = 'test_account'
        job.distro = 'SLES'
        job.image = 'image123'
        job.tests = 'test1,test2'
        self.testing.jobs['1'] = job

        self.testing._run_test('1')

        mock_test_image.assert_called_once_with(
            'EC2',
            account='test_account',
            distro='SLES',
            log_level=30,
            image_id='image123',
            tests='test1,test2'
        )

    @patch.object(TestingService, '_run_test')
    def test_testing_test_image(self, mock_run_test):
        job = Mock()
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        scheduler = Mock()
        self.testing.scheduler = scheduler

        self.testing._test_image(
            self.channel,
            Mock(),
            Mock(),
            '{"uploader_result": {"job_id": "1", "image": "image123"}}'
        )

        assert self.testing.jobs['1'].image == 'image123'
        scheduler.add_job.assert_called_once_with(
            mock_run_test,
            args=('1',),
            id='1'
        )

    @patch.object(TestingService, '_run_test')
    def test_testing_test_image_invalid(self, mock_run_test):
        job = Mock()
        job.utctime = 'always'
        self.testing.jobs['1'] = job

        scheduler = Mock()
        self.testing.scheduler = scheduler

        self.testing._test_image(
            self.channel,
            Mock(),
            Mock(),
            '{"uploader_result": {"job_id": "1"}}'
        )

        self.testing.log.error.assert_called_once_with(
            'Invalid uploader result file: '
            '{"uploader_result": {"job_id": "1"}}'
        )

    @patch.object(TestingService, '_add_job')
    def test_testing_validate_job(self, mock_add_job):
        job = {
            'account': 'account',
            'job_id': '1',
            'provider': 'EC2',
            'tests': 'test_stuff',
            'utctime': 'now'
        }
        self.testing._validate_job(job)

        mock_add_job.call_count == 1

    def test_testing_validate_invalid_job(self):
        job = {
            'account': 'account',
            'job_id': '1',
            'provider': 'Fake',
            'tests': 'test_stuff',
            'utctime': 'now'
        }

        self.testing._validate_job(job)
        self.testing.log.exception.assert_called_once_with(
            'Invalid job configuration: Provider: Fake not supported.'
        )

    def test_testing_start(self):
        scheduler = Mock()
        self.testing.scheduler = scheduler
        self.testing.channel = self.channel

        self.testing.start()
        scheduler.start.assert_called_once_with()
        self.channel.start_consuming.assert_called_once_with()

    @patch.object(TestingService, 'close_connection')
    def test_testing_stop(self, mock_close_connection):
        scheduler = Mock()
        self.testing.scheduler = scheduler
        self.testing.channel = self.channel

        self.testing.stop()
        scheduler.shutdown.assert_called_once_with()
        self.channel.stop_consuming.assert_called_once_with()
        mock_close_connection.assert_called_once_with()
