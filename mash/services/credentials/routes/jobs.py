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

from flask import Blueprint, current_app, jsonify, request, make_response

from mash.services.credentials.utils import (
    add_job_to_queue,
    remove_job,
    remove_job_from_queue,
    save_job
)

blueprint = Blueprint('jobs', __name__, url_prefix='/jobs')


@blueprint.route('/', methods=['POST'])
def add_job():
    data = json.loads(request.data.decode())
    job_doc = data['credentials_job']

    if job_doc['id'] in current_app.jobs:
        msg = 'Job exists'
        current_app.logger.info(msg, extra={'job_id': job_doc['id']})
        return make_response(jsonify({'msg': msg}), 400)

    try:
        save_job(job_doc, current_app.config['JOB_DIR']),
        add_job_to_queue(job_doc, current_app.jobs)
    except Exception as error:
        msg = 'Unable to add job: {0}'.format(error)
        current_app.logger.warning(msg, extra={'job_id': job_doc['id']})
        return make_response(jsonify({'msg': msg}), 400)

    current_app.logger.info(
        'Job queued, awaiting credentials requests.',
        extra={'job_id': job_doc['id']}
    )
    return make_response(jsonify({'msg': 'Job added'}), 201)


@blueprint.route('/<string:job_id>', methods=['DELETE'])
def delete_job(job_id):
    if job_id not in current_app.jobs:
        msg = 'Job does not exist'
        current_app.logger.warning(msg, extra={'job_id': job_id})
        return make_response(jsonify({'msg': msg}), 404)

    try:
        remove_job(current_app.config['JOB_DIR'], job_id)
        remove_job_from_queue(job_id, current_app.jobs)
    except Exception as error:
        msg = 'Unable to delete job: {0}'.format(error)
        current_app.logger.warning(msg, extra={'job_id': job_id})
        return make_response(jsonify({'msg': msg}), 400)

    current_app.logger.info('Deleting job.', extra={'job_id': job_id})
    return make_response(jsonify({'msg': 'Job deleted'}), 200)
