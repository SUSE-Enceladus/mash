from unittest.mock import (
    patch, call, MagicMock, Mock
)
from pytz import utc
from datetime import datetime
import dateutil.parser

from apscheduler.events import EVENT_JOB_SUBMITTED

from mash.services.download.s3_job import S3DownloadJob


class TestS3DownloadJob(object):
    @patch('mash.services.download.s3_job.logging')
    # @patch('mash.utils.ec2.get_client')
    def setup_method(self, method, mock_logging):
        # def setup_method(self, method, mock_get_client, mock_logging):
        self.logger = MagicMock()
        # self.downloader = MagicMock()
    #     mock_obs_img_util.return_value = self.downloader

        self.log_callback = MagicMock()
        mock_logging.LoggerAdapter.return_value = self.log_callback

        self.download_result = S3DownloadJob(
            '815',
            'job_file',
            's3://my_s3_bucket',
            'my_image_name-v20231231-lto',
            'x86_64',
            'suse-',
            '.raw.xz',
            'upload',
            self.log_callback,
            notification_email='test@fake.com',
            download_account='download_account',
            download_credentials={
                'access_key_id': 'my_access_key_id',
                'secret_access_key': 'my_secret_access_key'
            },
            download_directory="/tmp/download_directory"
        )

    def test_set_result_handler(self):
        function = Mock()
        self.download_result.set_result_handler(function)
        assert self.download_result.result_callback == function

    @patch.object(S3DownloadJob, '_result_callback')
    def test_call_result_handler(self, mock_result_callback):
        self.download_result.call_result_handler()
        mock_result_callback.assert_called_once_with()

    def test_result_callback(self):
        self.download_result.result_callback = Mock()
        self.download_result.job_status = 'success'
        # self.downloader.build_time = '1703977200'
        self.download_result._result_callback()
        self.download_result.result_callback.assert_called_once_with(
            '815', {
                'download_result': {
                    'id': '815',
                    'image_file': '/tmp/download_directory/815/suse-my_image_name-v20231231-lto-x86_64.raw.xz',  # NOQA
                    'status': 'success',
                    'errors': [],
                    'notification_email': 'test@fake.com',
                    'last_service': 'upload',
                    'build_time': '1703977200'
                }
            }
        )

    def test_result_callback_unknown_build_time(self):
        self.download_result.result_callback = Mock()
        self.download_result.job_status = 'success'
        orig_image_name = self.download_result.image_name
        self.download_result.image_name = 'my_image_name'
        # self.downloader.build_time = 'unknown'
        self.download_result._result_callback()
        self.download_result.result_callback.assert_called_once_with(
            '815', {
                'download_result': {
                    'id': '815',
                    'image_file': '/tmp/download_directory/815/suse-my_image_name-v20231231-lto-x86_64.raw.xz',  # NOQA
                    'status': 'success',
                    'errors': [],
                    'notification_email': 'test@fake.com',
                    'last_service': 'upload',
                    'build_time': 'unknown'
                }
            }
        )
        self.download_result.image_name = orig_image_name

    @patch('mash.services.download.s3_job.BackgroundScheduler')
    @patch.object(S3DownloadJob, '_download_image_file')
    @patch.object(S3DownloadJob, '_job_submit_event')
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

    @patch.object(S3DownloadJob, '_result_callback')
    def test_job_skipped_event(self, mock_result_callback):
        self.download_result._job_skipped_event(Mock())

    # @patch.object(S3DownloadJob, '_result_callback')
    @patch('mash.services.download.s3_job.get_client')
    def test_download_image_file(self, mock_get_client):
        # set up
        client_mock = MagicMock()
        mock_get_client.return_value = client_mock
        self.download_result.result_callback = Mock()

        # test
        self.download_result._download_image_file()

        # assertions
        mock_get_client.assert_called_once_with(
            's3',
            'my_access_key_id',
            'my_secret_access_key',
            None
        )
        client_mock.download_fileobj.assert_called_once_with(
            's3://my_s3_bucket',
            'suse-my_image_name-v20231231-lto-x86_64.raw.xz',
            '/tmp/download_directory/815/suse-my_image_name-v20231231-lto-x86_64.raw.xz'
        )
        log_info_calls = [
            call('Job running'),
            call('Downloaded: suse-my_image_name-v20231231-lto-x86_64.raw.xz from s3://my_s3_bucket S3 bucket'),
            call('Job status: success'),
            call('Job done')
        ]
        self.log_callback.info.assert_has_calls(log_info_calls, any_order=False)

        self.download_result.result_callback.assert_called_once_with(
            '815', {
                'download_result': {
                    'id': '815',
                    'image_file': '/tmp/download_directory/815/suse-my_image_name-v20231231-lto-x86_64.raw.xz',  # NOQA
                    'status': 'success',
                    'errors': [],
                    'notification_email': 'test@fake.com',
                    'last_service': 'upload',
                    'build_time': '1703977200'
                }
            }
        )

    # @patch.object(S3DownloadJob, '_result_callback')
    @patch('mash.services.download.s3_job.get_client')
    def test_download_image_file_exception(self, mock_get_client):
        # set up
        client_mock = MagicMock()
        client_mock.download_fileobj.side_effect = Exception('my_exception')
        mock_get_client.return_value = client_mock
        self.download_result.result_callback = Mock()

        # test
        self.download_result._download_image_file()

        # assertions
        mock_get_client.assert_called_once_with(
            's3',
            'my_access_key_id',
            'my_secret_access_key',
            None
        )
        client_mock.download_fileobj.assert_called_once_with(
            's3://my_s3_bucket',
            'suse-my_image_name-v20231231-lto-x86_64.raw.xz',
            '/tmp/download_directory/815/suse-my_image_name-v20231231-lto-x86_64.raw.xz'
        )
        log_info_calls = [
            call('Job running')
        ]
        self.log_callback.info.assert_has_calls(log_info_calls, any_order=False)
        self.log_callback.error.assert_called_once_with('Exception: my_exception')  # NOQA

        self.download_result.result_callback.assert_called_once_with(
            '815', {
                'download_result': {
                    'id': '815',
                    'image_file': '/tmp/download_directory/815/suse-my_image_name-v20231231-lto-x86_64.raw.xz',  # NOQA
                    'status': 'failed',
                    'errors': ['Exception: my_exception'],
                    'notification_email': 'test@fake.com',
                    'last_service': 'upload',
                    'build_time': '1703977200'
                }
            }
        )

    #     self,
    #     mock_result_callback
    # ):
    #     self.downloader.get_image.return_value = 'new-image.xz'
    #     self.download_result._update_image_status()
    #     mock_result_callback.assert_called_once_with()

    # @patch.object(S3DownloadJob, '_result_callback')
    # def test_update_image_status_raises(
    #     self, mock_result_callback
    # ):
    #     self.downloader.conditions = [{'version': '1.2.3', 'status': False}]
    #     self.downloader.get_image.side_effect = Exception(
    #         'request error'
    #     )
    #     self.download_result._update_image_status()
    #     mock_result_callback.assert_called_once_with()
    #     assert self.log_callback.info.call_args_list == [
    #         call('Job running')
    #     ]
    #     assert self.log_callback.error.call_args_list == [
    #         call('Exception: request error')
    #     ]
    #     assert len(self.download_result.errors) == 2

    # def test_progress_callback(self):
    #     self.download_result.progress_callback(0, 0, 0, done=True)
    #     self.log_callback.info.assert_called_once_with(
    #         'Image download finished.'
    #     )
    #     self.log_callback.info.reset_mock()

    #     self.download_result.progress_callback(4, 25, 400)
    #     self.log_callback.info.assert_called_once_with(
    #         'Image 25% downloaded.'
    #     )
