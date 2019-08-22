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

import atexit
import logging
import os

from flask import Flask
from flask.logging import default_handler

from mash.utils.mash_utils import setup_logfile, setup_rabbitmq_log_handler
from mash.log.filter import BaseServiceFilter
from mash.services.credentials.datastore import CredentialsDatastore
from mash.services.credentials.utils import restart_jobs
from mash.services.credentials.routes import credentials
from mash.services.credentials.routes import jobs


def setup_app(app):
    """Setup credentials datastore and restart jobs."""
    app.jobs = {}
    app.credentials_datastore = CredentialsDatastore(
        app.config['CREDS_DIR'],
        app.config['ENC_KEYS_FILE'],
        app.logger
    )
    atexit.register(app.credentials_datastore.shutdown)

    os.makedirs(app.config['JOB_DIR'], exist_ok=True)
    restart_jobs(app.config['JOB_DIR'], app.jobs)


def create_app(config_object):
    """
    Factory for creating api using provided configuration object.
    """
    app = Flask('CredentialsService', static_url_path='/static')
    app.config.from_object(config_object)
    register_blueprints(app)
    configure_logger(app)
    setup_app(app)
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
    app.register_blueprint(credentials.blueprint)
    app.register_blueprint(jobs.blueprint)
