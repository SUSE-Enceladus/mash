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
import os

from mash.log.handler import RabbitMQHandler
from mash.mash_exceptions import MashLogSetupException
from mash.utils.mash_utils import load_json, persist_json, remove_file


def setup_logfile(logfile):
    """
    Create log dir and log file if either does not already exist.
    """
    try:
        log_dir = os.path.dirname(logfile)
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)
    except Exception as e:
        raise MashLogSetupException(
            'Log setup failed: {0}'.format(e)
        )

    logfile_handler = logging.FileHandler(
        filename=logfile, encoding='utf-8'
    )

    return logfile_handler


def get_logging_formatter():
    return logging.Formatter(
        '%(newline)s%(levelname)s %(asctime)s %(name)s%(newline)s'
        '    %(job)s %(message)s'
    )


def setup_rabbitmq_log_handler(host, username, password):
    rabbit_handler = RabbitMQHandler(
        host=host,
        username=username,
        password=password,
        routing_key='mash.logger'
    )
    rabbit_handler.setFormatter(get_logging_formatter())

    return rabbit_handler


def add_job_to_queue(job_doc, jobs):
    jobs[job_doc['id']] = job_doc


def get_job_file(job_dir, job_id):
    return '{0}job-{1}.json'.format(job_dir, job_id)


def restart_jobs(job_dir, jobs):
    for job_file in os.listdir(job_dir):
        job_doc = load_json(os.path.join(job_dir, job_file))
        add_job_to_queue(job_doc, jobs)


def save_job(job_doc, job_dir):
    job_file = get_job_file(job_dir, job_doc['id'])
    job_doc['job_file'] = job_file
    persist_json(job_file, job_doc)


def remove_job_from_queue(job_id, jobs):
    del jobs[job_id]


def remove_job(job_dir, job_id):
    job_file = get_job_file(job_dir, job_id)
    remove_file(job_file)
