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

import io

from pytest import raises
from unittest.mock import call, MagicMock, patch

from mash.mash_exceptions import MashException, MashLogSetupException
from mash.utils.json_format import JsonFormat
from mash.utils.mash_utils import (
    create_json_file,
    create_key_file,
    generate_name,
    get_key_from_file,
    create_ssh_key_pair,
    format_string_with_date,
    remove_file,
    persist_json,
    load_json,
    restart_job,
    restart_jobs,
    handle_request,
    setup_logfile,
    setup_rabbitmq_log_handler,
    get_fingerprint_from_private_key,
    normalize_dictionary
)


private_key = '''-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQCqGKukO1De7zhZj6+H0qtjTkVxwTCpvKe4eCZ0FPqri0cb2JZfXJ/DgYSF6vUp
wmJG8wVQZKjeGcjDOL5UlsuusFncCzWBQ7RKNUSesmQRMSGkVb1/3j+skZ6UtW+5u09lHNsj6tQ5
1s1SPrCBkedbNf0Tp0GbMJDyR4e9T04ZZwIDAQABAoGAFijko56+qGyN8M0RVyaRAXz++xTqHBLh
3tx4VgMtrQ+WEgCjhoTwo23KMBAuJGSYnRmoBZM3lMfTKevIkAidPExvYCdm5dYq3XToLkkLv5L2
pIIVOFMDG+KESnAFV7l2c+cnzRMW0+b6f8mR1CJzZuxVLL6Q02fvLi55/mbSYxECQQDeAw6fiIQX
GukBI4eMZZt4nscy2o12KyYner3VpoeE+Np2q+Z3pvAMd/aNzQ/W9WaI+NRfcxUJrmfPwIGm63il
AkEAxCL5HQb2bQr4ByorcMWm/hEP2MZzROV73yF41hPsRC9m66KrheO9HPTJuo3/9s5p+sqGxOlF
L0NDt4SkosjgGwJAFklyR1uZ/wPJjj611cdBcztlPdqoxssQGnh85BzCj/u3WqBpE2vjvyyvyI5k
X6zk7S0ljKtt2jny2+00VsBerQJBAJGC1Mg5Oydo5NwD6BiROrPxGo2bpTbu/fhrT8ebHkTz2epl
U9VQQSQzY1oZMVX8i1m5WUTLPz2yLJIBQVdXqhMCQBGoiuSoSjafUhV7i1cEGpb88h5NBYZzWXGZ
37sJ5QsW+sJyoNde3xH8vdXhzU7eT82D6X/scw9RZz+/6rCJ4p0=
-----END RSA PRIVATE KEY-----
'''


@patch('mash.utils.mash_utils.os')
@patch('mash.utils.mash_utils.NamedTemporaryFile')
def test_create_json_file(mock_temp_file, mock_os):
    json_file = MagicMock()
    json_file.name = 'test.json'
    mock_temp_file.return_value = json_file

    data = {'tenantId': '123456', 'subscriptionId': '98765'}
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value = MagicMock(spec=io.IOBase)
        with create_json_file(data) as json_file:
            assert json_file == 'test.json'

        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(JsonFormat.json_message(data))

    mock_os.remove.assert_called_once_with('test.json')


def test_generate_name():
    result = generate_name(10)
    assert len(result) == 10


def test_get_key_from_file():
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value = MagicMock(spec=io.IOBase)
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.read.return_value = 'fakekey'
        result = get_key_from_file('my-key.file')

    assert result == 'fakekey'


@patch('mash.utils.mash_utils.rsa')
def test_create_ssh_key_pair(mock_rsa):
    private_key = MagicMock()
    public_key = MagicMock()

    public_key.public_bytes.return_value = b'0987654321'

    private_key.public_key.return_value = public_key
    private_key.private_bytes.return_value = b'1234567890'

    mock_rsa.generate_private_key.return_value = private_key

    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value = MagicMock(spec=io.IOBase)
        create_ssh_key_pair('/temp.key')
        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_has_calls([
            call(b'1234567890'),
            call(b'0987654321')
        ])


def test_format_string_with_date_error():
    value = 'Name with a {timestamp}'
    format_string_with_date(value)


@patch('mash.utils.mash_utils.os.remove')
def test_remove_file(mock_remove):
    mock_remove.side_effect = FileNotFoundError('File not found.')
    remove_file('job-test.json')
    mock_remove.assert_called_once_with('job-test.json')


def test_persist_json():
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value = MagicMock(spec=io.IOBase)

        persist_json('tmp-dir/job-1.json', {'id': '1'})

        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with('{\n    "id": "1"\n}')


@patch('mash.utils.mash_utils.json.load')
def test_load_json(mock_load_json):
    mock_load_json.return_value = {'id': '123'}

    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value = MagicMock(spec=io.IOBase)

        data = load_json('tmp/job-123.json')

        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.read.call_count == 1

    assert data['id'] == '123'


@patch('mash.utils.mash_utils.load_json')
def test_restart_job(mock_json_load):
    mock_json_load.return_value = {'id': '123'}
    callback = MagicMock()

    restart_job('tmp/job-123.json', callback)
    mock_json_load.assert_called_once_with(
        'tmp/job-123.json'
    )
    callback.assert_called_once_with({'id': '123'})


@patch('mash.utils.mash_utils.restart_job')
@patch('mash.utils.mash_utils.os.listdir')
def test_restart_jobs(mock_os_listdir, mock_restart_job):
    mock_os_listdir.return_value = ['job-123.json']
    callback = MagicMock()

    restart_jobs('tmp/', callback)
    mock_restart_job.assert_called_once_with(
        'tmp/job-123.json',
        callback
    )


@patch('mash.utils.mash_utils.requests')
def test_handle_request(mock_requests):
    response = MagicMock()
    response.status_code = 200
    mock_requests.get.return_value = response

    result = handle_request('localhost', '/jobs', 'get')
    assert result == response


@patch('mash.utils.mash_utils.requests')
def test_handle_request_failed(mock_requests):
    response = MagicMock()
    response.status_code = 400
    response.reason = 'Not Found'
    response.json.return_value = {}
    mock_requests.get.return_value = response

    with raises(MashException):
        handle_request('localhost', '/jobs', 'get')


@patch('mash.utils.mash_utils.logging')
@patch('mash.utils.mash_utils.os')
def test_setup_logfile(mock_os, mock_logging):
    mock_os.path.isdir.return_value = False
    mock_os.path.dirname.return_value = '/file/dir'

    setup_logfile('/file/dir/fake.path')
    mock_os.makedirs.assert_called_once_with('/file/dir')
    mock_logging.FileHandler.assert_called_once_with(
        filename='/file/dir/fake.path', encoding='utf-8'
    )

    mock_os.makedirs.side_effect = Exception('Cannot create dir')
    with raises(MashLogSetupException):
        setup_logfile('fake.path')


@patch('mash.utils.mash_utils.logging')
@patch('mash.utils.mash_utils.RabbitMQHandler')
def test_setup_rabbitmq_log_handler(mock_rabbit, mock_logging):
    handler = MagicMock()
    formatter = MagicMock()
    mock_rabbit.return_value = handler
    mock_logging.Formatter.return_value = formatter

    setup_rabbitmq_log_handler('localhost', 'user1', 'pass')

    mock_rabbit.assert_called_once_with(
        host='localhost',
        username='user1',
        password='pass',
        routing_key='mash.logger'
    )
    handler.setFormatter.assert_called_once_with(formatter)


def test_get_fingerprint_from_private_key():
    fingerprint = get_fingerprint_from_private_key(private_key)
    assert fingerprint == '95:3c:b5:5e:a5:ca:c7:2d:6b:0a:e1:41:93:0e:89:32'

    # Test key already bytes
    get_fingerprint_from_private_key(private_key.encode())


@patch('mash.utils.mash_utils.os')
@patch('mash.utils.mash_utils.NamedTemporaryFile')
def test_create_key_file(mock_temp_file, mock_os):
    key_file = MagicMock()
    key_file.name = 'test.pem'
    mock_temp_file.return_value = key_file

    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value = MagicMock(spec=io.IOBase)
        with create_key_file(private_key) as f:
            assert f == 'test.pem'

        file_handle = mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called_with(private_key)

    mock_os.remove.assert_called_once_with('test.pem')


def test_normalize_dict():
    data = {
        'boolean': True,
        'int': 8,
        'string': 'Good string',
        'bad_string': ' extra white space ',
        'dict': {'test': ' data '},
        'list': [' test '],
        'list_dict': [{'test': ' data ', 'boolean': False}]
    }
    data = normalize_dictionary(data)

    assert data['boolean']
    assert data['int'] == 8
    assert data['string'] == 'Good string'
    assert data['bad_string'] == 'extra white space'
    assert data['dict']['test'] == 'data'
    assert data['list'][0] == 'test'
    assert data['list_dict'][0]['test'] == 'data'
