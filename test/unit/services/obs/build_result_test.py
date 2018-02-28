from pytest import raises
from unittest.mock import patch
from unittest.mock import call
from unittest.mock import Mock
from pytz import utc
from datetime import datetime
from collections import namedtuple
import dateutil.parser
import subprocess

from apscheduler.events import (
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_SUBMITTED
)

from mash.services.obs.build_result import OBSImageBuildResult
from mash.mash_exceptions import (
    MashOBSLookupException,
    MashImageDownloadException,
    MashVersionExpressionException,
    MashException
)


class TestOBSImageBuildResult(object):
    def setup(self):
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

    @patch.object(OBSImageBuildResult, '_get_binary_list')
    @patch('mash.services.obs.build_result.mkpath')
    @patch('mash.services.obs.build_result.Command.run')
    def test_get_image(
        self, mock_run, mock_mkpath, mock_get_binary_list
    ):
        mock_get_binary_list.return_value = [
            'image.raw.xz',
            'image.raw.xz.sha256'
        ]
        assert self.obs_result.get_image() == [
            '/tmp/image.raw.xz', '/tmp/image.raw.xz.sha256'
        ]
        mock_mkpath.assert_called_once_with('/tmp')
        assert mock_run.call_args_list == [
            call([
                'osc', '-A', 'https://api.opensuse.org',
                'getbinaries', '-d', '/tmp', '-q', 'obs_project',
                'obs_package', 'images', 'x86_64', 'image.raw.xz'
            ]),
            call([
                'osc', '-A', 'https://api.opensuse.org',
                'getbinaries', '-d', '/tmp', '-q', 'obs_project',
                'obs_package', 'images', 'x86_64', 'image.raw.xz.sha256'
            ])
        ]

    def test_match_image_file(self):
        name = 'image.iso'
        assert self.obs_result._match_image_file(name) is True
        name = 'image.xz'
        assert self.obs_result._match_image_file(name) is True
        name = 'image.xz.sha256'
        assert self.obs_result._match_image_file(name) is True
        name = 'foo'
        assert self.obs_result._match_image_file(name) is False

    @patch('mash.services.obs.build_result.Command.run')
    def test_get_image_obs_error(self, mock_run):
        mock_run.side_effect = Exception
        with raises(MashOBSLookupException):
            self.obs_result.get_image()

    @patch('mash.services.obs.build_result.Command.run')
    @patch.object(OBSImageBuildResult, '_get_binary_list')
    def test_get_image_download_error(
        self, mock_get_binary_list, mock_run
    ):
        mock_run.side_effect = Exception
        mock_get_binary_list.return_value = [
            'image.raw.xz',
            'image.raw.xz.sha256'
        ]
        with raises(MashImageDownloadException):
            self.obs_result.get_image()

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

    @patch.object(OBSImageBuildResult, '_setup_lock')
    def test_lock(self, mock_setup_lock):
        self.obs_result._lock()
        mock_setup_lock.assert_called_once_with(command='lock')

    @patch.object(OBSImageBuildResult, '_setup_lock')
    def test_unlock(self, mock_setup_lock):
        self.obs_result._unlock()
        mock_setup_lock.assert_called_once_with(command='unlock')

    @patch('mash.services.obs.build_result.Command.run')
    @patch.object(OBSImageBuildResult, '_log_error')
    @patch.object(OBSImageBuildResult, '_log_callback')
    def test_setup_lock(self, mock_log_callback, mock_log_error, mock_run):
        assert self.obs_result._setup_lock('lock') is True
        mock_log_callback.assert_called_once_with(
            'lock: obs_project/obs_package'
        )
        mock_run.assert_called_once_with(
            [
                'osc', '-A', 'https://api.opensuse.org',
                'lock', '-m', 'mash_lock', 'obs_project', 'obs_package'
            ]
        )
        mock_run.side_effect = Exception('error')
        assert self.obs_result._setup_lock('lock') is False
        mock_log_error.assert_called_once_with(
            'lock failed for obs_project/obs_package: Exception: error'
        )

    @patch('mash.services.obs.build_result.threading.Thread')
    @patch.object(OBSImageBuildResult, '_watch_obs_result')
    def test_wait_for_new_image(self, mock_watch_obs_result, mock_Thread):
        osc_result_thread = Mock()
        osc_result_thread.is_alive.return_value = True
        mock_Thread.return_value = osc_result_thread
        self.obs_result.osc_results_process = Mock()
        self.obs_result._wait_for_new_image(10)
        mock_Thread.assert_called_once_with(target=mock_watch_obs_result)
        osc_result_thread.start.assert_called_once_with()
        assert osc_result_thread.join.call_args_list == [
            call(10), call()
        ]
        self.obs_result.osc_results_process.terminate.assert_called_once_with()

    @patch('mash.services.obs.build_result.subprocess.Popen')
    def test_watch_obs_result(self, mock_Popen):
        self.obs_result._watch_obs_result()
        mock_Popen.assert_called_once_with(
            [
                'osc', '-A', 'https://api.opensuse.org', 'results',
                '--arch', 'x86_64', '--repo', 'images', '--watch',
                'obs_project', 'obs_package'
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.obs_result.osc_results_process.communicate.assert_called_once_with()

    def test_image_conditions_complied(self):
        self.obs_result.image_status['version'] = 'unknown'
        assert self.obs_result._image_conditions_complied() is False
        self.obs_result.image_status['version'] = '1.2.3'
        assert self.obs_result._image_conditions_complied() is True
        self.obs_result.image_status['conditions'] = [{'status': False}]
        assert self.obs_result._image_conditions_complied() is False

    @patch.object(OBSImageBuildResult, '_lock')
    @patch.object(OBSImageBuildResult, '_unlock')
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
        mock_result_callback, mock_log_callback, mock_unlock, mock_lock
    ):
        self.obs_result.image_status['version'] = '1.2.3'
        self.obs_result.image_status['conditions'] = [
            {'image': '1.2.3'},
            {'package': 'package'}
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
        mock_lock.assert_called_once_with()
        mock_unlock.assert_called_once_with()
        mock_result_callback.assert_called_once_with()
        assert self.obs_result.image_status == {
            'job_status': 'success',
            'name': 'obs_package',
            'packages_checksum': '895dffb744492711f7b6524d3e696422',
            'version': '1.2.3',
            'conditions': [
                {'status': True, 'image': '1.2.3'},
                {'status': True, 'package': 'package'}
            ], 'image_source': []
        }

        self.obs_result.job_nonstop = True
        self.obs_result._update_image_status()
        mock_wait_for_new_image.assert_called_once_with()

        self.obs_result.image_status['version'] = '7.7.7'
        mock_lookup_package.return_value = False
        mock_image_conditions_complied.return_value = False
        self.obs_result._update_image_status()
        assert self.obs_result.image_status['job_status'] == 'failed'

    @patch.object(OBSImageBuildResult, '_lock')
    @patch.object(OBSImageBuildResult, '_unlock')
    @patch.object(OBSImageBuildResult, '_log_callback')
    def test_update_image_status_lock_failed(
        self, mock_log_callback, mock_unlock, mock_lock
    ):
        mock_lock.return_value = False
        self.obs_result._update_image_status()
        assert self.obs_result.image_status['job_status'] == 'failed'
        mock_lock.assert_called_once_with()

    @patch.object(OBSImageBuildResult, '_lock')
    @patch.object(OBSImageBuildResult, '_unlock')
    @patch.object(OBSImageBuildResult, '_log_callback')
    def test_update_image_status_error(
        self, mock_log_callback, mock_unlock, mock_lock
    ):
        self.obs_result.log = Mock()
        mock_lock.side_effect = MashException('error')
        self.obs_result._update_image_status()
        mock_unlock.assert_called_once_with()

    @patch.object(OBSImageBuildResult, '_get_binary_list')
    @patch('mash.services.obs.build_result.Command.run')
    @patch('mash.services.obs.build_result.NamedTemporaryFile')
    @patch('os.rename')
    def test_lookup_image_packages_metadata(
        self, mock_rename, mock_NamedTemporaryFile, mock_run,
        mock_get_binary_list
    ):
        tempfile = Mock()
        tempfile.name = '../data/image.packages'
        mock_NamedTemporaryFile.return_value = tempfile
        mock_get_binary_list.return_value = [
            'Azure-Factory.x86_64-1.0.5-Build5.28.vhdfixed.xz.sha256',
            'image.packages'
        ]
        data = self.obs_result._lookup_image_packages_metadata()
        mock_run.assert_called_once_with(
            [
                'osc', '-A', 'https://api.opensuse.org', 'getbinaries',
                '-d', '/tmp', '-q', 'obs_project', 'obs_package',
                'images', 'x86_64', 'image.packages'
            ]
        )
        mock_rename.assert_called_once_with(
            '/tmp/image.packages', '../data/image.packages'
        )
        assert data['file-magic'].checksum == '8e776ae58aac4e50edcf190e493e5c20'
        assert self.obs_result.image_status['version'] == '1.0.5'
        mock_get_binary_list.return_value = [
            'foo.xz.sha256'
        ]
        self.obs_result._lookup_image_packages_metadata()
        assert self.obs_result.image_status['version'] == 'unknown'

    @patch('mash.services.obs.build_result.Command.run')
    @patch('mash.services.obs.build_result.NamedTemporaryFile')
    def test_lookup_package(
        self, mock_NamedTemporaryFile, mock_run
    ):
        tempfile = Mock()
        tempfile.name = '../data/image.packages'
        mock_NamedTemporaryFile.return_value = tempfile
        packages = self.obs_result._lookup_image_packages_metadata()
        assert self.obs_result._lookup_package(
            packages, ['foo']
        ) is False
        assert self.obs_result._lookup_package(
            packages, ['file-magic']
        ) is True
        assert self.obs_result._lookup_package(
            packages, ['file-magic', '>=5.32']
        ) is True
        assert self.obs_result._lookup_package(
            packages, ['file-magic', '>=5.32', '>=1.2']
        ) is True
        assert self.obs_result._lookup_package(
            packages, ['file-magic', '<5.32', '<1.2']
        ) is False
        with raises(MashVersionExpressionException):
            self.obs_result._lookup_package(
                packages, ['file-magic', '=5.32']
            )
