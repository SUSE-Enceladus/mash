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

from mash.mash_exceptions import MashDeprecateException
from mash.services.mash_job import MashJob
from mash.services.status_levels import SUCCESS


class AliyunDeprecateJob(MashJob):
    """
    Class for an Aliyun deprecate job.
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
            raise MashDeprecateException(
                'Aliyun deprecate Jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.old_cloud_image_name = self.job_config.get(
            'old_cloud_image_name'
        )

    def run_job(self):
        """
        Deprecate image in all target regions in each source region.
        """
        self.status = SUCCESS

        if self.old_cloud_image_name is None:
            # There is no old image that needs deprecate for the job.
            return

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
                aliyun_image.deprecate_image(
                    self.old_cloud_image_name,
                    replacement_image=self.cloud_image_name
                )
            except Exception as error:
                msg = (
                    f'Failed to deprecate {self.old_cloud_image_name} '
                    f'in {region}: {error}'
                )
                self.add_error_msg(msg)
                self.log_callback.warning(msg)
