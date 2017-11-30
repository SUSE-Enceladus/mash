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
import jwt

# project
from mash.services.base_service import BaseService
from mash.utils.json_format import JsonFormat


class CredentialsService(BaseService):
    """
    Implements CredentialsService based on web token technology

    Note:
    The current implementation is not final ! The service acts as
    a stub service in order to develop other mash services which
    requires cloud credentials. Thus error handling, security aspects
    and token workflow as well as request validation are not
    completed and will change for the final version of this service
    """
    def post_init(self):
        # consume on service queue
        self.consume_queue(
            self._control_in, self.bind_service_queue()
        )
        try:
            self.channel.start_consuming()
        except Exception:
            if self.channel and self.channel.is_open:
                self.channel.stop_consuming()
                self.close_connection()

    def _send_control_response(self, result, job_id=None):
        message = result['message']

        job_metadata = {}
        if job_id:
            job_metadata['job_id'] = job_id

        if result['ok']:
            self.log.info(message, extra=job_metadata)
        else:
            self.log.error(message, extra=job_metadata)

    def _control_in(self, channel, method, properties, message):
        """
        On message sent by client

        The message is interpreted as json data and allows for:

        1. add new credentials payload
        """
        channel.basic_ack(method.delivery_tag)
        message_data = {}
        try:
            message_data = JsonFormat.json_loads_byteified(format(message))
        except Exception as e:
            return self._send_control_response(
                {
                    'ok': False,
                    'message': 'JSON:deserialize error: {0} : {1}'.format(
                        message, e
                    )
                }
            )
        if 'credentials' in message_data:
            self._create_credentials(message_data)
        else:
            self._send_control_response(
                {
                    'ok': False,
                    'message': 'No idea what to do with: {0}'.format(
                        message_data
                    )
                }
            )

    def _create_credentials(self, data):
        """
        Create JWT token from the provided information and send
        it to the authentication exchange

        credentials description example:
        {
          "credentials": {
              "id": "123"
              "csp": "ec2",
              "payload": {
                  ...credentials data
              }
          }
        }
        """
        payload = None
        csp = None
        job_id = None
        if 'credentials' in data:
            job = data['credentials']
            if 'id' in job:
                job_id = data['credentials']['id']
            if 'payload' in job:
                payload = data['credentials']['payload']
            if 'csp' in job:
                csp = data['credentials']['csp']

        if payload and csp and job_id:
            token = jwt.encode(
                payload, 'secret', algorithm='HS256'
            )
            queue_name = '{0}_{1}'.format(csp, job_id)
            self._bind_queue(self.service_exchange, queue_name)
            self._publish(
                self.service_exchange, queue_name, JsonFormat.json_message(
                    {'credentials': token}
                )
            )
            result = {
                'ok': True,
                'message': 'Credentials token created'
            }
        else:
            result = {
                'ok': False,
                'message': 'Insufficient job information'
            }
        self._send_control_response(result, job_id)
