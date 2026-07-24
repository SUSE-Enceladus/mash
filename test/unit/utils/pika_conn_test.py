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

import pytest
from unittest.mock import MagicMock, patch

import pika
import pika.exceptions

from mash.utils.pika_conn import Connection, MessageWrapper


class TestPikaConn(object):
    @patch('mash.utils.pika_conn.pika_pool.QueuedPool')
    def test_connection_init_and_close(self, mock_queued_pool):
        mock_pool_instance = MagicMock()
        mock_queued_pool.return_value = mock_pool_instance

        # Setup mock queue queue for pool closing
        mock_queue = MagicMock()
        mock_queue.empty.side_effect = [False, True]
        mock_fairy = MagicMock()
        mock_queue.get_nowait.return_value = mock_fairy
        mock_pool_instance._queue = mock_queue

        conn = Connection(
            host='localhost',
            username='guest',
            password='password',
            port=5672,
            kwargs={'heartbeat': 600}
        )

        assert conn.is_open is True
        assert conn.is_closed is False

        # Close the connection
        conn.close()

        assert conn.is_open is False
        assert conn.is_closed is True
        mock_pool_instance.close.assert_called_once_with(mock_fairy)

    def test_message_wrapper(self):
        mock_channel = MagicMock()
        mock_method = MagicMock()
        mock_method.routing_key = 'test-key'
        mock_method.delivery_tag = 12345
        mock_properties = MagicMock()

        # Test string body
        msg_str = MessageWrapper(
            body='{"foo": "bar"}',
            method=mock_method,
            properties=mock_properties,
            delivery_tag=12345,
            channel_wrapper=mock_channel
        )
        assert msg_str.body == '{"foo": "bar"}'
        assert msg_str.method == {'routing_key': 'test-key'}

        # Test bytes body
        msg_bytes = MessageWrapper(
            body=b'test-bytes',
            method=mock_method,
            properties=mock_properties,
            delivery_tag=12345,
            channel_wrapper=mock_channel
        )
        assert msg_bytes.body == 'test-bytes'

        # Test ack
        msg_str.ack()
        mock_channel.basic_ack.assert_called_once_with(12345)

    @patch('mash.utils.pika_conn.pika_pool.QueuedPool')
    def test_channel_wrapper_declarations(self, mock_queued_pool):
        mock_pool_instance = MagicMock()
        mock_queued_pool.return_value = mock_pool_instance

        # Mock the fairy / acquired connection
        mock_fairy_connection = MagicMock()
        mock_pika_channel = MagicMock()
        mock_fairy_connection.channel = mock_pika_channel

        # Support context manager on acquire
        mock_pool_instance.acquire.return_value.__enter__.return_value = mock_fairy_connection

        conn = Connection('localhost', 'user', 'pass')
        channel = conn.channel()

        assert channel.is_open is True
        assert channel.is_closed is False

        # Exchange declare
        channel.exchange.declare(exchange='test-ex', exchange_type='topic', durable=True)
        mock_pika_channel.exchange_declare.assert_called_once_with(
            exchange='test-ex',
            exchange_type='topic',
            durable=True
        )

        # Queue declare
        res = channel.queue.declare(queue='test-q', durable=False)
        assert res.method.queue == 'test-q'
        mock_pika_channel.queue_declare.assert_called_once_with(
            queue='test-q',
            durable=False
        )

        # Queue bind
        channel.queue.bind(exchange='test-ex', queue='test-q', routing_key='rk')
        mock_pika_channel.queue_bind.assert_called_once_with(
            queue='test-q',
            exchange='test-ex',
            routing_key='rk'
        )

        # Queue unbind
        channel.queue.unbind(exchange='test-ex', queue='test-q', routing_key='rk')
        mock_pika_channel.queue_unbind.assert_called_once_with(
            queue='test-q',
            exchange='test-ex',
            routing_key='rk'
        )

        # Basic publish
        channel.basic.publish(body='msg', routing_key='rk', exchange='test-ex')
        # We need to capture the pika.BasicProperties passed to basic_publish
        _, kwargs = mock_pika_channel.basic_publish.call_args
        assert kwargs['exchange'] == 'test-ex'
        assert kwargs['routing_key'] == 'rk'
        assert kwargs['body'] == 'msg'
        assert isinstance(kwargs['properties'], pika.BasicProperties)
        assert kwargs['properties'].content_type == 'application/json'
        assert kwargs['properties'].delivery_mode == 2

    @patch('mash.utils.pika_conn.pika_pool.QueuedPool')
    def test_consuming_and_stop(self, mock_queued_pool):
        mock_pool_instance = MagicMock()
        mock_queued_pool.return_value = mock_pool_instance

        mock_fairy_connection = MagicMock()
        mock_pika_channel = MagicMock()
        mock_fairy_connection.channel = mock_pika_channel

        # acquire() during consuming is called on Connection instance directly
        mock_pool_instance.acquire.return_value = mock_fairy_connection

        conn = Connection('localhost', 'user', 'pass')
        channel = conn.channel()

        # Set up a consumer callback that calls ack() and stop_consuming() on the active channel
        def user_callback(message):
            assert isinstance(message, MessageWrapper)
            assert message.body == 'message-body'
            assert message.method == {'routing_key': 'test-rk'}
            message.ack()
            channel.stop_consuming()

        mock_user_callback = MagicMock(side_effect=user_callback)
        channel.basic.consume(mock_user_callback, 'test-q')

        # Run start_consuming which is blocking, so we make start_consuming raise a dummy exception to break out
        def mock_start_consuming():
            # Trigger the basic_consume's callback
            assert mock_pika_channel.basic_consume.call_count == 1
            args, kwargs = mock_pika_channel.basic_consume.call_args
            assert kwargs['queue'] == 'test-q'
            assert kwargs['auto_ack'] is False

            # Retrieve the callback
            cb = kwargs['on_message_callback']

            # Construct mock parameters for the callback
            mock_ch = MagicMock()
            mock_method = MagicMock()
            mock_method.delivery_tag = 999
            mock_method.routing_key = 'test-rk'
            mock_properties = MagicMock()

            # Call the callback
            cb(mock_ch, mock_method, mock_properties, b'message-body')

            raise RuntimeError("Stop consuming loop")

        mock_pika_channel.start_consuming.side_effect = mock_start_consuming

        # Run start_consuming which triggers our mock and callback
        with pytest.raises(RuntimeError, match="Stop consuming loop"):
            channel.start_consuming()

        # Verify user callback was called
        assert mock_user_callback.call_count == 1

        # Verify basic_ack was successfully called inside the callback context
        mock_pika_channel.basic_ack.assert_called_once_with(delivery_tag=999)

        # Verify stop_consuming was called on the active channel during consumption
        mock_pika_channel.stop_consuming.assert_called_once()
