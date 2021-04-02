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

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashCreateException
from mash.services.status_levels import SUCCESS
from aliyun_img_utils.aliyun_image import AliyunImage


class AliyunCreateJob(MashJob):
    """
    Implements create VM image in Aliyun.
    """
    def post_init(self):
        self.cloud_image_description = ''

        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.bucket = self.job_config['bucket']
            self.cloud_image_description = \
                self.job_config['image_description']
            self.cloud_architecture = self.job_config['cloud_architecture']
            self.platform = self.job_config['platform']
        except KeyError as error:
            raise MashCreateException(
                'Aliyun create jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.disk_size = self.job_config.get('disk_size')

    def run_job(self):
        self.status = SUCCESS
        self.status_msg['source_regions'] = {}
        self.log_callback.info('Creating image.')

        self.cloud_image_name = self.status_msg['cloud_image_name']
        object_name = self.status_msg['object_name']

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]

        aliyun_image = AliyunImage(
            credentials['access_key'],
            credentials['access_secret'],
            self.region,
            self.bucket,
            log_callback=self.log_callback
        )

        try:
            existing_image = aliyun_image.get_compute_image(
                image_name=self.cloud_image_name
            )
        except Exception:
            existing_image = None

        if existing_image:
            self.log_callback.info(
                'Replacing existing image with the same name.'
            )
            aliyun_image.delete_compute_image(self.cloud_image_name)

        kwargs = {}
        if self.disk_size:
            kwargs['disk_image_size'] = self.disk_size

        image_id = aliyun_image.create_compute_image(
            self.cloud_image_name,
            self.cloud_image_description,
            object_name,
            platform=self.platform,
            arch=self.cloud_architecture,
            **kwargs
        )

        self.status_msg['source_regions'][self.region] = image_id
        self.log_callback.info(
            'Created image: {0}'.format(
                self.cloud_image_name
            )
        )
