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

import json

from flask import Flask, render_template
from flask_restplus import Api

from mash.services.api.routes.accounts import api as accounts_api
from mash.services.api.routes.accounts.azure import api as azure_accounts_api
from mash.services.api.routes.accounts.gce import api as gce_accounts_api
from mash.services.api.routes.accounts.ec2 import api as ec2_accounts_api

from mash.services.api.routes.jobs import api as jobs_api
from mash.services.api.routes.jobs.ec2 import api as ec2_jobs_api
from mash.services.api.routes.jobs.gce import api as gce_jobs_api
from mash.services.api.routes.jobs.azure import api as azure_jobs_api

app = Flask(__name__, static_url_path='/static')
api = Api(
    app,
    version='3.3.0',
    title='MASH API',
    description='MASH provides a set of endpoints for Image Release '
                'automation into the Public Cloud Frameworks.',
    validate=True,
    doc=False
)

api.add_namespace(accounts_api, path='/accounts')
api.add_namespace(azure_accounts_api, path='/accounts/azure')
api.add_namespace(gce_accounts_api, path='/accounts/gce')
api.add_namespace(ec2_accounts_api, path='/accounts/ec2')

api.add_namespace(jobs_api, path='/jobs')
api.add_namespace(ec2_jobs_api, path='/jobs/ec2')
api.add_namespace(gce_jobs_api, path='/jobs/gce')
api.add_namespace(azure_jobs_api, path='/jobs/azure')


@app.route('/api/docs', methods=('GET', 'POST'))
def api_doc():
    api_spec = json.dumps(api.__schema__)
    return render_template('api_doc.html', api_spec=api_spec)
