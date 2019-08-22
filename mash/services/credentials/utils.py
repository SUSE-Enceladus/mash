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

import os

from mash.utils.mash_utils import load_json, persist_json, remove_file


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
