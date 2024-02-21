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

from jwt.exceptions import PyJWTError

from flask_restx import Api
from flask_jwt_extended import JWTManager

authorizations = {
    'apiKey': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'example': 'Bearer {token}'
    }
}

api = Api(
    version='13.8.1',
    contact='public-cloud-dev@susecloud.net',
    title='MASH API',
    description='MASH provides a set of endpoints for Image Release '
                'automation into Public Cloud Frameworks.',
    validate=True,
    doc=False,
    authorizations=authorizations
)


@api.errorhandler(PyJWTError)
def handle_jwt_exception(error):
    err = '. '.join([
        str(error),
        'Log in again with "mash auth login" or "mash auth oidc".'
    ])
    return {"msg": err}, 401


jwt = JWTManager()
