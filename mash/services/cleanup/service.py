# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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
import time

from apscheduler.schedulers.background import BlockingScheduler
from pytz import utc

from mash.services.mash_service import MashService
from mash.utils.mash_utils import setup_logfile


class CleanupService(MashService):
    """
    Implementation of cleanup service. Runs periodic cleanup jobs.

    * :attr:`custom_args`
    """
    def post_init(self, custom_args=None):
        """
        Initialize cleanup class.
        """
        logfile_handler = setup_logfile(
            self.config.get_log_file(self.service_exchange)
        )
        self.log.addHandler(logfile_handler)
        self.start()

    def start(self):
        self.scheduler = BlockingScheduler(timezone=utc)

        self.scheduler.add_job(
            self._purge_images,
            'cron',
            hour='5',
            minute='0'
        )
        self.scheduler.start()

    def _purge_images(self):
        download_dir = self.config.get_download_directory()
        max_image_age = self.config.get_max_image_age()

        if not os.path.isdir(download_dir):
            self.log.error('Error: no such directory {}'.format(download_dir))
            return

        now = time.time()
        cutoff = now - max_image_age * 86400

        for entry in os.scandir(download_dir):
            if (not entry.name.startswith('.')
                and entry.is_file(follow_symlinks=False)):
                if entry.stat().st_mtime < cutoff:
                    self.log.info('Purging {}'.format(entry.name))
                    os.unlink(entry.path)
