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
import requests

from jwt import PyJWK

from urllib.parse import urljoin


def decode_token(
    provider_url,
    token,
    audience,
    tenant=None,
    jwks_uri='keys'
):
    """
    Decode given Java Web Token
    """
    url = urljoin(
        provider_url + '/',
        '/'.join(filter(None, [tenant, jwks_uri, '/']))
    )

    try:
        response = requests.get(url)
    except Exception as error:
        raise Exception(
            f'Unable to retreive signing keys from {url}: {str(error)}'
        )

    if response.status_code not in (200, 201):
        response.raise_for_status()

    jwks = response.json()
    keys = jwks.get('keys')
    if not keys:
        raise Exception('no keys retrieved from authentication provider')

    for jwk in keys:
        try:
            jwk_obj = PyJWK(jwk)
            algorithm = jwk.get('alg', 'RS256')
            token_json = jwt.decode(
                token,
                jwk_obj.key,
                audience=audience,
                algorithms=[algorithm]
            )
            return token_json
        except Exception as e:
            last_exception = e
            pass

    raise last_exception
