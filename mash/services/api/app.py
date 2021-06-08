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

import logging

from flask import Flask
from flask.logging import default_handler

from mash.services.api.extensions import api, jwt

from mash.log.filter import BaseServiceFilter
from mash.utils.mash_utils import setup_logfile, setup_rabbitmq_log_handler
from mash.utils.email_notification import EmailNotification

from mash.services.api.v1.utils.tokens import is_token_revoked

from mash.services.api.routes.api_spec import spec_api
from mash.services.api.v1.routes.user import api as v1_user_api
from mash.services.api.v1.routes.auth import api as v1_auth_api
from mash.services.api.v1.routes.token import api as v1_token_api

from mash.services.api.v1.routes.accounts import api as v1_accounts_api
from mash.services.api.v1.routes.accounts.azure import api as v1_azure_accounts_api
from mash.services.api.v1.routes.accounts.gce import api as v1_gce_accounts_api
from mash.services.api.v1.routes.accounts.ec2 import api as v1_ec2_accounts_api
from mash.services.api.v1.routes.accounts.oci import api as v1_oci_accounts_api
from mash.services.api.v1.routes.accounts.aliyun import api as v1_aliyun_accounts_api

from mash.services.api.v1.routes.jobs import api as v1_jobs_api
from mash.services.api.v1.routes.jobs.ec2 import api as v1_ec2_jobs_api
from mash.services.api.v1.routes.jobs.gce import api as v1_gce_jobs_api
from mash.services.api.v1.routes.jobs.azure import api as v1_azure_jobs_api
from mash.services.api.v1.routes.jobs.oci import api as v1_oci_jobs_api
from mash.services.api.v1.routes.jobs.aliyun import api as v1_aliyun_jobs_api


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
    configure_logger(app)
    configure_mailer(app)
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


def configure_mailer(app):
    """Configure email notification class."""
    notification_class = EmailNotification(
        app.config['SMTP_HOST'],
        app.config['SMTP_PORT'],
        app.config['SMTP_USER'],
        app.config['SMTP_PASS'],
        app.config['SMTP_SSL'],
        log_callback=app.logger
    )

    app.notification_class = notification_class


def register_namespaces():
    """Register Flask restplus namespaces."""
    api.add_namespace(spec_api, path='/api/spec')

    # V1
    api.add_namespace(v1_user_api, path='/v1/user')
    api.add_namespace(v1_auth_api, path='/v1/auth')
    api.add_namespace(v1_token_api, path='/v1/auth/token')

    api.add_namespace(v1_accounts_api, path='/v1/accounts')
    api.add_namespace(v1_azure_accounts_api, path='/v1/accounts/azure')
    api.add_namespace(v1_gce_accounts_api, path='/v1/accounts/gce')
    api.add_namespace(v1_ec2_accounts_api, path='/v1/accounts/ec2')
    api.add_namespace(v1_oci_accounts_api, path='/v1/accounts/oci')
    api.add_namespace(v1_aliyun_accounts_api, path='/v1/accounts/aliyun')

    api.add_namespace(v1_jobs_api, path='/v1/jobs')
    api.add_namespace(v1_ec2_jobs_api, path='/v1/jobs/ec2')
    api.add_namespace(v1_gce_jobs_api, path='/v1/jobs/gce')
    api.add_namespace(v1_azure_jobs_api, path='/v1/jobs/azure')
    api.add_namespace(v1_oci_jobs_api, path='/v1/jobs/oci')
    api.add_namespace(v1_aliyun_jobs_api, path='/v1/jobs/aliyun')


def register_extensions(app):
    """Register Flask extensions."""
    jwt.init_app(app)
    api.init_app(app)
