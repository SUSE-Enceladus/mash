from pytest import raises
from unittest.mock import (
    patch, call, Mock, MagicMock
)
from pytz import utc
from datetime import datetime
from collections import namedtuple
import dateutil.parser
import io

from apscheduler.events import (
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_SUBMITTED
)

from mash.services.obs.build_result import OBSImageBuildResult
from mash.mash_exceptions import (
    MashImageDownloadException,
    MashVersionExpressionException,
    MashWebContentException
)


class TestOBSImageBuildResult(object):
    @patch('mash.services.obs.build_result.WebContent')
    def setup(self, mock_WebContent):
        self.obs_result = OBSImageBuildResult(
            '815', 'job_file', 'obs_project', 'obs_package'
        )

    def test_initial_image_status(self):
        self.obs_result.conditions = [{'status': None}]
        self.obs_result.image_status = self.obs_result._init_status()
        assert self.obs_result.get_image_status() == {
            'job_status': 'prepared',
            'name': 'obs_package',
            'packages_checksum': 'unknown',
            'version': 'unknown',
            'conditions': [{'status': None}],
            'image_source': ['unknown']
        }

    def test_set_log_handler(self):
        function = Mock()
        self.obs_result.set_log_handler(function)
        assert self.obs_result.log_callback == function

    def test_set_result_handler(self):
        function = Mock()
        self.obs_result.set_result_handler(function)
        assert self.obs_result.result_callback == function

    @patch.object(OBSImageBuildResult, '_result_callback')
    def test_call_result_handler(self, mock_result_callback):
        self.obs_result.call_result_handler()
        mock_result_callback.assert_called_once_with()

    def test_log_callback(self):
        self.obs_result.log_callback = Mock()
        self.obs_result.iteration_count = 1
        self.obs_result._log_callback('message')
        self.obs_result.log_callback.assert_called_once_with(
            '815', 'Pass[1]: message'
        )

    def test_result_callback(self):
        self.obs_result.result_callback = Mock()
        self.obs_result.image_status['job_status'] = 'success'
        self.obs_result.image_status['image_source'] = ['image', 'sum']
        self.obs_result._result_callback()
        self.obs_result.result_callback.assert_called_once_with(
            '815', {
                'obs_result': {
                    'id': '815',
                    'image_file': ['image', 'sum'], 'status': 'success'
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

    @patch('mash.services.obs.build_result.BackgroundScheduler')
    @patch.object(OBSImageBuildResult, '_update_image_status')
    @patch.object(OBSImageBuildResult, '_job_skipped_event')
    @patch.object(OBSImageBuildResult, '_job_submit_event')
    def test_start_watchdog_nonstop(
        self, mock_job_submit_event, mock_job_skipped_event,
        mock_update_image_status, mock_BackgroundScheduler
    ):
        scheduler = Mock()
        mock_BackgroundScheduler.return_value = scheduler
        time = 'Tue Oct 10 14:40:42 UTC 2017'
        iso_time = dateutil.parser.parse(time).isoformat()
        run_time = datetime.strptime(iso_time[:19], '%Y-%m-%dT%H:%M:%S')
        self.obs_result.start_watchdog(
            isotime=iso_time, nonstop=True
        )
        mock_BackgroundScheduler.assert_called_once_with(
            timezone=utc
        )
        scheduler.add_job.assert_called_once_with(
            mock_update_image_status, 'interval',
            max_instances=1, seconds=5, start_date=run_time,
            timezone='utc'
        )
        assert scheduler.add_listener.call_args_list == [
            call(mock_job_skipped_event, EVENT_JOB_MAX_INSTANCES),
            call(mock_job_submit_event, EVENT_JOB_SUBMITTED)
        ]
        scheduler.start.assert_called_once_with()

    def test_stop_watchdog_no_exception(self):
        self.obs_result.job = Mock()
        self.obs_result.stop_watchdog()
        self.obs_result.job.remove.assert_called_once_with()

    def test_stop_watchdog_just_pass_with_exception(self):
        self.obs_result.job = Mock()
        self.obs_result.job.remove.side_effect = Exception
        self.obs_result.stop_watchdog()

    @patch('mash.services.obs.build_result.mkpath')
    def test_get_image(self, mock_mkpath):
        self.obs_result.image_metadata_name = \
            'Azure-Factory.x86_64-1.0.5-Build5.28.packages'
        self.obs_result.remote.fetch_files.return_value = \
            ['/var/lib/mash/images/'
             'Azure-Factory.x86_64-1.0.5-Build5.28.vhdfixed.xz']
        assert self.obs_result.get_image() == [
            '/var/lib/mash/images/'
            'Azure-Factory.x86_64-1.0.5-Build5.28.vhdfixed.xz'
        ]
        mock_mkpath.assert_called_once_with('/var/lib/mash/images/')
        self.obs_result.image_metadata_name = \
            'Azure-Factory.x86_64-1.0.5-Build42.42.packages'
        with raises(MashImageDownloadException):
            self.obs_result.get_image()

    def test_get_build_number(self):
        name = 'Azure-Factory.x86_64-1.0.5-Build42.42.packages'
        assert self.obs_result._get_build_number(name) == ['1.0.5', '42.42']

    @patch.object(OBSImageBuildResult, '_log_callback')
    def test_job_submit_event(self, mock_log_callback):
        self.obs_result.job_nonstop = True
        self.obs_result._job_submit_event(Mock())
        mock_log_callback.assert_called_once_with('Nonstop job submitted')
        mock_log_callback.reset_mock()
        self.obs_result.job_nonstop = False
        self.obs_result._job_submit_event(Mock())
        mock_log_callback.assert_called_once_with('Oneshot Job submitted')

    @patch.object(OBSImageBuildResult, '_result_callback')
    def test_job_skipped_event(self, mock_result_callback):
        self.obs_result._job_skipped_event(Mock())

    @patch('mash.services.obs.build_result.threading.Thread')
    @patch.object(OBSImageBuildResult, '_watch_obs_result')
    def test_wait_for_new_image(self, mock_watch_obs_result, mock_Thread):
        osc_result_thread = Mock()
        mock_Thread.return_value = osc_result_thread
        self.obs_result._wait_for_new_image()
        mock_Thread.assert_called_once_with(target=mock_watch_obs_result)
        osc_result_thread.start.assert_called_once_with()
        osc_result_thread.join.assert_called_once_with()

    @patch('mash.services.obs.build_result.NamedTemporaryFile')
    @patch('time.sleep')
    def test_watch_obs_result(self, mock_sleep, mock_NamedTemporaryFile):
        tempfile = Mock()
        tempfile.name = 'tmpfile'
        mock_NamedTemporaryFile.return_value = tempfile

        # simulate fetch_file success, exception, success
        fetch_file_returns = [True, False, True]

        # simulate first checksum not equal second attempt
        handle_read_returns = ['a', 'b']

        def fetch_file(*args):
            if not fetch_file_returns.pop():
                raise Exception

        def handle_read():
            return handle_read_returns.pop()

        self.obs_result.remote.fetch_file.side_effect = fetch_file

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.read.side_effect = handle_read
            self.obs_result._watch_obs_result()
            assert mock_sleep.call_args_list == [
                call(60), call(60), call(60)
            ]
            assert mock_open.call_args_list == [
                call(tempfile.name), call(tempfile.name)
            ]

    def test_image_conditions_complied(self):
        self.obs_result.image_status['version'] = 'unknown'
        assert self.obs_result._image_conditions_complied() is False
        self.obs_result.image_status['version'] = '1.2.3'
        assert self.obs_result._image_conditions_complied() is True
        self.obs_result.image_status['conditions'] = [{'status': False}]
        assert self.obs_result._image_conditions_complied() is False

    @patch('mash.services.obs.build_result.time')
    @patch.object(OBSImageBuildResult, '_log_callback')
    @patch.object(OBSImageBuildResult, '_result_callback')
    @patch.object(OBSImageBuildResult, '_lookup_image_packages_metadata')
    @patch.object(OBSImageBuildResult, '_lookup_package')
    @patch.object(OBSImageBuildResult, '_image_conditions_complied')
    @patch.object(OBSImageBuildResult, '_wait_for_new_image')
    @patch.object(OBSImageBuildResult, 'get_image')
    def test_update_image_status(
        self, mock_get_image, mock_wait_for_new_image,
        mock_image_conditions_complied, mock_lookup_package,
        mock_lookup_image_packages_metadata,
        mock_result_callback, mock_log_callback, mock_time
    ):
        self.obs_result.image_status['version'] = '1.2.3'
        self.obs_result.image_status['conditions'] = [
            {'image': '1.2.3'},
            {'name': 'package'}
        ]
        package_type = namedtuple(
            'package_type', [
                'version', 'release', 'arch', 'checksum'
            ]
        )
        mock_get_image.return_value = []
        mock_lookup_image_packages_metadata.return_value = {
            'package': package_type(
                version='1.2.3',
                release='0.1',
                arch='x86_64',
                checksum='0815'
            )
        }
        mock_lookup_package.return_value = True
        mock_image_conditions_complied.return_value = True
        self.obs_result._update_image_status()
        mock_result_callback.assert_called_once_with()
        assert self.obs_result.image_status == {
            'job_status': 'success',
            'name': 'obs_package',
            'packages_checksum': '895dffb744492711f7b6524d3e696422',
            'version': '1.2.3',
            'conditions': [
                {'status': True, 'image': '1.2.3'},
                {'status': True, 'name': 'package'}
            ], 'image_source': []
        }

        self.obs_result.job_nonstop = True
        self.obs_result._update_image_status()
        mock_wait_for_new_image.assert_called_once_with()

        self.obs_result.image_status['version'] = '7.7.7'
        mock_lookup_package.side_effect = [False, True]
        mock_image_conditions_complied.side_effect = [False, True]
        self.obs_result._update_image_status()

    @patch.object(OBSImageBuildResult, '_log_callback')
    @patch.object(OBSImageBuildResult, '_lookup_image_packages_metadata')
    @patch.object(OBSImageBuildResult, '_result_callback')
    def test_update_image_status_raises(
        self, mock_result_callback, mock_lookup_image_packages_metadata,
        mock_log_callback
    ):
        mock_lookup_image_packages_metadata.side_effect = \
            MashWebContentException('request error')
        self.obs_result._update_image_status()
        mock_result_callback.assert_called_once_with()
        assert mock_log_callback.call_args_list == [
            call('Job running'),
            call('Error: MashWebContentException: request error')
        ]

    @patch('mash.services.obs.build_result.NamedTemporaryFile')
    def test_lookup_image_packages_metadata(self, mock_NamedTemporaryFile):
        tempfile = Mock()
        tempfile.name = '../data/image.packages'
        mock_NamedTemporaryFile.return_value = tempfile
        self.obs_result.remote.fetch_file.return_value = \
            'Azure-Factory.x86_64-1.0.5-Build5.28.packages'
        data = self.obs_result._lookup_image_packages_metadata()
        self.obs_result.remote.fetch_file.assert_called_once_with(
            'obs_package.x86_64', '.packages', '../data/image.packages'
        )
        assert data['file-magic'].checksum == '8e776ae58aac4e50edcf190e493e5c20'
        assert self.obs_result.image_status['version'] == '1.0.5'
        self.obs_result.remote.fetch_file.return_value = 'foo.packages'
        self.obs_result._lookup_image_packages_metadata()
        assert self.obs_result.image_status['version'] == 'unknown'

    @patch('mash.services.obs.build_result.NamedTemporaryFile')
    def test_lookup_package(
        self, mock_NamedTemporaryFile
    ):
        tempfile = Mock()
        tempfile.name = '../data/image.packages'
        mock_NamedTemporaryFile.return_value = tempfile
        packages = self.obs_result._lookup_image_packages_metadata()
        assert self.obs_result._lookup_package(
            packages, {'name': 'foo'}
        ) is False
        assert self.obs_result._lookup_package(
            packages, {
                'name': 'file-magic',
                'version': '5.32'
            }
        ) is True
        assert self.obs_result._lookup_package(
            packages, {
                'name': 'file-magic',
                'version': '5.32',
                'condition': '=='
            }
        ) is True
        assert self.obs_result._lookup_package(
            packages,
            {
                'name': 'file-magic',
                'version': '5.32',
                'condition': '>'
            }
        ) is False
        assert self.obs_result._lookup_package(
            packages,
            {
                'name': 'file-magic',
                'version': '5.32',
                'condition': '<'
            }
        ) is False
        assert self.obs_result._lookup_package(
            packages,
            {
                'name': 'file-magic',
                'version': '5.32',
                'build_id': '1.2',
                'condition': '<='
            }
        ) is True
        assert self.obs_result._lookup_package(
            packages,
            {
                'name': 'file-magic',
                'version': '5.32',
                'build_id': '1.1',
                'condition': '<='
            }
        ) is False
        with raises(MashVersionExpressionException):
            self.obs_result._lookup_package(
                packages,
                {
                    'name': 'file-magic',
                    'version': '5.32',
                    'condition': '='
                }
            )
