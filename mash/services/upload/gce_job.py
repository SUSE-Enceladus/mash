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

# project
from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashUploadException
from mash.utils.mash_utils import (
    format_string_with_date,
    timestamp_from_epoch
)
from mash.services.status_levels import SUCCESS
from gceimgutils.gceutils import (
    get_storage_client,
    blob_exists,
    get_credentials
)
from gceimgutils.gceuploadblob import GCEUploadBlob
from gceimgutils.gceremoveblob import GCERemoveBlob


class GCEUploadJob(MashJob):
    """
    Implements system image upload to GCE
    """
    def post_init(self):
        try:
            self.account = self.job_config['account']
            self.region = self.job_config['region']
            self.bucket = self.job_config['bucket']
            self.base_cloud_image_name = self.job_config['cloud_image_name']
        except KeyError as error:
            raise MashUploadException(
                'GCE upload jobs require a(n) {0} '
                'key in the job doc.'.format(
                    error
                )
            )

        self.use_build_time = self.job_config.get('use_build_time')
        self.force_replace_image = self.job_config.get('force_replace_image')

        # SLES 11 is EOL, however images remain available in the
        # build service and thus we need to continue to test for
        # this condition.
        if 'sles-11' in self.base_cloud_image_name:
            raise MashUploadException(
                'No SLES 11 support in mash for GCE.'
            )

    def run_job(self):
        self.status = SUCCESS
        self.log_callback.info('Uploading image.')

        timestamp = None
        build_time = self.status_msg.get('build_time', 'unknown')

        if self.use_build_time and (build_time != 'unknown'):
            timestamp = timestamp_from_epoch(build_time)
        elif self.use_build_time and (build_time == 'unknown'):
            raise MashUploadException(
                'use_build_time set for job but build time is unknown.'
            )

        self.cloud_image_name = format_string_with_date(
            self.base_cloud_image_name,
            timestamp=timestamp
        )

        self.request_credentials([self.account])
        credentials = self.credentials[self.account]
        project = credentials['project_id']
        credentials_obj = get_credentials(project, credentials_info=credentials)
        storage_client = get_storage_client(project, credentials_obj)

        object_name = ''.join([self.cloud_image_name, '.tar.gz'])

        exists = blob_exists(storage_client, self.bucket, object_name)
        if exists and not self.force_replace_image:
            raise MashUploadException(
                'Image tarball: {object_name} already exists '
                'in bucket: {bucket}. Use force_replace_image '
                'to replace the existing tarball.'.format(
                    object_name=object_name,
                    bucket=self.bucket
                )
            )
        elif exists and self.force_replace_image:
            self.log_callback.info(
                'Deleting tarball: {0}, in the bucket named: {1}'.format(
                    object_name,
                    self.bucket
                )
            )
            remover = GCERemoveBlob(
                object_name,
                self.bucket,
                credentials_info=credentials,
                project=project,
                log_callback=self.log_callback
            )
            remover.remove_blob()

        uploader = GCEUploadBlob(
            self.bucket,
            self.status_msg['image_file'],
            blob_name=object_name,
            credentials_info=credentials,
            project=project,
            log_callback=self.log_callback
        )
        uploader.upload_blob()

        self.status_msg['cloud_image_name'] = self.cloud_image_name
        self.status_msg['object_name'] = object_name
        self.log_callback.info(
            'Uploaded image: {0}, to the bucket named: {1}'.format(
                object_name,
                self.bucket
            )
        )
