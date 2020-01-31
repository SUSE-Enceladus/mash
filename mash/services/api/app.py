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

import logging

from flask import Flask
from flask.logging import default_handler

from mash.services.api.extensions import api, db, jwt, migrate

from mash.log.filter import BaseServiceFilter
from mash.utils.mash_utils import setup_logfile, setup_rabbitmq_log_handler

from mash.services.api.utils.tokens import is_token_revoked

from mash.services.api.routes.api_spec import spec_api
from mash.services.api.routes.user import api as user_api
from mash.services.api.routes.auth import api as auth_api
from mash.services.api.routes.token import api as token_api

from mash.services.api.routes.accounts import api as accounts_api
from mash.services.api.routes.accounts.azure import api as azure_accounts_api
from mash.services.api.routes.accounts.gce import api as gce_accounts_api
from mash.services.api.routes.accounts.ec2 import api as ec2_accounts_api
from mash.services.api.routes.accounts.oci import api as oci_accounts_api

from mash.services.api.routes.jobs import api as jobs_api
from mash.services.api.routes.jobs.ec2 import api as ec2_jobs_api
from mash.services.api.routes.jobs.gce import api as gce_jobs_api
from mash.services.api.routes.jobs.azure import api as azure_jobs_api
from mash.services.api.routes.jobs.oci import api as oci_jobs_api

from mash.services.api.commands import tokens_cli


@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decoded_token):
    return is_token_revoked(decoded_token)


def create_app(config_object):
    """
    Factory for creating api using provided configuration object.
    """
    app = Flask('APIService', static_url_path='/static')
    app.config.from_object(config_object)
    register_extensions(app)
    register_namespaces()
    register_commands(app)
    configure_logger(app)
    return app


def configure_logger(app):
    """Configure loggers."""
    app.logger.removeHandler(default_handler)

    logging.basicConfig()
    app.logger.addFilter(BaseServiceFilter())
    app.logger.setLevel(logging.DEBUG)
    app.logger.propagate = False

    rabbit_handler = setup_rabbitmq_log_handler(
        app.config['AMQP_HOST'],
        app.config['AMQP_USER'],
        app.config['AMQP_PASS']
    )
    app.logger.addHandler(rabbit_handler)

    logfile_handler = setup_logfile(app.config['LOG_FILE'])
    app.logger.addHandler(logfile_handler)


def register_namespaces():
    """Register Flask restplus namespaces."""
    api.add_namespace(spec_api, path='/api/spec')
    api.add_namespace(user_api, path='/user')
    api.add_namespace(auth_api, path='/auth')
    api.add_namespace(token_api, path='/auth/token')

    api.add_namespace(accounts_api, path='/accounts')
    api.add_namespace(azure_accounts_api, path='/accounts/azure')
    api.add_namespace(gce_accounts_api, path='/accounts/gce')
    api.add_namespace(ec2_accounts_api, path='/accounts/ec2')
    api.add_namespace(oci_accounts_api, path='/accounts/oci')

    api.add_namespace(jobs_api, path='/jobs')
    api.add_namespace(ec2_jobs_api, path='/jobs/ec2')
    api.add_namespace(gce_jobs_api, path='/jobs/gce')
    api.add_namespace(azure_jobs_api, path='/jobs/azure')
    api.add_namespace(oci_jobs_api, path='/jobs/oci')


def register_extensions(app):
    """Register Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    api.init_app(app)

    # Required for flask-restplus to play nicely with flask-jwt-extended
    jwt._set_error_handler_callbacks(api)


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(tokens_cli)
