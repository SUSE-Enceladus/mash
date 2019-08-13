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
# flake8: noqa: E402

import json

from flask import Flask
from flask_restplus import Api
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from mash.services.api.config import Config

app = Flask('MashAPIService', static_url_path='/static')
api = Api(
    app,
    version='3.4.0',
    title='MASH API',
    description='MASH provides a set of endpoints for Image Release '
                'automation into Public Cloud Frameworks.',
    validate=True,
    doc=False
)

app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Imports out of order to prevent circular dependencies
from mash.services.api.routes.accounts import api as accounts_api
from mash.services.api.routes.accounts.azure import api as azure_accounts_api
from mash.services.api.routes.accounts.gce import api as gce_accounts_api
from mash.services.api.routes.accounts.ec2 import api as ec2_accounts_api

from mash.services.api.routes.jobs import api as jobs_api
from mash.services.api.routes.jobs.ec2 import api as ec2_jobs_api
from mash.services.api.routes.jobs.gce import api as gce_jobs_api
from mash.services.api.routes.jobs.azure import api as azure_jobs_api

api.add_namespace(accounts_api, path='/accounts')
api.add_namespace(azure_accounts_api, path='/accounts/azure')
api.add_namespace(gce_accounts_api, path='/accounts/gce')
api.add_namespace(ec2_accounts_api, path='/accounts/ec2')

api.add_namespace(jobs_api, path='/jobs')
api.add_namespace(ec2_jobs_api, path='/jobs/ec2')
api.add_namespace(gce_jobs_api, path='/jobs/gce')
api.add_namespace(azure_jobs_api, path='/jobs/azure')


@app.route('/api/spec', methods=('GET', 'POST'))
def api_doc():
    return json.dumps(api.__schema__)
