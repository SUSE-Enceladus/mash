# Copyright (c) 2021 SUSE LLC.  All rights reserved.
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

from aliyun_img_utils.aliyun_image import AliyunImage

from mash.mash_exceptions import MashPublishException
from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS, FAILED


class AliyunPublishJob(MashJob):
    """
    Class for an Aliyun publishing job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.account = self.job_config['account']
            self.bucket = self.job_config['bucket']
            self.region = self.job_config['region']
            self.launch_permission = self.job_config['launch_permission']
        except KeyError as error:
            raise MashPublishException(
                'Aliyun publish Jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

    def run_job(self):
        """
        Publish image and update status.
        """
        self.status = SUCCESS
        self.cloud_image_name = self.status_msg['cloud_image_name']

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

        aliyun_image = AliyunImage(
            credentials['access_key'],
            credentials['access_secret'],
            self.region,
            self.bucket,
            log_callback=self.log_callback
        )
        regions = aliyun_image.get_regions()

        for region in regions:
            aliyun_image.region = region

            try:
                aliyun_image.publish_image(
                    self.cloud_image_name,
                    self.launch_permission
                )
            except Exception as error:
                self.status = FAILED
                msg = (
                    f'Failed to publish {self.cloud_image_name} '
                    f'in {region}: {error}'
                )
                self.add_error_msg(msg)
                self.log_callback.warning(msg)
