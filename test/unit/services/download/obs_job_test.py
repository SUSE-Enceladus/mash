from unittest.mock import (
    patch, call, MagicMock, Mock
)
from pytest import raises
from pytz import utc
from datetime import datetime
import dateutil.parser

from apscheduler.events import EVENT_JOB_SUBMITTED

from mash.services.download.obs_job import OBSDownloadJob
from mash.services.base_config import BaseConfig
from mash.mash_exceptions import MashImageDownloadException


class TestOBSDownloadJob(object):
    @patch('mash.services.download.obs_job.logging')
    @patch('mash.services.download.obs_job.OBSImageUtil')
    def setup_method(self, method, mock_obs_img_util, mock_logging):
        self.logger = MagicMock()
        self.downloader = MagicMock()
        mock_obs_img_util.return_value = self.downloader

        self.log_callback = MagicMock()
        mock_logging.LoggerAdapter.return_value = self.log_callback

        job_config = {
            'id': '815',
            'job_file': 'job_file',
            'download_url': 'obs_project',
            'image': 'obs_package',
            'last_service': 'publish',
            'notification_email': 'test@fake.com',
            'profile': 'Proxy',
            'disallow_licenses': ['MIT'],
            'disallow_packages': ['fake']
        }
        config = BaseConfig('./test/data/mash_config.yaml')

        self.download_result = OBSDownloadJob(job_config, config)
        self.download_result.set_log_handler(self.log_callback)

    def test_set_result_handler(self):
        function = Mock()
        self.download_result.set_result_handler(function)
        assert self.download_result.result_callback == function

    @patch.object(OBSDownloadJob, '_result_callback')
    def test_call_result_handler(self, mock_result_callback):
        self.download_result.call_result_handler()
        mock_result_callback.assert_called_once_with()

    def test_result_callback(self):
        self.download_result.result_callback = Mock()
        self.download_result.job_status = 'success'
        self.downloader.image_source = 'image'
        self.downloader.build_time = '1601061355'
        self.download_result._result_callback()
        self.download_result.result_callback.assert_called_once_with(
            '815', {
                'download_result': {
                    'id': '815',
                    'image_file': 'image',
                    'status': 'success',
                    'errors': [],
                    'notification_email': 'test@fake.com',
                    'last_service': 'publish',
                    'build_time': '1601061355'
                }
            }
        )

    @patch('mash.services.download.obs_job.BackgroundScheduler')
    @patch.object(OBSDownloadJob, '_update_image_status')
    @patch.object(OBSDownloadJob, '_job_submit_event')
    def test_start_watchdog_single_shot(
        self, mock_job_submit_event, mock_update_image_status,
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
            mock_update_image_status, 'date', run_date=run_time,
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

    @patch.object(OBSDownloadJob, '_result_callback')
    def test_job_skipped_event(self, mock_result_callback):
        self.download_result._job_skipped_event(Mock())

    @patch.object(OBSDownloadJob, '_result_callback')
    def test_update_image_status(
        self,
        mock_result_callback
    ):
        self.downloader.get_image.return_value = 'new-image.xz'
        self.download_result._update_image_status()
        mock_result_callback.assert_called_once_with()

    @patch.object(OBSDownloadJob, '_result_callback')
    def test_update_image_status_raises(
        self, mock_result_callback
    ):
        self.downloader.conditions = [{'version': '1.2.3', 'status': False}]
        self.downloader.get_image.side_effect = Exception(
            'request error'
        )
        self.download_result._update_image_status()
        mock_result_callback.assert_called_once_with()
        assert self.log_callback.info.call_args_list == [
            call('Job running')
        ]
        assert self.log_callback.error.call_args_list == [
            call('Exception: request error')
        ]
        assert len(self.download_result.errors) == 2

    def test_progress_callback(self):
        self.download_result.progress_callback(0, 0, 0, done=True)
        self.log_callback.info.assert_called_once_with(
            'Image download finished.'
        )
        self.log_callback.info.reset_mock()

        self.download_result.progress_callback(4, 25, 400)
        self.log_callback.info.assert_called_once_with(
            'Image 25% downloaded.'
        )

    def test_required_params(self):
        config = BaseConfig('./test/data/mash_config.yaml')
        test_params = [
            (
                {
                    'job_file': 'job_file',
                    'download_url': 'obs_project',
                    'image': 'obs_package',
                    'last_service': 'publish'
                },
                'id field is required in Mash job doc.'
            ),
            (
                {
                    'id': '815',
                    'download_url': 'obs_project',
                    'image': 'obs_package',
                    'last_service': 'publish'
                },
                'job_file field is required in Mash job doc.'
            ),
            (
                {
                    'id': '815',
                    'job_file': 'job_file',
                    'image': 'obs_package',
                    'last_service': 'publish'
                },
                'download_url field is required in Mash job doc.'
            ),
            (
                {
                    'id': '815',
                    'job_file': 'job_file',
                    'download_url': 'obs_project',
                    'last_service': 'publish'
                },
                'image field is required in Mash job doc.'
            ),
            (
                {
                    'id': '815',
                    'job_file': 'job_file',
                    'download_url': 'obs_project',
                    'image': 'obs_package'
                },
                'last_service field is required in Mash job doc.'
            )
        ]

        for (job_config, expected_output) in test_params:
            with raises(MashImageDownloadException) as e:
                OBSDownloadJob(job_config, config)
            assert e.value.args[0] == expected_output
