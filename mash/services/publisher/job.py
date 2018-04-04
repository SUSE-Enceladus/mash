# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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

import dateutil.parser

from mash.mash_exceptions import MashPublisherException
from mash.services.status_levels import UNKOWN
from mash.services.publisher.constants import NOT_IMPLEMENTED


class PublisherJob(object):
    """
    Class for an individual publisher job.
    """

    def __init__(self, id, provider, publish_regions, utctime, job_file=None):
        self.cloud_image_name = None
        self.credentials = None
        self.iteration_count = 0
        self.id = id
        self.job_file = job_file
        self.log_callback = None
        self.provider = self.validate_provider(provider)
        self.publish_regions = self.validate_publish_regions(publish_regions)
        self.status = UNKOWN
        self.utctime = self.validate_timestamp(utctime)

    def get_metadata(self):
        """
        Return dictionary of metadata based on job.
        """
        return {'job_id': self.id}

    def _publish(self):
        """
        Publish image and update status.
        """
        raise NotImplementedError(NOT_IMPLEMENTED)

    def publish_image(self):
        """
        Update iteration_count and publish image.
        """
        self.iteration_count += 1
        self._publish()

    def send_log(self, message, success=True):
        """
        Send message to log callback method.
        """
        if self.log_callback:
            self.log_callback(
                'Pass[{0}]: {1}'.format(
                    self.iteration_count,
                    message
                ),
                self.get_metadata(),
                success
            )

    def set_log_callback(self, callback):
        """
        Set log_callback function to callback.
        """
        self.log_callback = callback

    def validate_provider(self, provider):
        """
        Validate the provider is supported for publisher.
        """
        if provider not in ('ec2',):
            raise MashPublisherException(
                'Provider: {0} not supported.'.format(provider)
            )
        return provider

    def validate_publish_regions(self, publish_regions):
        """
        Validate the publish regions dict has required keys.
        """
        for region_info in publish_regions:
            if not (region_info['account'] and region_info['target_regions']):
                raise MashPublisherException(
                    'Invalid publish_regions format. '
                    'Must be a list of dictionaries with account and '
                    'target_regions keys.'
                )

        return publish_regions

    def validate_timestamp(self, utctime):
        """
        Validate the utctime is always, now or valid utc time format.
        """
        if utctime not in ('always', 'now'):
            try:
                utctime = dateutil.parser.parse(utctime)
            except Exception as e:
                raise MashPublisherException(
                    'Invalid utctime format: {0}.'.format(utctime)
                )
        return utctime
