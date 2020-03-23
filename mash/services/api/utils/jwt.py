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

import jwt
import json
import requests

from cryptography.hazmat.primitives import serialization


def decode_token(provider_url, token, audience):
    """
    Decode given Java Web Token
    """
    response = requests.get('{}/keys'.format(provider_url))

    if response.status_code not in (200, 201):
        response.raise_for_status()

    jwks = response.json()
    keys = jwks.get('keys')
    if not keys:
        raise Exception('no keys retrieved from authentication provider')

    for jwk in keys:
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        try:
            token_json = jwt.decode(token, pem, audience=audience)
            return token_json
        except Exception as e:
            last_exception = e
            pass

    raise last_exception
