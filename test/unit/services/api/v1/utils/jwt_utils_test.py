from pytest import raises
from unittest.mock import patch, Mock

import jwt
import time

from mash.services.api.v1.utils.jwt import decode_token


@patch('mash.services.api.v1.utils.jwt.jwt.algorithms.RSAAlgorithm.from_jwk')
@patch('mash.services.api.v1.utils.jwt.requests')
def test_decode_token(mock_requests, mock_from_jwt):
    now = int(time.time())
    token = {
        'iss': 'iss-1234',
        'sub': 'sub-1234',
        'email': 'user1@fake.com',
        'aud': 'aud-1234',
        'iat': now,
        'exp': now + 3600 * 24
    }
    key = 'secret'
    mock_response = Mock()
    mock_response.json.return_value = {'keys': [{'foo': 'bar'}]}
    mock_response.status_code.return_value = 200
    mock_requests.get.return_value = mock_response
    mock_key = Mock()
    mock_key.public_bytes.return_value = key
    mock_from_jwt.return_value = mock_key

    # test success
    jw_token = jwt.encode(token, key)
    dec_token = decode_token('https://fake.com/ouath2/v1', jw_token, 'aud-1234')

    assert dec_token == token

    # test decode fail
    with raises(Exception):
        decode_token('https://fake.com/ouath2/v1', jw_token, 'aud-4321')

    # test key retrieval fail
    mock_response.json.return_value = {}
    with raises(Exception):
        decode_token('https://fake.com/ouath2/v1', jw_token, 'aud-1234')

    # test key retrieval fail wrong status
    mock_response.status_code.return_value = 499
    with raises(Exception):
        decode_token('https://fake.com/ouath2/v1', jw_token, 'aud-1234')
