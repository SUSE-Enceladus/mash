# Copyright (c) 2019 SUSE LLC.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#

import os
import re
import time
import threading
import logging
import hashlib

from distutils.dir_util import mkpath
from datetime import datetime
from pkg_resources import parse_version
from pytz import utc
from tempfile import NamedTemporaryFile
from collections import namedtuple
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import (
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_SUBMITTED
)

# project
from mash.utils.web_content import WebContent
from mash.services.obs.defaults import Defaults
from mash.log.filter import SchedulerLoggingFilter
from mash.services.status_levels import FAILED, SUCCESS
from mash.mash_exceptions import (
    MashImageDownloadException,
    MashVersionExpressionException
)


class OBSImageBuildResult(object):
    """
    Implements Open BuildService image result watchdog

    Attributes

    * :attr:`job_id`
      job id number

    * :attr:`job_file`
      job file containing the job description

    * :attr:`download_url`
      Buildservice URL

    * :attr:`image_name`
      Image name as specified in the KIWI XML description of the
      Buildservice project and package

    * :attr:`last_service`
      The last service for the job.

    * :attr:`conditions`
      Criteria for the image build which is a list of hashes like
      the following example demonstrates:

      conditions=[
          # a package condition with version and release spec
          {
           'package_name': 'kernel-default',
           'version': '4.13.1',
           'build_id': '1.1'
          },
          # a image version condition
          {'image': '1.42.1'}
      ]

    * :attr:`arch`
      Buildservice package architecture, defaults to: x86_64

    * :attr:`download_directory`
      Download directory name, defaults to: /tmp

    * :attr:`notification_email`
      Email to send job notifications.

    * :attr:`notification_type`
      The frequency of notification emails.
    """
    def __init__(
        self, job_id, job_file, download_url, image_name, last_service,
        conditions=None, arch='x86_64',
        download_directory=Defaults.get_download_dir(),
        notification_email=None, notification_type='single'
    ):
        self.arch = arch
        self.job_id = job_id
        self.job_file = job_file
        self.download_directory = os.path.join(download_directory, job_id)
        self.download_url = download_url
        self.image_name = image_name
        self.last_service = last_service
        self.image_metadata_name = None
        self.conditions = conditions
        self.scheduler = None
        self.job = None
        self.job_deleted = False
        self.job_nonstop = False
        self.log_callback = None
        self.result_callback = None
        self.notification_callback = None
        self.iteration_count = 0
        self.notification_email = notification_email
        self.notification_type = notification_type

        self.remote = WebContent(self.download_url)

        self.image_status = self._init_status()

    def start_watchdog(
        self, interval_sec=5, nonstop=False, isotime=None
    ):
        """
        Start a background job which triggers the update
        of the image build data and image fetched from the obs project.

        The job is started at a given data/time which must
        be the result of a isoformat() call. If no data/time is
        specified the job runs immediately. If nonstop is true
        the job runs continuously in the given interval but allows
        for one active instance only. The running job causes any
        subsequent jobs to be skipped until the state of the build
        results changes

        :param bool nonstop: run continuously
        :param string isotime: data and time by isoformat()
        :param int interval_sec: interval for nonstop jobs
        """
        self.job_nonstop = nonstop
        time = None
        if isotime:
            time = datetime.strptime(isotime[:19], '%Y-%m-%dT%H:%M:%S')
        self.scheduler = BackgroundScheduler(timezone=utc)
        if nonstop:
            self.job = self.scheduler.add_job(
                self._update_image_status, 'interval',
                max_instances=1, seconds=interval_sec,
                start_date=time, timezone='utc'
            )
            self.scheduler.add_listener(
                self._job_skipped_event, EVENT_JOB_MAX_INSTANCES
            )
            logging.getLogger("apscheduler.scheduler").addFilter(
                SchedulerLoggingFilter()
            )
        else:
            self.job = self.scheduler.add_job(
                self._update_image_status, 'date',
                run_date=time, timezone='utc'
            )
        self.scheduler.add_listener(
            self._job_submit_event, EVENT_JOB_SUBMITTED
        )
        self.scheduler.start()

    def stop_watchdog(self):
        """
        Remove active job from scheduler

        Current image status is retained
        """
        try:
            self.job.remove()
            self.job_deleted = True
        except Exception:
            pass

    def set_log_handler(self, function):
        self.log_callback = function

    def set_result_handler(self, function):
        self.result_callback = function

    def set_notification_handler(self, function):
        self.notification_callback = function

    def call_result_handler(self):
        self._result_callback()

    def get_image_status(self):
        """
        Return status of the image and condition states
        """
        return self.image_status

    def get_image(self):
        """
        Download image and shasum to given file
        """
        mkpath(self.download_directory)
        file_prefix = self.image_metadata_name.replace('.packages', '')
        image_files = self.remote.fetch_files(
            ''.join([self.image_name, '.']),
            [
                ''.join([file_prefix, '.xz.sha256']),
                ''.join([file_prefix, '.xz']),
                ''.join([file_prefix, '.tar.gz.sha256']),
                ''.join([file_prefix, '.tar.gz'])
            ],
            self.download_directory
        )

        if not image_files:
            raise MashImageDownloadException(
                'No images found that match the image file name {0}.'.format(
                    file_prefix
                )
            )

        return image_files

    def _get_build_number(self, name):
        build = re.search(
            r'{0}-(\d+\.\d+\.\d+)-Build([0-9]+\.[0-9]+)'.format(self.arch),
            name
        ) or re.search(
            r'{0}-(\d+\.\d+\.\d+)-Beta([0-9]+)'.format(self.arch),
            name
        )
        if build:
            return [build.group(1), build.group(2)]

    def _log_callback(self, message):
        if self.log_callback:
            self.log_callback(
                self.job_id, 'Pass[{0}]: {1}'.format(
                    self.iteration_count, message
                )
            )

    def _result_callback(self):
        job_status = self.image_status['job_status']
        if self.result_callback:
            self.result_callback(
                self.job_id, {
                    'obs_result': {
                        'id': self.job_id,
                        'image_file': self.image_status['image_source'],
                        'status': job_status
                    }
                }
            )

    def _notification_callback(
        self, status, error=None
    ):
        utctime = 'always' if self.job_nonstop else 'now'

        if self.notification_callback:
            self.notification_callback(
                self.job_id, self.notification_email, self.notification_type,
                status, utctime, self.last_service, self.iteration_count,
                error
            )

    def _init_status(self):
        image_status = {
            'name': self.image_name,
            'job_status': 'prepared',
            'image_source': ['unknown'],
            'packages_checksum': 'unknown',
            'version': 'unknown',
            'conditions': []
        }
        if self.conditions:
            for condition in self.conditions:
                condition['status'] = None
            image_status['conditions'] = self.conditions
        return image_status

    def _job_submit_event(self, event):
        if self.job_nonstop:
            self._log_callback('Nonstop job submitted')
        else:
            self._log_callback('Oneshot Job submitted')

    def _job_skipped_event(self, event):
        # Job is still active while the next _update_image_status
        # event was scheduled. In this case we just skip the event
        # and keep the active job waiting for an obs change
        pass

    def _wait_for_new_image(self):
        osc_result_thread = threading.Thread(target=self._watch_obs_result)
        osc_result_thread.start()
        osc_result_thread.join()

    def _watch_obs_result(self, timeout=60):
        checksum_file = NamedTemporaryFile()
        checksum_current = None
        checksum_latest = None
        while not self.job_deleted:
            time.sleep(timeout)
            self._log_callback('Rechecking checksum for {0}'.format(
                self.image_name)
            )
            try:
                self.remote.fetch_file(
                    ''.join([self.image_name, '.', self.arch]),
                    '.sha256',
                    checksum_file.name
                )
                with open(checksum_file.name) as checksum:
                    checksum_latest = checksum.read()
                if checksum_current and checksum_current != checksum_latest:
                    return
                checksum_current = checksum_latest
            except Exception:
                continue

    def _image_conditions_complied(self):
        for condition in self.image_status['conditions']:
            if condition['status'] is not True:
                return False
        return True

    def _log_error(self, message):
        self.image_status['job_status'] = 'failed'
        self._log_callback('Error: {0}'.format(message))

    def _update_image_status(self):
        try:
            self.iteration_count += 1
            retries = 10
            conditions_fail_logged = False
            self._log_callback('Job running')

            while True:
                packages = self._lookup_image_packages_metadata()
                for condition in self.image_status['conditions']:
                    if 'image' in condition:
                        if self.image_status['version'] == condition['image']:
                            condition['status'] = True
                        else:
                            condition['status'] = False
                    elif 'package_name' in condition:
                        if self._lookup_package(
                            packages, condition
                        ):
                            condition['status'] = True
                        else:
                            condition['status'] = False

                if self._image_conditions_complied():
                    packages_digest = hashlib.md5()
                    packages_digest.update(format(packages).encode())
                    packages_checksum = packages_digest.hexdigest()
                    if packages_checksum != \
                            self.image_status['packages_checksum']:
                        self._log_callback('Downloading image...')
                        self.image_status['packages_checksum'] = 'unknown'

                        try:
                            self.image_status['image_source'] = \
                                self.get_image()
                        except MashImageDownloadException:
                            if retries > 0:
                                retries -= 1
                                self._log_callback(
                                    'Image files not found, retrying...'
                                )
                                continue
                            else:
                                raise

                        self._log_callback(
                            'Downloaded: {0}'.format(
                                self.image_status['image_source']
                            )
                        )
                    self.image_status['packages_checksum'] = packages_checksum
                    self.image_status['job_status'] = 'success'
                    break
                else:
                    if not conditions_fail_logged:
                        self._log_callback('Waiting for conditions to be met.')
                        conditions_fail_logged = True

                    time.sleep(300)

            self._log_callback(
                'Job status: {0}'.format(self.image_status['job_status'])
            )
            self._result_callback()

            if self.job_nonstop:
                self._log_callback('Waiting for image update')
                self._wait_for_new_image()
            else:
                self._notification_callback(SUCCESS)
                self._log_callback('Job done')
        except Exception as issue:
            msg = '{0}: {1}'.format(type(issue).__name__, issue)

            self._log_error(msg)
            self._notification_callback(FAILED, msg)

            if not self.job_nonstop:
                self._result_callback()

    def _lookup_image_packages_metadata(self):
        packages_file = NamedTemporaryFile()
        self.image_metadata_name = self.remote.fetch_file(
            ''.join([self.image_name, '.', self.arch]),
            '.packages',
            packages_file.name
        )

        if not self.image_metadata_name:
            raise MashImageDownloadException(
                'No image metadata found for image name: {0}'.format(
                    self.image_name
                )
            )

        try:
            # Extract image version information from .packages file name
            self.image_status['version'] = \
                self._get_build_number(self.image_metadata_name)[0]
        except Exception:
            # Naming conventions for image names in obs violated
            self.image_status['version'] = 'unknown'
            raise MashImageDownloadException(
                'No image version found. '
                'Unexpected image name format: {0}'.format(
                    self.image_metadata_name
                )
            )

        package_type = namedtuple(
            'package_type', [
                'version', 'release', 'arch', 'checksum'
            ]
        )

        result_packages = {}
        with open(packages_file.name) as packages:
            for package in packages.readlines():
                package_digest = hashlib.md5()
                package_digest.update(package.encode())
                package_info = package.split('|')
                package_name = package_info[0]
                package_result = package_type(
                    version=package_info[2],
                    release=package_info[3],
                    arch=package_info[4],
                    checksum=package_digest.hexdigest()
                )
                result_packages[package_name] = package_result
        return result_packages

    def _version_compare(self, current, expected, condition):
        if condition == '>=':
            return parse_version(current) >= parse_version(expected)
        elif condition == '<=':
            return parse_version(current) <= parse_version(expected)
        elif condition == '==':
            return parse_version(current) == parse_version(expected)
        elif condition == '>':
            return parse_version(current) > parse_version(expected)
        elif condition == '<':
            return parse_version(current) < parse_version(expected)
        else:
            raise MashVersionExpressionException(
                'Invalid version compare expression: "{0}"'.format(condition)
            )

    def _lookup_package(self, packages, condition):
        package_name = condition['package_name']

        if package_name not in packages:
            return False

        condition_eval = condition.get('condition', '>=')
        package_data = packages[package_name]

        if 'version' in condition:
            # we want to lookup a specific version
            match = self._version_compare(
                package_data.version,
                condition['version'],
                condition_eval
            )

            if not match:
                return False

        if 'build_id' in condition:
            # we want to lookup a specific build number
            match = self._version_compare(
                package_data.release,
                condition['build_id'],
                condition_eval
            )

            if not match:
                return False

        return True
