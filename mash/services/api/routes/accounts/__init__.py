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

from flask_restplus import fields, Namespace

from mash.services.api.schema import validation_error
from mash.services.api.schema.accounts import delete_account

api = Namespace(
    'accounts',
    description='Account related operations'
)
delete_account_request = api.schema_model(
    'delete_account_request',
    delete_account
)
account_response = api.model(
    'add_account_response', {
        'name': fields.String(example='user1')
    }
)
validation_error_response = api.schema_model(
    'validation_error',
    validation_error
)
