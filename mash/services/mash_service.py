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

import logging

from amqpstorm import Connection

# project
from mash.log.filter import BaseServiceFilter
from mash.services.status_levels import SUCCESS
from mash.mash_exceptions import MashRabbitConnectionException
from mash.utils.mash_utils import setup_rabbitmq_log_handler
from mash.utils.email_notification import EmailNotification


class MashService(object):
    """
    Base class for RabbitMQ message broker

    Attributes

    * :attr:`host`
      RabbitMQ server host

    * :attr:`service_exchange`
      Name of service exchange
    """
    def __init__(self, service_exchange, config, custom_args=None):
        self.channel = None
        self.connection = None

        self.service_exchange = service_exchange
        self.custom_args = custom_args
        self.config = config

        # amqp settings
        self.amqp_host = self.config.get_amqp_host()
        self.amqp_user = self.config.get_amqp_user()
        self.amqp_pass = self.config.get_amqp_pass()

        self._open_connection()

        logging.basicConfig()
        self.log = logging.getLogger(
            '{0}Service'.format(self.service_exchange.title())
        )
        self.log.setLevel(logging.DEBUG)
        self.log.propagate = False

        rabbit_handler = setup_rabbitmq_log_handler(
            self.amqp_host,
            self.amqp_user,
            self.amqp_pass
        )
        self.log.addHandler(rabbit_handler)
        self.log.addFilter(BaseServiceFilter())

        # notification settings
        self.notification_class = EmailNotification(
            self.config.get_smtp_host(),
            self.config.get_smtp_port(),
            self.config.get_smtp_user(),
            self.config.get_smtp_pass(),
            self.config.get_smtp_ssl(),
            log_callback=self.log
        )

        self.post_init()

    def post_init(self):
        """
        Post initialization method

        Implementation in specialized service class
        """
        pass

    def _declare_direct_exchange(self, exchange):
        """
        Declare/create exchange and set as durable.

        The exchange, queues and messages will survive a broker restart.
        """
        self.channel.exchange.declare(
            exchange=exchange, exchange_type='direct', durable=True
        )

    def _declare_queue(self, queue):
        """
        Declare the queue and set as durable.
        """
        return self.channel.queue.declare(queue=queue, durable=True)

    def _get_queue_name(self, exchange, name):
        """
        Return formatted name based on exchange and queue name.

        Example: obs.service
        """
        return '{0}.{1}'.format(exchange, name)

    def _open_connection(self):
        """
        Open connection or channel if currently closed or None.

        Raises: MashRabbitConnectionException if connection
                cannot be established.
        """
        if not self.connection or self.connection.is_closed:
            try:
                self.connection = Connection(
                    self.amqp_host,
                    self.amqp_user,
                    self.amqp_pass,
                    kwargs={'heartbeat': 600}
                )
            except Exception as e:
                raise MashRabbitConnectionException(
                    'Connection to RabbitMQ server failed: {0}'.format(e)
                )

        if not self.channel or self.channel.is_closed:
            self.channel = self.connection.channel()
            self.channel.confirm_deliveries()

    def _publish(self, exchange, routing_key, message):
        """
        Publish message to the provided exchange with the routing key.
        """
        self.channel.basic.publish(
            body=message,
            routing_key=routing_key,
            exchange=exchange,
            properties={
                'content_type': 'application/json',
                'delivery_mode': 2
            },
            mandatory=True
        )

    def bind_queue(self, exchange, routing_key, name):
        """
        Bind queue on exchange to the provided routing key.

        All messages that match the routing key will be inserted in queue.
        """
        self._declare_direct_exchange(exchange)
        queue = self._get_queue_name(exchange, name)
        self._declare_queue(queue)
        self.channel.queue.bind(
            exchange=exchange, queue=queue, routing_key=routing_key
        )
        return queue

    def close_connection(self):
        """
        If channel or connection open, stop consuming and close.
        """
        if self.channel and self.channel.is_open:
            self.channel.stop_consuming()
            self.channel.close()

        if self.connection and self.connection.is_open:
            self.connection.close()

    def consume_queue(self, callback, queue_name, exchange):
        """
        Declare and consume queue.
        """
        queue = self._get_queue_name(exchange, queue_name)
        self._declare_queue(queue)
        self.channel.basic.consume(
            callback=callback, queue=queue
        )

    def unbind_queue(self, queue, exchange, routing_key):
        """
        Unbind the routing_key from the queue on given exchange.
        """
        queue = self._get_queue_name(exchange, queue)
        self.channel.queue.unbind(
            queue=queue, exchange=exchange, routing_key=routing_key
        )

    def _should_notify(
        self, notification_email, notification_type, utctime, status,
        last_service
    ):
        """
        Return True if a notification should be sent based on job info.
        """
        if not notification_email:
            return False
        elif status != SUCCESS:
            return True
        elif notification_type == 'periodic' and utctime != 'always':
            return True
        elif last_service == self.service_exchange and utctime != 'always':
            return True

        return False

    def _create_notification_content(
        self, job_id, status, utctime, last_service, image_name,
        iteration_count=None, error=None
    ):
        """
        Build content string for job notification message.
        """
        msg = [
            'Job: {job_id}\n'
            'Image Name: {image_name}\n'
            'Service: {service}\n'
            'Log: {job_log}\n\n'
        ]

        if status == SUCCESS:
            if self.service_exchange == last_service:
                msg.append('Job finished successfully.')
            else:
                msg.append(
                    'Job finished through the {service} service.'
                )
        else:
            msg.append('Job failed.')

            if utctime == 'always' and iteration_count:
                msg.append(' The current pass is #{iteration_count}.')

            if error:
                msg.append(' The following error was logged: \n\n{error}')

        msg = ''.join(msg)

        return msg.format(
            job_id=job_id,
            service=self.service_exchange,
            job_log=self.config.get_job_log_file(job_id),
            image_name=image_name,
            iteration_count=str(iteration_count),
            error=error
        )

    def send_notification(
        self, job_id, notification_email, notification_type, status, utctime,
        last_service, image_name, iteration_count=None, error=None
    ):
        """
        Send job notification based on result of _should_notify.
        """
        notify = self._should_notify(
            notification_email, notification_type, utctime, status,
            last_service
        )

        if notify:
            content = self._create_notification_content(
                job_id, status, utctime, last_service, image_name,
                iteration_count, error
            )
            self.notification_class.send_notification(
                content,
                self.config.get_notification_subject(),
                notification_email
            )
