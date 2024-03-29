# Copyright (c) 2021 SUSE LLC.  All rights reserved.
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

from flask import jsonify
from flask_restx import Namespace, Resource

from mash.services.api.extensions import api

spec_api = Namespace(
    'API Spec document',
    description='API Specification'
)


@spec_api.route('/', doc=False)
class APIDoc(Resource):
    def post(self):
        return jsonify(api.__schema__)

    def get(self):
        return jsonify(api.__schema__)
