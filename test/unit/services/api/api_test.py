from unittest.mock import MagicMock, patch


@patch('mash.services.api.utils.amqp.Connection')
def test_api_delete_job(mock_connection, test_client):
    channel = MagicMock()
    connection = MagicMock()
    connection.channel.return_value = channel
    mock_connection.return_value = connection

    response = test_client.delete(
        '/jobs/12345678-1234-1234-1234-123456789012'
    )

    channel.basic.publish.assert_called_once_with(
        body='{"job_delete": "12345678-1234-1234-1234-123456789012"}',
        routing_key='job_document',
        exchange='jobcreator',
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
    assert response.status_code == 200
    assert response.data == \
        b'{"job_id":"12345678-1234-1234-1234-123456789012"}\n'
