# Copyright (c) 2026 SUSE LLC.  All rights reserved.
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

import pika
import pika.exceptions
import pika_pool

# Expose AMQPError as an alias for pika.exceptions.AMQPError to keep compatibility
AMQPError = pika.exceptions.AMQPError


class MessageWrapper(object):
    def __init__(self, body, method, properties, delivery_tag, channel_wrapper):
        self._body = body
        self._method = method
        self._properties = properties
        self.delivery_tag = delivery_tag
        self.channel = channel_wrapper

    @property
    def body(self):
        if isinstance(self._body, bytes):
            return self._body.decode('utf-8')
        return self._body

    @property
    def method(self):
        return {'routing_key': getattr(self._method, 'routing_key', '')}

    def ack(self):
        self.channel.basic_ack(self.delivery_tag)


class ExchangeWrapper(object):
    def __init__(self, channel_wrapper):
        self.channel_wrapper = channel_wrapper

    def declare(self, exchange, exchange_type='direct', durable=True):
        self.channel_wrapper._declare_exchange(
            exchange=exchange,
            exchange_type=exchange_type,
            durable=durable
        )


class QueueWrapper(object):
    def __init__(self, channel_wrapper):
        self.channel_wrapper = channel_wrapper

    def declare(self, queue, durable=True):
        self.channel_wrapper._declare_queue(queue=queue, durable=durable)

        class Method(object):
            def __init__(self, name):
                self.queue = name

        class QueueResult(object):
            def __init__(self, name):
                self.method = Method(name)

        return QueueResult(queue)

    def bind(self, exchange, queue, routing_key):
        self.channel_wrapper._bind_queue(
            exchange=exchange,
            queue=queue,
            routing_key=routing_key
        )

    def unbind(self, queue, exchange, routing_key):
        self.channel_wrapper._unbind_queue(
            queue=queue,
            exchange=exchange,
            routing_key=routing_key
        )


class BasicWrapper(object):
    def __init__(self, channel_wrapper):
        self.channel_wrapper = channel_wrapper

    def consume(self, callback, queue):
        self.channel_wrapper._consumers.append((queue, callback))

    def publish(self, body, routing_key, exchange, properties=None, mandatory=False):
        self.channel_wrapper._publish(
            body=body,
            routing_key=routing_key,
            exchange=exchange,
            properties=properties,
            mandatory=mandatory
        )


class ChannelWrapper(object):
    def __init__(self, connection_wrapper):
        self._connection_wrapper = connection_wrapper
        self._closed = False
        self._consuming = False
        self._consumers = []
        self._active_consumer_cxn = None

        self.exchange = ExchangeWrapper(self)
        self.queue = QueueWrapper(self)
        self.basic = BasicWrapper(self)

    @property
    def is_open(self):
        return not self._closed

    @property
    def is_closed(self):
        return self._closed

    def confirm_deliveries(self):
        pass

    def close(self):
        self._closed = True
        self._consuming = False
        if self._active_consumer_cxn:
            try:
                self._active_consumer_cxn.channel.stop_consuming()
            except Exception:
                pass
            try:
                self._active_consumer_cxn.close()
            except Exception:
                pass
            self._active_consumer_cxn = None

    def stop_consuming(self):
        self._consuming = False
        if self._active_consumer_cxn:
            try:
                self._active_consumer_cxn.channel.stop_consuming()
            except Exception:
                pass

    def start_consuming(self):
        self._consuming = True

        self._active_consumer_cxn = self._connection_wrapper.acquire_connection()
        channel = self._active_consumer_cxn.channel

        for queue_name, user_callback in self._consumers:
            def make_cb(u_cb):
                def cb(ch, method, properties, body):
                    wrapped_msg = MessageWrapper(
                        body=body,
                        method=method,
                        properties=properties,
                        delivery_tag=method.delivery_tag,
                        channel_wrapper=self
                    )
                    u_cb(wrapped_msg)
                return cb

            channel.basic_consume(
                queue=queue_name,
                on_message_callback=make_cb(user_callback),
                auto_ack=False
            )

        try:
            channel.start_consuming()
        finally:
            self._consuming = False
            if self._active_consumer_cxn:
                try:
                    self._active_consumer_cxn.release()
                except Exception:
                    pass
                self._active_consumer_cxn = None

    def basic_ack(self, delivery_tag):
        if self._active_consumer_cxn:
            self._active_consumer_cxn.channel.basic_ack(delivery_tag=delivery_tag)

    def _execute_on_channel(self, func):
        with self._connection_wrapper.acquire_connection() as cxn:
            return func(cxn.channel)

    def _declare_exchange(self, exchange, exchange_type, durable):
        def action(channel):
            channel.exchange_declare(
                exchange=exchange,
                exchange_type=exchange_type,
                durable=durable
            )
        self._execute_on_channel(action)

    def _declare_queue(self, queue, durable):
        def action(channel):
            channel.queue_declare(queue=queue, durable=durable)
        self._execute_on_channel(action)

    def _bind_queue(self, exchange, queue, routing_key):
        def action(channel):
            channel.queue_bind(
                queue=queue,
                exchange=exchange,
                routing_key=routing_key
            )
        self._execute_on_channel(action)

    def _unbind_queue(self, queue, exchange, routing_key):
        def action(channel):
            channel.queue_unbind(
                queue=queue,
                exchange=exchange,
                routing_key=routing_key
            )
        self._execute_on_channel(action)

    def _publish(self, body, routing_key, exchange, properties=None, mandatory=False):
        properties = properties or {}
        content_type = properties.get('content_type', 'application/json')
        delivery_mode = properties.get('delivery_mode', 2)

        pika_properties = pika.BasicProperties(
            content_type=content_type,
            delivery_mode=delivery_mode
        )

        def action(channel):
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body,
                properties=pika_properties,
                mandatory=mandatory
            )
        self._execute_on_channel(action)


class Connection(object):
    def __init__(self, host, username, password, port=5672, kwargs=None):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.kwargs = kwargs or {}
        self.heartbeat = self.kwargs.get('heartbeat', 600)

        def create_cxn():
            if self.host.startswith('memory:'):
                raise NotImplementedError("Memory transport not supported in pika wrapper")

            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=self.heartbeat
            )
            return pika.BlockingConnection(parameters)

        self._pool = pika_pool.QueuedPool(
            create=create_cxn,
            max_size=10,
            max_overflow=10,
            timeout=30,
            recycle=None,
            stale=None,
        )

        self._closed = False

    @property
    def is_open(self):
        return not self._closed

    @property
    def is_closed(self):
        return self._closed

    def channel(self):
        return ChannelWrapper(self)

    def acquire_connection(self):
        return self._pool.acquire()

    def close(self):
        self._closed = True
        while not self._pool._queue.empty():
            try:
                fairy = self._pool._queue.get_nowait()
                self._pool.close(fairy)
            except Exception:
                pass
