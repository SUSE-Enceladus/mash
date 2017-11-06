from pytest import raises
from mock import patch
from mock import call
from mock import Mock
from pytz import utc
from datetime import datetime
from collections import namedtuple
import dateutil.parser

from .test_helper import (
    patch_open,
    context_manager
)

from apscheduler.events import (
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_SUBMITTED
)

from mash.services.obs.build_result import OBSImageBuildResult
from mash.mash_exceptions import (
    MashOBSLookupException,
    MashImageDownloadException,
    MashVersionExpressionException,
    MashOBSResultException,
    MashJobRetireException,
    MashException
)


class TestOBSImageBuildResult(object):
    @patch('distutils.dir_util.mkpath')
    @patch('osc.conf')
    def setup(self, mock_osc_conf, mock_mkpath):
        self.obs_result = OBSImageBuildResult(
            '815', 'job_file', 'obs_project', 'obs_package'
        )
        mock_mkpath.assert_called_once_with('/var/tmp/mash/obs_jobs_done/')
        mock_osc_conf.get_config.assert_called_once_with()

    def test_initial_image_status(self):
        self.obs_result.conditions = [{'status': None}]
        self.obs_result.image_status = self.obs_result._init_status()
        assert self.obs_result.get_image_status() == {
            'job_status': 'prepared',
            'errors': [],
            'name': 'obs_package',
            'packages_checksum': 'unknown',
            'version': 'unknown',
            'conditions': [{'status': None}],
            'image_source': 'unknown'
        }

    @patch('osc.conf')
    def test_init_error_reading_osc_config(self, mock_osc_conf):
        mock_osc_conf.get_config.side_effect = Exception('osc_error')
        obs_result = OBSImageBuildResult(
            '815', 'job_file', 'obs_project', 'obs_package'
        )
        assert obs_result.image_status['errors'] == [
            'Reading osc config failed: osc_error'
        ]

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
            max_instances=1, seconds=30, start_date=run_time,
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

    @patch('mash.services.obs.build_result.get_binary_file')
    @patch('mash.services.obs.build_result.get_binarylist')
    @patch('mash.services.obs.build_result.mkpath')
    def test_get_image(
        self, mock_mkpath, mock_get_binary_list, mock_get_binary_file
    ):
        binary_list_type = namedtuple(
            'binary_list_type', ['name', 'mtime']
        )
        mock_get_binary_list.return_value = [
            binary_list_type(name='image.raw.xz', mtime='time'),
            binary_list_type(name='image.raw.xz.sha256', mtime='time')
        ]
        assert self.obs_result.get_image() == [
            '/tmp/image.raw.xz', '/tmp/image.raw.xz.sha256'
        ]
        mock_mkpath.assert_called_once_with('/tmp')
        assert mock_get_binary_file.call_args_list == [
            call(
                'https://api.opensuse.org', 'obs_project', 'images',
                'x86_64', 'image.raw.xz', package='obs_package',
                target_filename='/tmp/image.raw.xz', target_mtime='time'
            ),
            call(
                'https://api.opensuse.org', 'obs_project', 'images',
                'x86_64', 'image.raw.xz.sha256', package='obs_package',
                target_filename='/tmp/image.raw.xz.sha256', target_mtime='time'
            )
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

    @patch('mash.services.obs.build_result.get_binarylist')
    def test_get_image_obs_error(self, mock_get_binary_list):
        mock_get_binary_list.side_effect = Exception
        with raises(MashOBSLookupException):
            self.obs_result.get_image()

    @patch('mash.services.obs.build_result.get_binary_file')
    @patch('mash.services.obs.build_result.get_binarylist')
    def test_get_image_download_error(
        self, mock_get_binary_list, mock_get_binary_file
    ):
        binary_list_type = namedtuple(
            'binary_list_type', ['name', 'mtime']
        )
        mock_get_binary_list.return_value = [
            binary_list_type(name='image.raw.xz', mtime='time'),
            binary_list_type(name='image.raw.xz.sha256', mtime='time')
        ]
        mock_get_binary_file.side_effect = Exception
        with raises(MashImageDownloadException):
            self.obs_result.get_image()

    def test_job_submit_event(self):
        self.obs_result.log = Mock()
        self.obs_result._job_submit_event(Mock())
        assert self.obs_result.image_status['job_status'] == 'oneshot'

    def test_job_skipped_event(self):
        self.obs_result.log = Mock()
        self.obs_result._job_skipped_event(Mock())

    @patch('mash.services.obs.build_result.meta_exists')
    @patch('mash.services.obs.build_result.edit_meta')
    def test_lock(self, mock_edit_meta, mock_meta_exists):
        mock_meta_exists.return_value = \
            '<package name="x" project="y"><title/><description/></package>'
        self.obs_result._lock()
        mock_meta_exists.assert_called_once_with(
            apiurl='https://api.opensuse.org',
            create_new=False, metatype='pkg',
            path_args=('obs_project', 'obs_package')
        )
        mock_edit_meta.assert_called_once_with(
            data='<package name="x" project="y"><title /><description />' +
            '<lock><enable /></lock></package>',
            metatype='pkg', msg='lock',
            path_args=('obs_project', 'obs_package')
        )

    @patch('mash.services.obs.build_result.meta_exists')
    def test_lock_error(self, mock_meta_exists):
        self.obs_result.log = Mock()
        mock_meta_exists.side_effect = Exception('error')
        self.obs_result._lock()
        assert self.obs_result.image_status['errors'] == [
            'Lock failed for obs_project/obs_package: Exception: error'
        ]

    @patch('mash.services.obs.build_result.unlock_package')
    def test_unlock(self, mock_unlock_package):
        self.obs_result.lock_set_by_this_instance = True
        self.obs_result._unlock()
        mock_unlock_package.assert_called_once_with(
            'https://api.opensuse.org', 'obs_project', 'obs_package', 'unlock'
        )

    @patch('mash.services.obs.build_result.unlock_package')
    def test_unlock_error(self, mock_unlock_package):
        self.obs_result.lock_set_by_this_instance = True
        self.obs_result.log = Mock()
        mock_unlock_package.side_effect = Exception('error')
        self.obs_result._unlock()
        assert self.obs_result.image_status['errors'] == [
            'Unlock failed for obs_project/obs_package: Exception: error'
        ]

    @patch('mash.services.obs.build_result.get_results')
    def test_wait_for_new_image(self, mock_get_results):
        self.obs_result._wait_for_new_image()
        mock_get_results.assert_called_once_with(
            apiurl='https://api.opensuse.org',
            arch=['x86_64'], package='obs_package', project='obs_project',
            repository=['images'], wait=True
        )

    @patch('mash.services.obs.build_result.get_results')
    def test_wait_for_new_image_error(self, mock_get_results):
        mock_get_results.side_effect = Exception
        with raises(MashOBSResultException):
            self.obs_result._wait_for_new_image()

    @patch('mash.services.obs.build_result.pickle.dump')
    @patch('os.remove')
    @patch_open
    def test_retire_job(self, mock_open, mock_os_remove, mock_pickle_dump):
        context = context_manager()
        mock_open.return_value = context.context_manager_mock
        self.obs_result._retire_job()
        mock_os_remove.assert_called_once_with('job_file')
        mock_open.assert_called_once_with(
            '/var/tmp/mash/obs_jobs_done//815.pickle', 'wb'
        )

    @patch('os.remove')
    def test_retire_job_job_file_removal_error(self, mock_os_remove):
        mock_os_remove.side_effect = Exception
        with raises(MashJobRetireException):
            self.obs_result._retire_job()

    def test_image_conditions_complied(self):
        self.obs_result.image_status['version'] = 'unknown'
        assert self.obs_result._image_conditions_complied() is False
        self.obs_result.image_status['version'] = '1.2.3'
        assert self.obs_result._image_conditions_complied() is True
        self.obs_result.image_status['conditions'] = [{'status': False}]
        assert self.obs_result._image_conditions_complied() is False

    @patch.object(OBSImageBuildResult, '_lock')
    @patch.object(OBSImageBuildResult, '_unlock')
    @patch.object(OBSImageBuildResult, '_lookup_image_packages_metadata')
    @patch.object(OBSImageBuildResult, '_lookup_package')
    @patch.object(OBSImageBuildResult, '_image_conditions_complied')
    @patch.object(OBSImageBuildResult, '_wait_for_new_image')
    @patch.object(OBSImageBuildResult, '_retire_job')
    @patch.object(OBSImageBuildResult, 'get_image')
    def test_update_image_status(
        self, mock_get_image, mock_retire_job, mock_wait_for_new_image,
        mock_image_conditions_complied, mock_lookup_package,
        mock_lookup_image_packages_metadata, mock_unlock, mock_lock
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
        mock_retire_job.assert_called_once_with()
        mock_unlock.assert_called_once_with()
        assert self.obs_result.image_status == {
            'job_status': 'success',
            'errors': [],
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
    def test_update_image_status_lock_failed(self, mock_unlock, mock_lock):
        mock_lock.return_value = False
        self.obs_result._update_image_status()
        assert self.obs_result.image_status['job_status'] == 'prepared'
        mock_lock.assert_called_once_with()
        mock_unlock.assert_called_once_with()

    @patch.object(OBSImageBuildResult, '_lock')
    @patch.object(OBSImageBuildResult, '_unlock')
    def test_update_image_status_error(self, mock_unlock, mock_lock):
        self.obs_result.log = Mock()
        mock_lock.side_effect = MashException('error')
        self.obs_result._update_image_status()
        mock_unlock.assert_called_once_with()
        assert self.obs_result.image_status['errors'] == [
            'MashException: error'
        ]

    @patch('mash.services.obs.build_result.get_binarylist')
    @patch('mash.services.obs.build_result.get_binary_file')
    @patch('mash.services.obs.build_result.NamedTemporaryFile')
    def test_lookup_image_packages_metadata(
        self, mock_NamedTemporaryFile,
        mock_get_binary_file, mock_get_binary_list
    ):
        tempfile = Mock()
        tempfile.name = '../data/image.packages'
        mock_NamedTemporaryFile.return_value = tempfile
        binary_list_type = namedtuple(
            'binary_list_type', ['name', 'mtime']
        )
        mock_get_binary_list.return_value = [
            binary_list_type(
                name='Azure-Factory.x86_64-1.0.5-Build5.28.vhdfixed.xz.sha256',
                mtime='time'
            ),
            binary_list_type(
                name='image.packages',
                mtime='time'
            )
        ]
        data = self.obs_result._lookup_image_packages_metadata()
        mock_get_binary_file.assert_called_once_with(
            'https://api.opensuse.org', 'obs_project',
            'images', 'x86_64',
            'image.packages', package='obs_package',
            target_filename='../data/image.packages',
            target_mtime='time'
        )
        assert data['file-magic'].checksum == '8e776ae58aac4e50edcf190e493e5c20'
        assert self.obs_result.image_status['version'] == '1.0.5'
        mock_get_binary_list.return_value = [
            binary_list_type(name='foo.xz.sha256', mtime='time')
        ]
        self.obs_result._lookup_image_packages_metadata()
        assert self.obs_result.image_status['version'] == 'unknown'

    @patch('mash.services.obs.build_result.get_binarylist')
    @patch('mash.services.obs.build_result.NamedTemporaryFile')
    def test_lookup_package(
        self, mock_NamedTemporaryFile, mock_get_binary_list
    ):
        tempfile = Mock()
        tempfile.name = '../data/image.packages'
        mock_NamedTemporaryFile.return_value = tempfile
        mock_get_binary_list.return_value = []
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
