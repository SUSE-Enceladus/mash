from unittest.mock import (
    patch, MagicMock, Mock, call
)
from pytz import utc
from datetime import datetime
import dateutil.parser

from apscheduler.events import EVENT_JOB_SUBMITTED

from mash.services.download.s3bucket_job import S3BucketDownloadJob


class TestS3BucketDownloadJob(object):
    @patch('mash.services.download.s3bucket_job.logging')
    def setup_method(self, method, mock_logging):
        self.logger = MagicMock()

        self.log_callback = MagicMock()
        mock_logging.LoggerAdapter.return_value = self.log_callback

        self.download_result = S3BucketDownloadJob(
            '815',
            'job_file',
            's3://my_s3_bucket',
            'my_image_name-v20231231-lto',
            'x86_64',
            'upload',
            self.log_callback,
            notification_email='test@fake.com',
            download_account='download_account',
            download_credentials={
                'access_key_id': 'my_access_key_id',
                'secret_access_key': 'my_secret_access_key'
            },
            download_directory='/tmp/download_directory'
        )

    def test_set_result_handler(self):
        function = Mock()
        self.download_result.set_result_handler(function)
        assert self.download_result.result_callback == function

    @patch.object(S3BucketDownloadJob, '_result_callback')
    def test_call_result_handler(self, mock_result_callback):
        self.download_result.call_result_handler()
        mock_result_callback.assert_called_once_with()

    def test_result_callback(self):
        self.download_result.result_callback = Mock()
        self.download_result.job_status = 'success'
        self.download_result._result_callback()
        self.download_result.result_callback.assert_called_once_with(
            '815', {
                'download_result': {
                    'id': '815',
                    'image_file': '',
                    'status': 'success',
                    'errors': [],
                    'notification_email': 'test@fake.com',
                    'last_service': 'upload',
                    'build_time': 'unknown'
                }
            }
        )

    @patch('mash.services.download.s3bucket_job.BackgroundScheduler')
    @patch.object(S3BucketDownloadJob, '_download_image_file')
    @patch.object(S3BucketDownloadJob, '_job_submit_event')
    def test_start_watchdog_single_shot(
        self, mock_job_submit_event, mock_download_image_file,
        mock_BackgroundScheduler
    ):
        scheduler = Mock()
        mock_BackgroundScheduler.return_value = scheduler
        time = 'Tue Oct 10 14:40:42 UTC 2017'
        iso_time = dateutil.parser.parse(time).isoformat()
        run_time = datetime.strptime(iso_time[:19], '%Y-%m-%dT%H:%M:%S')
        self.download_result.start_watchdog(isotime=iso_time)
        mock_BackgroundScheduler.assert_called_once_with(
            timezone=utc
        )
        scheduler.add_job.assert_called_once_with(
            mock_download_image_file, 'date', run_date=run_time,
            timezone='utc'
        )
        scheduler.add_listener.assert_called_once_with(
            mock_job_submit_event, EVENT_JOB_SUBMITTED
        )
        scheduler.start.assert_called_once_with()

    def test_stop_watchdog_no_exception(self):
        self.download_result.job = Mock()
        self.download_result.stop_watchdog()
        self.download_result.job.remove.assert_called_once_with()

    def test_stop_watchdog_just_pass_with_exception(self):
        self.download_result.job = Mock()
        self.download_result.job.remove.side_effect = Exception
        self.download_result.stop_watchdog()

    def test_job_submit_event(self):
        self.download_result._job_submit_event(Mock())
        self.log_callback.info.assert_called_once_with('Oneshot Job submitted')

    @patch.object(S3BucketDownloadJob, '_result_callback')
    def test_job_skipped_event(self, mock_result_callback):
        self.download_result._job_skipped_event(Mock())

    def test_get_bucket_name_and_key_from_download_url(self):
        previous_download_url = self.download_result.download_url
        tests = [
            (
                's3://my_download_bucket/path/to/object',
                'my_download_bucket',
                'path/to/object',

            ),
            (
                'my_download_bucket/path/to/object',
                'my_download_bucket',
                'path/to/object'
            ),
            (
                'my_download_bucket',
                'my_download_bucket',
                ''
            )
        ]
        for (
            download_url,
            expected_bucket_name,
            expected_dir_part_of_obj_key
        ) in tests:
            self.download_result.download_url = download_url
            bucket_name, dir_part_of_obj_key = \
                self.download_result._get_bucket_name_and_key_from_download_url()  # NOQA
            assert bucket_name == expected_bucket_name
            assert dir_part_of_obj_key == expected_dir_part_of_obj_key

        self.download_result.download_url = previous_download_url

    @patch('mash.services.download.s3bucket_job.os.makedirs')
    @patch('mash.services.download.s3bucket_job.get_session')
    def test_download_image_file2(
        self,
        mock_get_session,
        mock_os_makedirs,
    ):
        client_mock = MagicMock()
        client_mock.download_file.return_value = True
        session_mock = MagicMock()
        session_mock.client.return_value = client_mock
        mock_get_session.return_value = session_mock
        self.log_callback.reset_mock()

        result_callback_mock = MagicMock()

        previous_download_url = self.download_result.download_url

        self.download_result.download_url = \
            's3://my_bucket_name/my_dir'
        self.download_result.image_name = 'myfile.tar.gz'
        self.download_result.result_callback = result_callback_mock

        self.download_result._download_image_file()

        # assertions
        mock_get_session.assert_called_once_with(
            'my_access_key_id',
            'my_secret_access_key',
            None
        )
        session_mock.client.assert_called_once_with(
            service_name='s3'
        )
        client_mock.download_file.assert_called_once_with(
            'my_bucket_name',
            'my_dir/myfile.tar.gz',
            '/tmp/download_directory/815/myfile.tar.gz'
        )
        mock_os_makedirs.assert_called_once_with(
            '/tmp/download_directory/815'
        )
        self.log_callback.info.assert_has_calls(
            [
                call('Job running'),
                call('Downloaded: my_dir/myfile.tar.gz from my_bucket_name S3 bucket to /tmp/download_directory/815/myfile.tar.gz'),  # NOQA
                call('Job status: success'),
                call('Job done')
            ]
        )
        self.download_result.download_url = previous_download_url
        result_callback_mock.assert_called_once_with(
            '815', {
                'download_result': {
                    'id': '815',
                    'image_file': '/tmp/download_directory/815/myfile.tar.gz',  # NOQA
                    'status': 'success',
                    'errors': [],
                    'notification_email': 'test@fake.com',
                    'last_service': 'upload',
                    'build_time': 'unknown'
                }
            }
        )

    @patch('mash.services.download.s3bucket_job.os.makedirs')
    @patch('mash.services.download.s3bucket_job.get_session')
    def test_download_image_file_exception(
        self,
        mock_get_session,
        mock_os_makedirs
    ):
        client_mock = MagicMock()
        client_mock.download_file.side_effect = Exception('my_exception')
        session_mock = MagicMock()
        session_mock.client.return_value = client_mock
        mock_get_session.return_value = session_mock
        self.log_callback.reset_mock()

        previous_download_url = self.download_result.download_url

        self.download_result.download_url = \
            's3://my_bucket_name/AWS/'
        self.download_result.image_name = 'myfile.tar.gz'

        result_callback_mock = MagicMock()
        self.download_result.result_callback = result_callback_mock

        self.download_result._download_image_file()

        # assertions
        mock_get_session.assert_called_once_with(
            'my_access_key_id',
            'my_secret_access_key',
            None
        )
        session_mock.client.assert_called_once_with(
            service_name='s3'
        )
        client_mock.download_file.assert_called_once_with(
            'my_bucket_name',
            'AWS/myfile.tar.gz',
            '/tmp/download_directory/815/myfile.tar.gz'
        )
        mock_os_makedirs.assert_called_once_with(
            '/tmp/download_directory/815'
        )
        self.log_callback.info.assert_has_calls(
            [
                call('Job running'),
            ]
        )
        self.log_callback.error.assert_called_once_with(
            'Exception: my_exception'
        )
        result_callback_mock.assert_called_once_with(
            '815', {
                'download_result': {
                    'id': '815',
                    'image_file': '',
                    'status': 'failed',
                    'errors': ['Exception: my_exception'],
                    'notification_email': 'test@fake.com',
                    'last_service': 'upload',
                    'build_time': 'unknown'
                }
            }
        )
        self.download_result.download_url = previous_download_url
