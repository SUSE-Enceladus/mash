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
import atexit
import os
import dateutil.parser

# project
from mash.services.mash_service import MashService
from mash.services.job_factory import BaseJobFactory
from mash.services.download.obs_job import OBSDownloadJob
from mash.services.download.s3bucket_job import S3BucketDownloadJob
from mash.utils.json_format import JsonFormat
from mash.utils.mash_utils import persist_json, restart_jobs, setup_logfile


class DownloadService(MashService):
    """
    Implements Download service
    """
    def post_init(self):
        self.job_document_key = 'job_document'
        self.listener_msg_key = 'listener_msg'
        self.service_queue = 'service'

        # setup service log file
        logfile_handler = setup_logfile(
            self.config.get_log_file(self.service_exchange)
        )
        self.log.addHandler(logfile_handler)

        # setup job factory
        self.job_factory = BaseJobFactory(
            'download',
            job_type_key='download_type',
            job_types={
                'OBS': OBSDownloadJob,
                'S3': S3BucketDownloadJob
            }
        )

        # setup service data directories
        self.download_directory = self.config.get_download_directory()

        self.jobs = {}

        # setup service job directory
        self.job_directory = self.config.get_job_directory(
            self.service_exchange
        )
        os.makedirs(
            self.job_directory, exist_ok=True
        )

        self.bind_queue(
            self.service_exchange, self.job_document_key, self.service_queue
        )

        # read and launch open jobs
        restart_jobs(self.job_directory, self._start_job)

        # consume on service queue
        atexit.register(lambda: os._exit(0))
        self.consume_queue(
            self._process_message,
            self.service_queue,
            self.service_exchange
        )

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.close_connection()

    def _send_job_result_for_upload(self, job_id, trigger_info):
        self._publish(
            self.service_exchange,
            self.listener_msg_key,
            JsonFormat.json_message(trigger_info)
        )
        self._delete_job(job_id)

    def _send_control_response(self, result, job_id=None):
        message = result['message']

        job_metadata = {}
        if job_id:
            job_metadata['job_id'] = job_id

        if result['ok']:
            self.log.info(message, extra=job_metadata)
        else:
            self.log.error(message, extra=job_metadata)

    def _process_message(self, message):
        try:
            job_data = JsonFormat.json_loads(format(message.body))
        except Exception as e:
            return self._send_control_response(
                {
                    'ok': False,
                    'message': 'JSON:deserialize error: {0} : {1}'.format(
                        message.body, e
                    )
                }
            )
        if message.method['routing_key'] == 'job_document':
            self._handle_jobs(job_data)

        message.ack()

    def _handle_jobs(self, job_data):
        """
        handle download job document for the OBS type
        """
        job_id = None
        if 'download_job' in job_data:
            job_id = job_data['download_job'].get('id', None)
            result = self._add_job(job_data)
        else:
            result = {
                'ok': False,
                'message': 'No idea what to do with: {0}'.format(job_data)
            }
        self._send_control_response(result, job_id)

    def _add_job(self, data):
        """
        Add a new job description file and start a watchdog job

        job description example:
        {
          "download_job": {
              "id": "123",
              "download_url": "http://download.suse.de/ibs/Devel:/PubCloud
              :/Stable:/Images12/images",
              "image": "SLES12-Azure-BYOS",
              "last_service": "upload",
              "utctime": "now|timestring_utc_timezone",
              "conditions": [
                  {
                    "package_name": "kernel-default",
                    "version": "4.13.1",
                    "release": "1.1",
                    "condition": ">="
                  },
                  {"version": "8.13.21"}
              ],
              "notification_email": "test@fake.com",
              "notify": True,
              "conditions_wait_time": 900
          }
        }
        """
        data = data['download_job']
        data['job_file'] = '{0}job-{1}.json'.format(
            self.job_directory, data['id']
        )
        persist_json(
            data['job_file'], data
        )
        return self._start_job(data)

    def _delete_job(self, job_id):
        """
        Delete job description and stop watchdog job

        delete job description example:
        {
            "download_job_delete": "123"
        }
        """
        if job_id not in self.jobs:
            return {
                'ok': False,
                'message': 'Job does not exist, can not delete it'
            }
        else:
            job_worker = self.jobs[job_id]
            # delete job file
            try:
                os.remove(job_worker.job_file)
            except Exception as e:
                return {
                    'ok': False,
                    'message': 'Job deletion failed: {0}'.format(e)
                }
            else:
                # stop running job
                if job_worker:
                    job_worker.stop_watchdog()

                # delete obs job instance
                del self.jobs[job_id]

                return {
                    'ok': True,
                    'message': 'Job Deleted'
                }

    def _start_job(self, job):
        job_id = job['id']
        time = job['utctime']

        if time == 'now':
            time = None
        else:
            time = dateutil.parser.parse(job['utctime']).isoformat()

        if 'download_type' not in job:
            job['download_type'] = 'OBS'

        job_worker = self.job_factory.create_job(job, self.config)
        job_worker.set_result_handler(self._send_job_result_for_upload)
        job_worker.set_log_handler(self.log)
        job_worker.start_watchdog(isotime=time)
        self.jobs[job_id] = job_worker
        return {
            'ok': True,
            'message': 'Job started'
        }
