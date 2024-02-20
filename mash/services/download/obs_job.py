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
import logging

from datetime import datetime
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_SUBMITTED

from obs_img_utils.api import OBSImageUtil

# project
from mash.log.filter import BaseServiceFilter
from mash.utils.mash_utils import setup_rabbitmq_log_handler


class OBSDownloadJob(object):
    """
    Implements Open BuildService image download job

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
           'release': '1.1'
          },
          # a image version condition
          {"version": "8.13.21"}
      ]

    * :attr:`arch`
      Buildservice package architecture, defaults to: x86_64

    * :attr:`download_directory`
      Download directory name, defaults to: /tmp

    * :attr:`notification_email`
      Email to send job notifications.

    * :attr:`profile`
      The multibuild profile name for the image.

    * :attr:`conditions_wait_time`
      Time to wait for conditions in image to be met.

    * :attr:`disallow_licenses`
      A list of licenses to disallow in the image.

    * :attr:`disallow_packages`
      A list of packages to disallow in the image.
    """
    def __init__(self, job_config, config):
        self.job_config = job_config
        self.config = config
        self.job_id = job_config['id']
        self.job_file = job_config['job_file']
        self.download_url = job_config['download_url']
        self.image_name = job_config['image_name']
        self.last_service = job_config['last_service']
        self.download_directory = os.path.join(
            config.get_download_directory(),
            self.job_id
        )

        logging.basicConfig()
        logger = logging.getLogger('DownloadService')
        logger.setLevel(logging.DEBUG)
        rabbit_handler = setup_rabbitmq_log_handler(
            config.get_amqp_host(),
            config.get_amqp_user(),
            config.get_amqp_pass()
        )
        logger.addHandler(rabbit_handler)
        logger.addFilter(BaseServiceFilter)
        self.log_callback = logging.LoggerAdapter(
            logger,
            {'job_id': self.job_id}
        )

        if 'conditions' in job_config:
            self.conditions = job_config['conditions']
        else:
            self.conditions = None

        if 'cloud_architecture' in job_config:
            self.arch = job_config['cloud_architecture']
        else:
            self.arch = 'x86_64'

        if 'profile' in job_config:
            self.profile = job_config['profile']
        else:
            self.profile = None

        if 'notification_email' in job_config:
            self.notification_email = job_config['notification_email']
        else:
            self.notification_email = None

        if 'conditions_wait_time' in job_config:
            self.conditions_wait_time = job_config['conditions_wait_time']
        else:
            self.conditions_wait_time = 900

        if 'disallow_licenses' in job_config:
            self.disallow_licenses = job_config['disallow_licenses']
        else:
            self.disallow_licenses = None

        if 'disallow_packages' in job_config:
            self.disallow_packages = job_config['disallow_packages']
        else:
            self.disallow_packages = None

        self.image_metadata_name = None
        self.scheduler = None
        self.job = None
        self.job_deleted = False

        self.result_callback = None
        self.job_status = 'prepared'
        self.progress_log = {}
        self.errors = []

        # How often to update log callback with download progress.
        # 25 updates every 25%. I.e. 25, 50, 75, 100.
        self.download_progress_percent = 25

        kwargs = {
            'conditions': self.conditions,
            'arch': self.arch,
            'target_directory': self.download_directory,
            'conditions_wait_time': self.conditions_wait_time,
            'log_callback': self.log_callback,
            'report_callback': self.progress_callback
        }

        if self.profile:
            kwargs['profile'] = self.profile

        if self.disallow_licenses:
            kwargs['filter_licenses'] = self.disallow_licenses

        if self.disallow_packages:
            kwargs['filter_packages'] = self.disallow_packages

        self.downloader = OBSImageUtil(
            self.download_url,
            self.image_name,
            **kwargs
        )

    def start_watchdog(self, isotime=None):
        """
        Start a background job which triggers the update
        of the image build data and image fetched from the obs project.

        The job is started at a given data/time which must
        be the result of a isoformat() call. If no data/time is
        specified the job runs immediately.

        :param string isotime: data and time by isoformat()
        """
        job_time = None

        if isotime:
            job_time = datetime.strptime(isotime[:19], '%Y-%m-%dT%H:%M:%S')

        self.scheduler = BackgroundScheduler(timezone=utc)

        self.job = self.scheduler.add_job(
            self._update_image_status, 'date',
            run_date=job_time, timezone='utc'
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

    def set_result_handler(self, function):
        self.result_callback = function

    def call_result_handler(self):
        self._result_callback()

    def _result_callback(self):
        if self.result_callback:
            self.result_callback(
                self.job_id, {
                    'download_result': {
                        'id': self.job_id,
                        'image_file':
                            self.downloader.image_source,
                        'status': self.job_status,
                        'errors': self.errors,
                        'notification_email': self.notification_email,
                        'last_service': self.last_service,
                        'build_time':
                            self.downloader.build_time,
                    }
                }
            )

    def _job_submit_event(self, event):
        self.log_callback.info('Oneshot Job submitted')

    def _job_skipped_event(self, event):
        # Job is still active while the next _update_image_status
        # event was scheduled. In this case we just skip the event
        # and keep the active job waiting for an obs change
        pass

    def _update_image_status(self):
        self.log_callback.extra = {
            'job_id': self.job_id
        }
        self.log_callback.info('Job running')

        try:
            # Force parse of metadata file to get build time
            self.downloader.packages
            image_source = self.downloader.get_image()
            self.log_callback.info(
                'Downloaded: {0}'.format(image_source)
            )

            self.job_status = 'success'
            self.log_callback.info(
                'Job status: {0}'.format(self.job_status)
            )
            self._result_callback()
            self.log_callback.info('Job done')
        except Exception as issue:
            msg = '{0}: {1}'.format(type(issue).__name__, issue)

            self.job_status = 'failed'
            self.errors.append(msg)
            self.log_callback.error(msg)

            if self.downloader.conditions:
                for condition in self.downloader.conditions:
                    if not condition.get('status'):
                        self.errors.append(
                            'Condition failed: {condition}'.format(
                                condition=condition
                            )
                        )

            self._result_callback()

    def progress_callback(self, block_num, read_size, total_size, done=False):
        """
        Update progress in log callback
        """
        if done:
            self.log_callback.info('Image download finished.')
        else:
            percent = int(((block_num * read_size) / total_size) * 100)

            if percent % self.download_progress_percent == 0 \
                    and percent not in self.progress_log:
                self.log_callback.info(
                    'Image {progress}% downloaded.'.format(
                        progress=str(percent)
                    )
                )
                self.progress_log[percent] = True
