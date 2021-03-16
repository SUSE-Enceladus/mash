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

from mash.utils.mash_utils import setup_logfile, setup_rabbitmq_log_handler
from mash.log.filter import BaseServiceFilter
from mash.services.database.routes import jobs, tokens, users
from mash.services.database.routes.accounts import aliyun, azure, ec2, gce, oci
from mash.services.database.extensions import db, migrate
from mash.services.database.commands import tokens_cli


def register_extensions(app):
    """Register Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)


def create_app(config_object):
    """
    Factory for creating api using provided configuration object.
    """
    app = Flask('DBService', static_url_path='/static')
    app.config.from_object(config_object)
    register_blueprints(app)
    register_commands(app)
    configure_logger(app)
    register_extensions(app)
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


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(jobs.blueprint)
    app.register_blueprint(tokens.blueprint)
    app.register_blueprint(users.blueprint)
    app.register_blueprint(azure.blueprint)
    app.register_blueprint(ec2.blueprint)
    app.register_blueprint(gce.blueprint)
    app.register_blueprint(oci.blueprint)
    app.register_blueprint(aliyun.blueprint)


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(tokens_cli)
