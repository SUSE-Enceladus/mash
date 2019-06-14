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

from flask import Flask
from flask_restplus import Api

from mash.services.api.accounts import api as accounts_api
from mash.services.api.azure_accounts import api as azure_accounts_api
from mash.services.api.gce_accounts import api as gce_accounts_api
from mash.services.api.ec2_accounts import api as ec2_accounts_api

from mash.services.api.jobs import api as jobs_api
from mash.services.api.ec2_jobs import api as ec2_jobs_api
from mash.services.api.gce_jobs import api as gce_jobs_api
from mash.services.api.azure_jobs import api as azure_jobs_api

app = Flask(__name__, static_url_path='/static')
api = Api(
    app,
    version='1.0',
    title='MASH API',
    description='MASH API',
    validate=True
)

api.add_namespace(accounts_api, path='/accounts')
api.add_namespace(azure_accounts_api, path='/accounts/azure')
api.add_namespace(gce_accounts_api, path='/accounts/gce')
api.add_namespace(ec2_accounts_api, path='/accounts/ec2')

api.add_namespace(jobs_api, path='/jobs')
api.add_namespace(ec2_jobs_api, path='/jobs/ec2')
api.add_namespace(gce_jobs_api, path='/jobs/gce')
api.add_namespace(azure_jobs_api, path='/jobs/azure')
