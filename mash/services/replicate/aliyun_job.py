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

from mash.mash_exceptions import MashReplicateException
from mash.services.mash_job import MashJob
from mash.services.status_levels import FAILED, SUCCESS


class AliyunReplicateJob(MashJob):
    """
    Class for an Aliyun replicate job.
    """

    def post_init(self):
        """
        Post initialization method.
        """
        try:
            self.account = self.job_config['account']
            self.bucket = self.job_config['bucket']
            self.region = self.job_config['region']
        except KeyError as error:
            raise MashReplicateException(
                'Aliyun replicate jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

    def run_job(self):
        """
        Replicate image to all target regions in each source region.
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

        self.log_callback.info(
            'Replicating {image}'.format(image=self.cloud_image_name)
        )

        images = aliyun_image.replicate_image(self.cloud_image_name)

        for region, image_id in images.items():
            error_msg = ''

            if image_id:
                aliyun_image.region = region
                try:
                    aliyun_image.wait_on_compute_image(image_id)
                except Exception as error:
                    self.status = FAILED
                    error_msg = str(error)
            else:
                self.status = FAILED

            if self.status == FAILED:
                msg = 'Replicate to {0} failed: {1}'.format(
                    region,
                    error_msg
                )
                self.add_error_msg(msg)
                self.log_callback.warning(msg)

        # Merge region to image id hash
        self.status_msg['source_regions'] = {
            **self.status_msg['source_regions'],
            **images
        }
