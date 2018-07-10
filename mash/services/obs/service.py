# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
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
from mash.services.base_service import BaseService
from mash.services.obs.build_result import OBSImageBuildResult
from mash.utils.json_format import JsonFormat
from mash.services.obs.defaults import Defaults


class OBSImageBuildResultService(BaseService):
    """
    Implements Open BuildService image result network
    service
    """
    def post_init(self):
        # setup service log file
        self.set_logfile(self.config.get_log_file(self.service_exchange))

        # setup service data directories
        self.download_directory = self.config.get_download_directory()

        self.jobs = {}

        # read and launch open jobs
        self.restart_jobs(self._start_job)

        # consume on service queue
        atexit.register(lambda: os._exit(0))
        self.consume_queue(self._process_message)
        try:
            self.channel.start_consuming()
        except Exception:
            if self.channel and self.channel.is_open:
                self.channel.stop_consuming()
                self.close_connection()

    def _send_job_response(self, job_id, status_message):
        self.log.info(status_message, extra={'job_id': job_id})

    def _send_job_result_for_uploader(self, job_id, trigger_info):
        self.publish_job_result(
            'uploader', job_id, JsonFormat.json_message(trigger_info)
        )
        if not self.jobs[job_id].job_nonstop:
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
        message.ack()
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

    def _handle_jobs(self, job_data):
        """
        handle obs job document
        """
        job_id = None
        if 'obs_job' in job_data:
            job_id = job_data['obs_job'].get('id', None)
            self.log.info(
                JsonFormat.json_message(job_data),
                extra={'job_id': job_id}
            )
            result = self._add_job(job_data)
        elif 'obs_job_delete' in job_data and job_data['obs_job_delete']:
            job_id = job_data['obs_job_delete']
            self.log.info(
                'Deleting Job'.format(job_id),
                extra={'job_id': job_id}
            )
            result = self._delete_job(job_id)
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
          "obs_job": {
              "id": "123",
              "api_url": "https://api.opensuse.org",
              "project": "Virtualization:Appliances:Images:Testing_x86",
              "image": "test-image-oem",
              "utctime": "now|always|timestring_utc_timezone",
              "conditions": [
                  {"package": ["kernel-default", ">=4.13.1", ">=1.1"]},
                  {"image": "1.42.1"}
              ]
          }
        }
        """
        data = data['obs_job']
        data['job_file'] = self.persist_job_config(data)
        return self._start_job(data)

    def _delete_job(self, job_id):
        """
        Delete job description and stop watchdog job

        delete job description example:
        {
            "obs_job_delete": "123"
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
        if 'conditions' not in job:
            job['conditions'] = None

        job_id = job['id']
        time = job['utctime']
        nonstop = False
        if time == 'now':
            time = None
        elif time == 'always':
            time = None
            nonstop = True
        else:
            time = dateutil.parser.parse(job['utctime']).isoformat()

        job_worker = OBSImageBuildResult(
            job_id=job_id, job_file=job['job_file'],
            project=job['project'], package=job['image'],
            conditions=job['conditions'],
            api_url=job.get('api_url') or Defaults.get_api_url(),
            download_directory=self.download_directory
        )
        job_worker.set_log_handler(self._send_job_response)
        job_worker.set_result_handler(self._send_job_result_for_uploader)
        job_worker.start_watchdog(
            nonstop=nonstop, isotime=time
        )
        self.jobs[job_id] = job_worker
        return {
            'ok': True,
            'message': 'Job started'
        }
