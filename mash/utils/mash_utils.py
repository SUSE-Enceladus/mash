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

import datetime
import json
import logging
import os
import random
import requests

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from contextlib import contextmanager, suppress
from string import ascii_lowercase
from tempfile import NamedTemporaryFile

from mash.log.handler import RabbitMQHandler
from mash.mash_exceptions import MashException, MashLogSetupException
from mash.utils.json_format import JsonFormat


@contextmanager
def create_json_file(data):
    try:
        temp_file = NamedTemporaryFile(delete=False)
        with open(temp_file.name, 'w') as json_file:
            json_file.write(JsonFormat.json_message(data))
        yield temp_file.name
    finally:
        with suppress(OSError):
            os.remove(temp_file.name)


def generate_name(length=8):
    """
    Generate a random lowercase string of the given length: Default of 8.
    """
    return ''.join([random.choice(ascii_lowercase) for i in range(length)])


def get_key_from_file(key_file_path):
    """
    Return a key as string from the given file.
    """
    with open(key_file_path, 'r') as key_file:
        key = key_file.read().strip()

    return key


def create_ssh_key_pair(ssh_private_key_file):
    """
    Create ssh key pair and store in ssh_private_key_file.
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )

    # Get public key
    public_key = private_key.public_key()

    # Write pem formatted private key to file
    pem_private_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(ssh_private_key_file, 'wb') as private_key_file:
        private_key_file.write(pem_private_key)

    # Write OpenSSH formatted public key to file
    ssh_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    )

    with open(''.join([ssh_private_key_file, '.pub']), 'wb') as public_key_file:
        public_key_file.write(ssh_public_key)


def format_string_with_date(value, timestamp=None, date_format='%Y%m%d'):
    if not timestamp:
        timestamp = datetime.date.today().strftime(date_format)

    try:
        value = value.format(date=timestamp)
    except KeyError:
        # Ignore unknown format strings.
        pass

    return value


def remove_file(file_path):
    """
    Remove file from disk if it exists.
    """
    try:
        os.remove(file_path)
    except FileNotFoundError:
        pass


def persist_json(file_path, data):
    """
    Persist the json data to a file on disk.
    """
    with open(file_path, 'w') as json_file:
        json_file.write(JsonFormat.json_message(data))


def load_json(file_path):
    """
    Load json from file and return dictionary.
    """
    with open(file_path, 'r') as json_file:
        data = json.load(json_file)

    return data


def restart_job(job_file, callback):
    """
    Restart job from config file using callback.
    """
    job_config = load_json(job_file)
    callback(job_config)


def restart_jobs(job_dir, callback):
    """
    Restart all jobs in job_dir using callback.
    """
    for job_file in os.listdir(job_dir):
        restart_job(os.path.join(job_dir, job_file), callback)


def handle_request(url, endpoint, method, job_data=None):
    """
    Post request based on endpoint and data.

    If response is unsuccessful raise exception.
    """
    request_method = getattr(requests, method)
    data = None if not job_data else JsonFormat.json_message(job_data)
    uri = ''.join([url, endpoint])

    response = request_method(uri, data=data)

    if response.status_code not in (200, 201):
        try:
            msg = response.json()['msg']
        except Exception:
            msg = 'Request to {uri} failed: {reason}'.format(
                uri=uri,
                reason=response.reason
            )

        raise MashException(msg)

    return response


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
