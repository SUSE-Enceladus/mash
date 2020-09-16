from unittest.mock import (
    patch, call, MagicMock, Mock
)
from pytz import utc
from datetime import datetime
import dateutil.parser

from apscheduler.events import EVENT_JOB_SUBMITTED

from mash.services.obs.build_result import OBSImageBuildResult


class TestOBSImageBuildResult(object):
    @patch('mash.services.obs.build_result.logging')
    @patch('mash.services.obs.build_result.OBSImageUtil')
    def setup(self, mock_obs_img_util, mock_logging):
        self.logger = MagicMock()
        self.downloader = MagicMock()
        mock_obs_img_util.return_value = self.downloader

        self.log_callback = MagicMock()
        mock_logging.LoggerAdapter.return_value = self.log_callback

        self.obs_result = OBSImageBuildResult(
            '815', 'job_file', 'obs_project', 'obs_package', 'publish',
            self.logger,
            notification_email='test@fake.com',
            profile='Proxy', disallow_licenses=["MIT"],
            disallow_packages=["fake"]
        )

    def test_set_result_handler(self):
        function = Mock()
        self.obs_result.set_result_handler(function)
        assert self.obs_result.result_callback == function

    @patch.object(OBSImageBuildResult, '_result_callback')
    def test_call_result_handler(self, mock_result_callback):
        self.obs_result.call_result_handler()
        mock_result_callback.assert_called_once_with()

    def test_result_callback(self):
        self.obs_result.result_callback = Mock()
        self.obs_result.job_status = 'success'
        self.downloader.image_status = {'image_source': 'image'}
        self.obs_result._result_callback()
        self.obs_result.result_callback.assert_called_once_with(
            '815', {
                'obs_result': {
                    'id': '815',
                    'image_file': 'image',
                    'status': 'success',
                    'errors': [],
                    'notification_email': 'test@fake.com',
                    'last_service': 'publish'
                }
            }
        )

    @patch('mash.services.obs.build_result.BackgroundScheduler')
    @patch.object(OBSImageBuildResult, '_update_image_status')
    @patch.object(OBSImageBuildResult, '_job_submit_event')
    def test_start_watchdog_single_shot(
        self, mock_job_submit_event, mock_update_image_status,
        mock_BackgroundScheduler
    ):
        scheduler = Mock()
        mock_BackgroundScheduler.return_value = scheduler
        time = 'Tue Oct 10 14:40:42 UTC 2017'
        iso_time = dateutil.parser.parse(time).isoformat()
        run_time = datetime.strptime(iso_time[:19], '%Y-%m-%dT%H:%M:%S')
        self.obs_result.start_watchdog(isotime=iso_time)
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
        self.obs_result.job = Mock()
        self.obs_result.stop_watchdog()
        self.obs_result.job.remove.assert_called_once_with()

    def test_stop_watchdog_just_pass_with_exception(self):
        self.obs_result.job = Mock()
        self.obs_result.job.remove.side_effect = Exception
        self.obs_result.stop_watchdog()

    def test_job_submit_event(self):
        self.obs_result._job_submit_event(Mock())
        self.log_callback.info.assert_called_once_with('Oneshot Job submitted')

    @patch.object(OBSImageBuildResult, '_result_callback')
    def test_job_skipped_event(self, mock_result_callback):
        self.obs_result._job_skipped_event(Mock())

    @patch('mash.services.obs.build_result.threading.Thread')
    @patch.object(OBSImageBuildResult, '_update_image_status')
    def test_wait_for_new_image(self, mock_image_status, mock_Thread):
        osc_result_thread = Mock()
        mock_Thread.return_value = osc_result_thread
        self.obs_result._wait_for_new_image()
        mock_Thread.assert_called_once_with(
            target=self.downloader.wait_for_new_image
        )
        osc_result_thread.start.assert_called_once_with()
        osc_result_thread.join.assert_called_once_with()
        mock_image_status.assert_called_once_with()

    @patch.object(OBSImageBuildResult, '_result_callback')
    def test_update_image_status(
        self,
        mock_result_callback
    ):
        self.downloader.get_image.return_value = 'new-image.xz'
        self.obs_result._update_image_status()
        mock_result_callback.assert_called_once_with()

    @patch.object(OBSImageBuildResult, '_result_callback')
    def test_update_image_status_raises(
        self, mock_result_callback
    ):
        self.downloader.get_image.side_effect = Exception(
            'request error'
        )
        self.obs_result._update_image_status()
        mock_result_callback.assert_called_once_with()
        assert self.log_callback.info.call_args_list == [
            call('Job running')
        ]
        assert self.log_callback.error.call_args_list == [
            call('Exception: request error')
        ]

    def test_progress_callback(self):
        self.obs_result.progress_callback(0, 0, 0, done=True)
        self.log_callback.info.assert_called_once_with(
            'Image download finished.'
        )
        self.log_callback.info.reset_mock()

        self.obs_result.progress_callback(4, 25, 400)
        self.log_callback.info.assert_called_once_with(
            'Image 25% downloaded.'
        )
