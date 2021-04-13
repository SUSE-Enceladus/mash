from unittest.mock import Mock, patch

from mash.services.api.v1.utils.amqp import connect, publish

from werkzeug.local import LocalProxy


@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.v1.utils.amqp.Connection')
def test_connect(mock_connection, mock_get_current_object):
    connection = Mock()
    channel = Mock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    connect()
    channel.confirm_deliveries.assert_called_once_with()


@patch('mash.services.api.v1.utils.amqp.connect')
@patch.object(LocalProxy, '_get_current_object')
@patch('mash.services.api.v1.utils.amqp.channel')
def test_publish(mock_channel, mock_get_current_object, mock_connect):
    mock_channel.closed = True
    publish('test', 'doc', 'msg')

    mock_connect.assert_called_once_with()
    mock_channel.basic.publish.assert_called_once_with(
        body='msg',
        routing_key='doc',
        exchange='test',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
