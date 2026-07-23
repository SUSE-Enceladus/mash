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

import contextlib
from kombu import Connection as KombuConnection
from kombu import Exchange as KombuExchange
from kombu import Queue as KombuQueue
from kombu.exceptions import KombuError

# Expose AMQPError as an alias for KombuError to keep compatibility
AMQPError = KombuError


class MessageWrapper(object):
    def __init__(self, kombu_msg, channel):
        self._kombu_msg = kombu_msg
        self.channel = channel

    @property
    def body(self):
        if isinstance(self._kombu_msg.body, bytes):
            return self._kombu_msg.body.decode('utf-8')
        return self._kombu_msg.body

    @property
    def method(self):
        delivery_info = self._kombu_msg.delivery_info or {}
        return {'routing_key': delivery_info.get('routing_key', '')}

    def ack(self):
        self._kombu_msg.ack()


class ExchangeWrapper(object):
    def __init__(self, channel_wrapper):
        self.channel_wrapper = channel_wrapper

    def declare(self, exchange, exchange_type='direct', durable=True):
        ex = KombuExchange(name=exchange, type=exchange_type, durable=durable)
        ex(self.channel_wrapper._kombu_channel).declare()


class QueueWrapper(object):
    def __init__(self, channel_wrapper):
        self.channel_wrapper = channel_wrapper

    def declare(self, queue, durable=True):
        q = KombuQueue(name=queue, durable=durable)
        q(self.channel_wrapper._kombu_channel).declare()

        class Method(object):
            def __init__(self, name):
                self.queue = name

        class QueueResult(object):
            def __init__(self, name):
                self.method = Method(name)

        return QueueResult(queue)

    def bind(self, exchange, queue, routing_key):
        ex = KombuExchange(name=exchange, type='direct')
        q = KombuQueue(name=queue, exchange=ex, routing_key=routing_key)
        q(self.channel_wrapper._kombu_channel).bind(self.channel_wrapper._kombu_channel)

    def unbind(self, queue, exchange, routing_key):
        self.channel_wrapper._kombu_channel.queue_unbind(
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
        from kombu import Producer
        properties = properties or {}
        content_type = properties.get('content_type', 'application/json')
        delivery_mode = properties.get('delivery_mode', 2)

        prod = Producer(self.channel_wrapper._kombu_channel)
        prod.publish(
            body=body,
            routing_key=routing_key,
            exchange=exchange,
            content_type=content_type,
            delivery_mode=delivery_mode,
            mandatory=mandatory
        )


class ChannelWrapper(object):
    def __init__(self, connection_wrapper):
        self._connection_wrapper = connection_wrapper
        self._kombu_channel = connection_wrapper._kombu_conn.channel()
        self._closed = False
        self._consuming = False
        self._consumers = []
        self._active_consumer_context = None

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
        if self._active_consumer_context:
            try:
                self._active_consumer_context.__exit__(None, None, None)
            except Exception:
                pass
            self._active_consumer_context = None
        try:
            self._kombu_channel.close()
        except Exception:
            pass

    def stop_consuming(self):
        self._consuming = False

    def start_consuming(self):
        self._consuming = True

        with contextlib.ExitStack() as stack:
            for queue_name, user_callback in self._consumers:
                q = KombuQueue(name=queue_name, no_ack=False)

                # Capture closure properly
                def make_cb(u_cb):
                    def cb(body, message):
                        wrapped_msg = MessageWrapper(message, self)
                        u_cb(wrapped_msg)
                    return cb

                consumer = self._connection_wrapper._kombu_conn.Consumer(
                    queues=[q],
                    callbacks=[make_cb(user_callback)]
                )
                stack.enter_context(consumer)

            while self._consuming and self._connection_wrapper._kombu_conn.connected:
                try:
                    self._connection_wrapper._kombu_conn.drain_events(timeout=1.0)
                except TimeoutError:
                    continue
                except Exception as e:
                    self._consuming = False
                    raise e


class Connection(object):
    def __init__(self, host, username, password, port=5672, kwargs=None):
        heartbeat = 600
        if kwargs and 'heartbeat' in kwargs:
            heartbeat = kwargs['heartbeat']

        # Support "memory://" for easier mocking/testing if host starts with memory
        if host.startswith('memory:'):
            self._kombu_conn = KombuConnection(host)
        else:
            self._kombu_conn = KombuConnection(
                hostname=host,
                userid=username,
                password=password,
                port=port,
                heartbeat=heartbeat
            )

    @property
    def is_open(self):
        return self._kombu_conn.connected

    @property
    def is_closed(self):
        return not self._kombu_conn.connected

    def channel(self):
        return ChannelWrapper(self)

    def close(self):
        try:
            self._kombu_conn.close()
        except Exception:
            pass
